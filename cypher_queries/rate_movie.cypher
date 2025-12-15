MATCH (u:USER {user_id: $user_id})
MATCH (m:MOVIE {imdb_id: $imdb_id})
MERGE (u)-[r:RATING]->(m)
SET r.value = $value

// Update average rating
WITH m
MATCH (m)<-[allRatings:RATING]-()
WITH m, avg(allRatings.value) AS rating_avg
SET m.rating_avg = rating_avg

RETURN m.rating_avg;
