MATCH (m:MOVIE)<-[r:RATING]-()
WITH m, avg(r.value) AS rating_avg
WHERE rating_avg IS NOT NULL
SET m.rating_avg = rating_avg;
