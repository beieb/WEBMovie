MATCH (n:USER {user_id: $user_id})-[r:PREFERENCE]-(g:GENRE)
RETURN g.name AS genre;
