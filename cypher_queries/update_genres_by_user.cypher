MATCH (u:USER {user_id: $user_id})
OPTIONAL MATCH (u)-[p:PREFERENCE]->(g_old:GENRE)
DELETE p
WITH u

UNWIND $genres AS genreName
MATCH (g_new:GENRE {name: genreName})
MERGE (u)-[:PREFERENCE]->(g_new)
RETURN COUNT(g_new) AS nb_preferences;
