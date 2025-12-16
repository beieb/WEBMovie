// Cherche les utilisateurs qui ont notés au moins 2 films que le client a également noté
// En réalité il faudrait bien plus que 2 films en commun pour que la similarité Pearson soit stable
MATCH (client:USER {user_id:$user_id})-[r1:RATING]->(m:MOVIE)<-[r2:RATING]-(other:USER)
WITH client, other,
     collect(r1.value) AS ratings1,  // vecteur de notes du client
     collect(r2.value) AS ratings2,  // vecteur de notes de l'autre utilisateur
     COUNT(m) AS nbMovies            // taille des vecteurs
WHERE nbMovies > 5

// Calcule le coefficient de similarité entre le client et les autres utilisateur
// La métrique de Pearson est utilisée mais d'autres fonctions existent (Cosine)
WITH client, other,
     gds.similarity.pearson(ratings1, ratings2) AS similarity
WHERE similarity > 0    // pour éviter les poids négatif dans les recommandations 
WITH client, other, similarity

// Cherche les films qui ont été notés par les autres utilisateurs mais pas encore par le client (potentielles suggestions)
MATCH (other)-[r:RATING]->(suggestion:MOVIE)
WHERE NOT (client)-[:RATING]->(suggestion)

// Récupère les genres des films s'il y en a
OPTIONAL MATCH (suggestion)-[:TYPE]->(g_movie:Genre)
WITH client, other, suggestion, r, similarity,
     collect(DISTINCT g_movie.genre_id) AS movieGenres

// Récupère les genres appréciés par le client s'il en a
OPTIONAL MATCH (client)-[:PREFERENCE]->(g_client:Genre)
WITH suggestion, r, similarity, movieGenres,
     collect(DISTINCT g_client.genre_id) AS userGenres

// Calcule les notes pondérées des autres utilisateurs et les scores basés sur les genres
WITH suggestion,
     // notes pondérées = produits des notes utilisateurs par leurs coef de similarité
     r.value * similarity AS weightedRating,
     // score de similarité entre les genres du film et ceux appréciés par le client avec la métrique Jaccard
     gds.similarity.jaccard(movieGenres, userGenres) AS genreScore

// Agregation par suggestion
MATCH (suggestion)<-[allRatings:RATING]-()
WITH suggestion,
     SUM(weightedRating) AS collaborativeScore,  // Somme des notes pondérées
     suggestion.rating_avg AS avgRating,         // Moyenne des notes sur les films (stockage statique)
     genreScore

// Calcule du score de suggestion avec les 3 facteur :
// Score collaboratif (le + puissant), score de genre (content-based), moyenne des notes (popularité globale)
RETURN suggestion.title AS title, suggestion.imdb_id AS imdb_id,
       collaborativeScore * (1 + genreScore) * (1 + 0.1 * avgRating) AS score
ORDER BY score DESC
LIMIT 30;
