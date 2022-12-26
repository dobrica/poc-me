# Run container
docker run -d --name=mbdb --publish=7474:7474 --publish=7687:7687 --env=NEO4J_ACCEPT_LICENSE_AGREEMENT=yes --env=NEO4J_AUTH=none neo4j:4.2.1-enterprise

# Download database dump
echo "Downloading DB dump..."
sleep 1
docker exec -it mbdb wget https://www.dropbox.com/s/t884p9obs72loyc/musicbrainz-backup.dump?dl=0 -O /var/lib/neo4j/import/musicbrainz-backup.dump

# Load database dump
echo "Loading DB dump..."
sleep 1
docker exec -u neo4j -it mbdb neo4j-admin load --database=musicbrainz --from=/var/lib/neo4j/import/musicbrainz-backup.dump

# Create database
echo "Create DB..."
sleep 10
docker exec -u neo4j -it mbdb cypher-shell "CREATE DATABASE musicbrainz;"