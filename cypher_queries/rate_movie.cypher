MATCH (u:USER {user_id: $user_id})
MATCH (m:MOVIE {imdb_id: $imdb_id})
MERGE (u)-[r:RATING]->(m)
SET r.value = $value
RETURN u.user_id, m.imdb_id, r.value;
