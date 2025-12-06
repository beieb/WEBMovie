import ast
import os
from flask import Flask, json, redirect, render_template, session, request
from pymongo import MongoClient
from tmdbv3api import TMDb, Movie
from neo4j import GraphDatabase
import requests
from dotenv import load_dotenv

load_dotenv()  # load .env



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
            # Test immédiat de connexion
            with self._driver.session() as session:
                result = session.run("RETURN 'Neo4j connection successful' AS message")
                print(result.single()["message"])
        except Exception as e:
            print("❌ Erreur de connexion à Neo4j :", e)

    def close(self):
        if self._driver is not None:
            self._driver.close()

    def query(self, cypher, params=None):
        """Execute une requete Cypher et retourne le resultat"""
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
db_uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
db_user = os.getenv("NEO4J_USER", "neo4j")
db_password = os.getenv("NEO4J_PASSWORD", "neo4j_password")

conn = Neo4jConnection(db_uri, db_user, db_password)
conn.connect()  # Test auto


# TMDB API
tmdb = TMDb()
tmdb.api_key = '4a5d922af6e223215c319ef376c12050'
movie = Movie()

# Flask + MongoDB
app = Flask(__name__)
client = MongoClient("mongodb://localhost:27017/")
db = client["movie"]


# =============================
#           ROUTES
# =============================
@app.route("/main")
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
    if requests.method == "POST":
        email = requests.form["email"]
        password = requests.form["password"]


        return "Connexion OK"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/main")

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
    movie_id = request.form.get("movie_id")
    rating = request.form.get("rating")
    user_id = session.get("user_id")

    #TODO: Change to create (replace if exists) rating in NEO4J db instead MongoDB
    db.ratings.insert_one({
        "user_id": user_id,
        "movie_id": movie_id,
        "rating": float(rating)
    })
    return {"status": "success"}, 200

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
    #TODO: Check user connection and get user_id
    user_id = 1

    with open("cypher_queries/movies_suggestion.cypher", "r", encoding="utf-8") as f:
        cypher_query = f.read()

    suggest_movies = conn.query(cypher_query, params={"user_id": user_id})
    if suggest_movies is None:
        return {"error": "Neo4j query failed"}, 500
    print(suggest_movies)

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


# =============================
#        LAUNCH APP
# =============================
if __name__ == "__main__":
    app.run(debug=True)
