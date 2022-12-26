from neo4j import Query
import dbUtil

# get 5 random artists
query="MATCH (var2:Artist) RETURN var2, rand() as r ORDER BY r LIMIT 5;"
# query = "MATCH (var2:Artist)-[:IS_FROM]-(s:Area {name: 'Serbia'}) RETURN var2;"

answer = dbUtil.get_answer(query)
print(answer)