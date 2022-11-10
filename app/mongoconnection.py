from pymongo import MongoClient
import os

#MONGODB_URL = "localhost:27017"
MONGODB_URL = os.environ["MONGODB_URL"]
USERNAME = "dbuser"
PASSWORD = "zehfblosvge6r5g46rh4tsjs65j4"

def get_db():
    #return MongoClient(f"mongodb://{MONGODB_URL}").test
    return MongoClient(
        host=MONGODB_URL,
        username = USERNAME,
        password = PASSWORD
        ).test