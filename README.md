# Système de recommandation de films

Le lancement de l'application web requiert d'avoir préalablement installé **Docker** et **Neo4j Desktop**.

L'installation et la configuration de MongoDB n'est pas nécessaire, car la base utilisée a été correctement conteneurisée.

## Étapes à suivre :

### Préparation de la base Neo4j
1. Créer une nouvelle instance Neo4j en gardant en mémoire l'**user** et le **password**.
2. Installer sur cette instance le plugin **GDS** (Graph Data Science) nécessaire pour le calcul de recommandation (via menu [···])
3. Démarrer l'instance et y créer une nouvelle base de données
4. Aller dans **Import** et se connecter à l'instance créée
5. Sélectionner la base de donnée créée (ne pas garder *"neo4j"*)
6. Depuis le menu [···], ouvrir le modèle qui se trouve dans **/data**
7. Importer les 5 fichiers **.csv** de **/data** dans **Tables**. Pour avoir des plus gros jeux de données, prendre les users et les ratings dans **/data/big**
8. Lier pour les 3 nœuds et les 2 relations le fichier CSV correspondant ainsi que les différentes propriétés avec les noms de colonnes
9. Lancer l'import
10. Lorsque l'import est terminé, exécuter la requête Cypher suivante pour calculer les moyennes initiales des notes.
```cypher
MATCH (m:MOVIE)<-[r:RATING]-()
WITH m, avg(r.value) AS rating_avg
WHERE rating_avg IS NOT NULL
SET m.rating_avg = rating_avg;
```

### Définition des variables d'environnement
Modifier le fichier **.env** en définissant ces variables d'environnement selon votre base Neo4j :
````
NEO4J_USER=...
NEO4J_PASSWORD=...
NEO4J_DBNAME=...
````

### Lancement du docker
Dans le répertoire principal du dépôt, exécuter :
```sh
docker compose up --build
```
Après construction et , l'application web est normalement disponible sur http://localhost:5000/ ou http://127.0.0.1:5000.

Pour arrêter :
```sh
docker compose down
``` 

Pour supprimer :
```sh
docker compose down
``` 