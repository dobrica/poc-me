from neo4j import GraphDatabase
from configparser import ConfigParser

config = ConfigParser()
config.read("config.ini")

graphdb = GraphDatabase.driver(uri=config["DEF"]["DB_URI"], auth=(config["DEF"]["DB_USERNAME"], config["DEF"]["DB_PASSWORD"]))

try:
    graphdb.verify_connectivity()
except:
    exit( "Database connection failed!")