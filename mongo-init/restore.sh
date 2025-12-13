#!/bin/bash
echo "▶ Restoring MongoDB database..."

mongorestore \
  --db movie \
  --drop \
  /dump/movie

echo "✅ MongoDB restore finished"
