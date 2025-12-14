MATCH (n:USER {user_id: $user_id})-[r:RATING]-(m:MOVIE)
RETURN m.imdb_id AS imdb_id, r.value AS value;
