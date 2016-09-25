from py2neo import Graph, authenticate

authenticate("localhost:7474", "neo4j", "skrebe")
graph = Graph("http://localhost:7474/db/data/")
