import ast
import os
from flask import Flask, json, redirect, render_template, session, request, jsonify
from pymongo import MongoClient
from tmdbv3api import TMDb, Movie
from neo4j import GraphDatabase
import requests
import uuid


# =============================
#    NEO4J CONNECTION CLASS
# =============================
class Neo4jConnection:
    def __init__(self, uri, user, password):
        self._uri = uri
        self._user = user
        self._password = password
        self._driver = None

    def connect(self):
        try:
            self._driver = GraphDatabase.driver(self._uri, auth=(self._user, self._password))
            with self._driver.session() as session:
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
            with self._driver.session() as session:
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
conn = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
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
    best_movies = list(
        db.movies_metadata
          .find({"vote_average": {"$gt": 8}})
          .sort("vote_count", -1)
          .limit(12)
    )


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

    return render_template("main.html", best_movies=best_movies)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pseudo = request.form.get("pseudo")
        # password = request.form.get("password")
        query = """
            MATCH (u:USER {pseudo: $pseudo})
            RETURN u.pseudo AS pseudo, u.password AS password, u.user_id AS user_id
        """

        result = conn.query(query, {"pseudo": pseudo})
        if not result:
            return "Pseudo inconnu", 401

        user = result[0]

        # if user["password"] != password:
        #     return "Mot de passe incorrect", 401

        # Création de la session
        session["logged"] = True
        session["pseudo"] = user["pseudo"]
        session["user_id"] = user["user_id"]

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
            return "Ce pseudo est déjà utilisé", 400

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
    name = request.args.get("name", "")
    films = list(
        db.movies_metadata
        .find({"original_title": {"$regex": name, "$options": "i"}})
        .sort("vote_count", -1)
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

    return render_template("main.html", best_movies=films)
  



# =============================
#        LAUNCH APP
# =============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

