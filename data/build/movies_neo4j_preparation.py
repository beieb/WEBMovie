import csv
import ast

input_file = "movies_metadata.csv"
movies_file = "movies.csv"
genres_file = "genres.csv"
relations_file = "movie_genres.csv"

genres_seen = set()
relations = []

with open(input_file, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    movies = []
    genres = []

    for row in reader:
        try:
            movie_id = int(row["id"])
        except ValueError:
            # Ligne corrompue → on ignore
            continue

        title = row["title"]
        imdb_id = row["imdb_id"]

        movies.append((movie_id, title, imdb_id))

        # Extraction des genres
        raw_genres = row["genres"].strip()

        if raw_genres in ("[]", "", None):
            continue

        try:
            genre_list = ast.literal_eval(raw_genres)
        except Exception:
            # Si le champ est cassé, on ignore ce film
            continue

        for g in genre_list:
            gid = int(g["id"])
            gname = g["name"]

            if gid not in genres_seen:
                genres_seen.add(gid)
                genres.append((gid, gname))

            relations.append((movie_id, gid))

# Write movies.csv
with open(movies_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["movie_id", "title", "imdb_id"])
    writer.writerows(movies)

# Write genres.csv
with open(genres_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["genre_id", "name"])
    writer.writerows(genres)

# Write movie_genres.csv
with open(relations_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["movie_id", "genre_id"])
    writer.writerows(relations)