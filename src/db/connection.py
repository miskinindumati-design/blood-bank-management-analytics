from __future__ import annotations

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from src.config import MONGODB_DB, MONGODB_URI


class DatabaseConnection:
    def __init__(self, uri: str | None = None, database_name: str | None = None) -> None:
        self.uri = uri or MONGODB_URI
        self.database_name = database_name or MONGODB_DB
        self.client = None
        self.db = None

    def connect(self):
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=4000)
            self.client.admin.command("ping")
            self.db = self.client[self.database_name]
            return self.db
        except PyMongoError:
            self.close()
            raise ConnectionError(
                "Unable to connect to MongoDB. Check MONGODB_URI and ensure MongoDB is available."
            ) from None

    def close(self) -> None:
        if self.client is not None:
            self.client.close()
            self.client = None
            self.db = None


def get_database():
    connection = DatabaseConnection()
    try:
        database = connection.connect()
        return database, connection
    except ConnectionError:
        return None, connection


def get_database_connection() -> DatabaseConnection:
    return DatabaseConnection()
