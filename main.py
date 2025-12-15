import ast
import os
from flask import Flask, json, redirect, render_template, session, request, jsonify, flash, url_for
from pymongo import MongoClient
from tmdbv3api import TMDb, Movie
from neo4j import GraphDatabase
import requests
import uuid
import math
import csv


# =============================
#    NEO4J CONNECTION CLASS
# =============================
class Neo4jConnection:
    def __init__(self, uri, user, password, database):
        self._uri = uri
        self._user = user
        self._password = password
        self._database = database
        self._driver = None

    def connect(self):
        try:
            self._driver = GraphDatabase.driver(
                self._uri,
                auth=(self._user, self._password)
            )
            with self._driver.session(database=self._database) as session:
                result = session.run("RETURN 'Neo4j connection successful' AS message")
                print(result.single()["message"])
        except Exception as e:
            print("❌ Erreur de connexion à Neo4j :", e)

    def close(self):
        if self._driver:
            self._driver.close()

    def query(self, cypher, params=None):
        if params is None:
            params = {}
        try:
            with self._driver.session(database=self._database) as session:
                result = session.run(cypher, params)
                return [record.data() for record in result]
        except Exception as e:
            print("❌ Neo4j query error:", e)
            return None


# =============================
#       CONFIGURATION
# =============================

# Flask
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "0123456789")

# Neo4j
NEO4J_URI = os.environ["NEO4J_URI"]
NEO4J_USER = os.environ["NEO4J_USER"]
NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]
conn = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, database="movies-users-ratings-2025-11-24t14-54-18")
conn.connect()

# MongoDB
mongo_url = os.environ["MONGO_URL"]
client = MongoClient(mongo_url)
db = client["movie"]

# TMDB API
tmdb = TMDb()
tmdb.api_key = '4a5d922af6e223215c319ef376c12050'
movie = Movie()


# =============================
#           ROUTES
# =============================



@app.route("/")
def main():
    page = request.args.get("page", 1, type=int)
    per_page = 18 

    query = {"vote_average": {"$gt": 8}}

    total_movies = db.movies_metadata.count_documents(query)
    total_pages = math.ceil(total_movies / per_page)

    best_movies = list(
        db.movies_metadata
          .find(query)
          .sort("vote_count", -1)
          .skip((page - 1) * per_page)
          .limit(per_page)
    )

    # récupération des posters TMDB
    for film in best_movies:
        imdb_id = film.get("imdb_id")
        if not imdb_id:
            continue

        url = (
            f"https://api.themoviedb.org/3/find/{imdb_id}"
            f"?api_key={tmdb.api_key}&external_source=imdb_id"
        )

        response = requests.get(url)
        if response.status_code != 200:
            continue

        data = response.json()
        if data.get("movie_results") and data["movie_results"][0].get("poster_path"):
            poster_path = data["movie_results"][0]["poster_path"]
            film["full_poster_url"] = f"https://image.tmdb.org/t/p/w500{poster_path}"

    return render_template(
        "main.html",
        best_movies=best_movies,
        page=page,
        total_pages=total_pages,
        endpoint="main",
        search_name = None
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pseudo = request.form.get("pseudo")
        password = request.form.get("password")
        query = """
            MATCH (u:USER {pseudo: $pseudo})
            RETURN u.pseudo AS pseudo, u.password AS password, u.user_id AS user_id
        """

        result = conn.query(query, {"pseudo": pseudo})
        if not result:
            return "Pseudo inconnu", 401
        
        result = conn.query(query, {"pseudo": pseudo})
        if not result or result[0]["password"] != password:
            flash("Pseudo ou mot de passe incorrect", "error")
            return redirect(url_for("login"))

        user = result[0]

        # if user["password"] != password:
        #     return "Mot de passe incorrect", 401

        # Création de la session
        session["logged"] = True
        session["pseudo"] = user["pseudo"]
        session["user_id"] = user["user_id"]

        # Retrieving user's favorite genres
        with open("cypher_queries/get_genres_by_user.cypher", "r", encoding="utf-8") as f:
            cypher_query = f.read()
        genres = conn.query(cypher_query, params={"user_id": user["user_id"]}) or []
        genres_list = list({g["genre"] for g in genres})
        session["genres"] = genres_list

        # Retrieving user's ratings
        with open("cypher_queries/get_ratings_by_user.cypher", "r", encoding="utf-8") as f:
            cypher_query = f.read()
        ratings_list = conn.query(cypher_query, params={"user_id": user["user_id"]}) or []
        ratings_dict = {r["imdb_id"]: r["value"] for r in ratings_list}
        session["ratings"] = ratings_dict

        return redirect("/")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        pseudo = request.form.get("pseudo")
        password = request.form.get("password")

        check_query = """
                    MATCH (u:USER {pseudo: $pseudo})
                    RETURN u
                """
        existing = conn.query(check_query, {"pseudo": pseudo})

        if existing:
            flash("Pseudo déja existant", "error")
            return redirect(url_for("register"))

        user_id = str(uuid.uuid4())     # UUID v4 = 122 bits of random -> 5.3e+36 combinations

        with open("cypher_queries/create_user.cypher", "r", encoding="utf-8") as f:
            cypher_query = f.read()

        new_user = conn.query(cypher_query, params={
            "pseudo": pseudo,
            "password": password,
            "user_id": user_id
        })

        if not new_user:
            return "Erreur lors de la création du compte", 500

        session["logged"] = True
        session["pseudo"] = pseudo
        session["user_id"] = user_id
        session["ratings"] = {}
        session["genres"] = []

        return redirect("/")

    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    session["logged"] = False
    return redirect("/")

@app.route("/neo4j/user")
def neo4j_user():
    cypher = """
        MATCH (m:Movie)
        RETURN m.title AS title, m.vote_average AS rating
        ORDER BY m.vote_average DESC
        LIMIT 10
    """

    results = conn.query(cypher)

    if results is None:
        return {"error": "Neo4j query failed"}, 500

    return {"movies": results}

@app.route("/rate_movie", methods=["POST"])
def rate_movie():

    # Error if we return directly login page -> delegate to JavaScript
    if not session.get("logged") or "user_id" not in session:
        return jsonify({
            "success": False,
            "error": "unauthorized"
        }), 401

    user_id = session.get("user_id")
    imdb_id = request.form.get("movie_id")
    rating = int(request.form.get("rating"))

    with open("cypher_queries/rate_movie.cypher", "r", encoding="utf-8") as f:
        cypher_query = f.read()

    result = conn.query(cypher_query, params={
        "user_id": user_id,
        "imdb_id": imdb_id,
        "value": rating
    })

    if result is None:
        print("Error 500 - Add Rating in Neo4j Database")
        print(f"\tuser_id: {user_id}\tmovie_imdb_id: {imdb_id}\trating: {rating}")
        return jsonify({"success": False, "error": "Neo4j query failed"}), 500
    else:
        session["ratings"][imdb_id] = rating
        return jsonify({"success": True}), 200

movie_genres = [
    'Action', 'Adventure', 'Animation', 'Comedy', 'Crime', 'Documentary', 'Drama', 'Family', 'Fantasy','Foreign',
    'History', 'Horror', 'Music', 'Mystery', 'Romance', 'Science Fiction', 'TV Movie', 'Thriller', 'War', 'Western'
]
@app.route("/preferences")
def preferences():
    if not session.get("logged") or not "user_id" in session:
        return redirect("/login")
    return render_template(
        "preferences.html",
        all_genres=movie_genres,
        user_genres=session.get("genres", []),
        pseudo=session.get("pseudo")
    )

@app.route("/update_genres", methods=["POST"])
def update_genres():
    if not session.get("logged") or not "user_id" in session:
        return jsonify(success=False, error="unauthorized"), 401

    data = request.get_json()
    if "genres" in data:
        genres = data.get("genres")

        with open("cypher_queries/update_genres_by_user.cypher", "r", encoding="utf-8") as f:
            cypher_query = f.read()

        user_id = session.get("user_id")
        result = conn.query(cypher_query, params={
            "user_id": user_id,
            "genres": genres
        })

        if result is None:
            print(f"Error 500 - Update genre preferences for user {user_id}")
            return jsonify({"success": False, "error": "Neo4j query failed"}), 500
        else:
            session["genres"] = genres
            return jsonify({"success": True}), 200
    else:
        return jsonify({"success": False, "error": "No genres in session"}), 404


@app.route("/movie/<imdb_id>")
def movie_details(imdb_id):
    film = db.movies_metadata.find_one({"imdb_id": imdb_id})
    if not film:
        return "Film non trouvé", 404
    
    raw = film.get("genres")
    if isinstance(raw, str):
        try:
            parsed = ast.literal_eval(raw)
            film["genres"] = [g["name"] for g in parsed]
        except:
            film["genres"] = []
    else:
        film["genres"] = []


    url = (
        f"https://api.themoviedb.org/3/find/{imdb_id}"
        f"?api_key={tmdb.api_key}&external_source=imdb_id"
    )
    r = requests.get(url)
    data = r.json()

    if data.get("movie_results"):
        poster = data["movie_results"][0].get("poster_path")
        if poster:
            film["full_poster_url"] = f"https://image.tmdb.org/t/p/w500{poster}"

    #details = film.details(imbd_id)
#    return render_template("movie_details.html", film=film, details=details)
    return render_template("movie_details.html", film=film)


@app.route("/suggestions")
def suggestions():
    if not session.get("logged") or not "user_id" in session:
        return redirect("/login")

    user_id = session["user_id"]  

    with open("cypher_queries/movies_suggestion.cypher", "r", encoding="utf-8") as f:
        cypher_query = f.read()

    suggest_movies = conn.query(cypher_query, params={"user_id": user_id})
    if suggest_movies is None:
        return {"error": "Neo4j query failed"}, 500

    #TODO: Refactoring : Same code repeated to get posters link
    for movie in suggest_movies:
        imdb_id = movie.get("imdb_id")
        if not imdb_id:
            continue
        url = (
            f"https://api.themoviedb.org/3/find/{imdb_id}"
            f"?api_key={tmdb.api_key}&external_source=imdb_id"
        )
        response = requests.get(url)
        if response.status_code != 200:
            continue
        data = response.json()
        if data.get("movie_results") and data["movie_results"][0].get("poster_path"):
            poster_path = data["movie_results"][0]["poster_path"]
            movie["full_poster_url"] = f"https://image.tmdb.org/t/p/w500{poster_path}"

    return render_template("suggestions.html", suggest_movies=suggest_movies)

@app.route("/search", methods=["GET", "POST"])
def search():
    page = request.args.get("page", 1, type=int)
    per_page = 18
    name = request.args.get("name", "")

    query = {
        "original_title": {
            "$regex": name,
            "$options": "i"
        }
    }
    total_movies = db.movies_metadata.count_documents(query)

    total_pages = math.ceil(total_movies / per_page)

    films = list(
        db.movies_metadata
        .find({"original_title": {"$regex": name, "$options": "i"}})
        .sort("vote_count", -1)
        .skip((page-1)*per_page)
        .limit(per_page)
        )
    
    for film in films:
        imdb_id = film.get("imdb_id")
        if not imdb_id:
            continue

        url = (
            f"https://api.themoviedb.org/3/find/{imdb_id}"
            f"?api_key={tmdb.api_key}&external_source=imdb_id"
        )

        response = requests.get(url)
        if response.status_code != 200:
            continue

        data = response.json()
        if data.get("movie_results") and data["movie_results"][0].get("poster_path"):
            poster_path = data["movie_results"][0]["poster_path"]
            film["full_poster_url"] = f"https://image.tmdb.org/t/p/w500{poster_path}"

    return render_template("main.html",
                            best_movies=films,
                            page=page,
                            total_pages=total_pages, 
                            endpoint="search",
                            search_name= name)
  
@app.route("/profile")
def profile():
    if not session.get("logged") or "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    page = int(request.args.get("page", 1))
    per_page = 10

    skip = (page - 1) * per_page
    limit = per_page


    # Récupération des films notés par l'utilisateur
    with open("cypher_queries/get_ratings_by_user.cypher", "r", encoding="utf-8") as f:
        cypher_query = f.read()

    rated_movies = conn.query(cypher_query, params={"user_id": user_id,"skip": skip, "limit": limit}) or []
    count_query = """
    MATCH (n:USER {user_id: $user_id})-[r:RATING]->(m:MOVIE)
    RETURN count(m) AS total
    """

    total_movies = conn.query(
        count_query,
        params={"user_id": user_id}
    )[0]["total"]

    total_pages = math.ceil(total_movies / per_page)

    # Récupération des posters TMDB
    for movie in rated_movies:
        imdb_id = movie.get("imdb_id")
        if not imdb_id:
            continue

        url = (
            f"https://api.themoviedb.org/3/find/{imdb_id}"
            f"?api_key={tmdb.api_key}&external_source=imdb_id"
        )
        response = requests.get(url)
        if response.status_code != 200:
            continue

        data = response.json()
        if data.get("movie_results") and data["movie_results"][0].get("poster_path"):
            poster_path = data["movie_results"][0]["poster_path"]
            movie["full_poster_url"] = f"https://image.tmdb.org/t/p/w500{poster_path}"

    return render_template(
        "profile.html",
        rated_movies=rated_movies,
        pseudo=session.get("pseudo"),
        total_pages=total_pages,
        page = page,
        endpoint="profile",
        search_name= None

    )

@app.route("/import_ratings_csv", methods=["POST"])
def import_ratings_csv():
    if not session.get("logged"):
        return jsonify(success=False, error="unauthorized"), 401

    file = request.files.get("csv_file")
    if not file or not file.filename.endswith(".csv"):
        return jsonify(success=False, error="invalid_file"), 400

    stream = file.stream.read().decode("utf-8").splitlines()
    reader = csv.reader(stream)

    user_id = session["user_id"]

    # detect if headers are on the 1st line
    first_row = next(reader, None)
    if first_row == ["imdb_id", "rating"]:
        rows = reader
    else:
        rows = [first_row] + list(reader)

    for row in rows:
        try:
            if len(row) != 2:
                continue
            imdb_id, rating = row
            rating = int(rating)

            if 0 < rating <= 10:
                conn.query(
                    open("cypher_queries/rate_movie.cypher").read(),
                    params={
                        "user_id": user_id,
                        "imdb_id": imdb_id,
                        "value": rating
                    }
                )
                session["ratings"][imdb_id] = rating
        except:
            print(row)
            continue

    return jsonify(success=True)


# =============================
#        LAUNCH APP
# =============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

