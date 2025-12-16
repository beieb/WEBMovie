import csv
import ast

#"ratings_small.csv"
#"generated_users.csv"
#"generated_ratings.csv"

input_file = "ratings_small.csv"
user_file = "small/generated_users.csv"
ratings_file = "small/generated_ratings.csv"

relations = []

with open(input_file, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    user_ids = []
    users = []
    genres = []

    for row in reader:

        try:
            user_id = int(row["userId"])

            if user_id not in user_ids:

                pseudo = "Generated User #"+str(user_id)
                users.append((user_id, pseudo))
                user_ids.append(user_id)

            try:
                movie_id = int(row["movieId"])
                rating = int(float(row["rating"])*2)   # /5 → /10
                relations.append((user_id,movie_id,rating))

            except ValueError:
                continue

        except ValueError:
            continue

# Write generated_users.csv
with open(user_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["user_id", "pseudo"])
    writer.writerows(users)

# Write generated_ratings.csv
with open(ratings_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["user_id", "movie_id", "value"])
    writer.writerows(relations)