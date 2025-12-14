MATCH (n:USER {user_id: $user_id})-[r:RATING]-(m:MOVIE)
RETURN m.title AS title, m.imdb_id AS imdb_id, r.value AS value
ORDER BY value DESC;
