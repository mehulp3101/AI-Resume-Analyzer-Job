"""Optional MongoDB account storage, configured through environment variables."""
import os
from functools import lru_cache

MONGO_URI = os.getenv("MONGODB_URI", "").strip()
MONGO_DATABASE = os.getenv("MONGODB_DATABASE", "resume_analyzer")


@lru_cache(maxsize=1)
def database():
    from pymongo import MongoClient

    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    try:
        collection = client[MONGO_DATABASE]["users"]
        collection.create_index("email", unique=True)
        return client[MONGO_DATABASE]
    except Exception:
        client.close()
        raise


def users():
    return database()["users"]


def jobs():
    return list(database()["jobs"].find({}, {"_id": 0}).sort("id", 1))


def skill_aliases():
    return {
        row["name"]: row["aliases"]
        for row in database()["skills"].find({}, {"name": 1, "aliases": 1})
    }
