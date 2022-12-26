import dbConnection
from configparser import ConfigParser

config = ConfigParser()
config.read("config.ini")

def get_answer(query):
    session = dbConnection.graphdb.session(database=config["DEF"]["DB_NAME"])
    answer = ""
    nodes = session.run(query)
    for node in nodes:
        if str(node["var2"]["title"]) != "None":
            answer += node["var2"]["title"] + "\n"
        if str(node["var2"]["name"]) != "None":
            answer += node["var2"]["name"] + "\n"
    if str(answer.strip()) == "":
        answer = "Nothing was found!" + "\n"
    session.close()
    return answer