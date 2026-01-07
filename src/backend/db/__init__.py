"""Database module - Cosmos DB client management."""

from db.cosmos_session import (
    close_cosmos,
    cosmos_session,
    get_container,
    get_cosmos_client,
    get_cosmos_db,
    get_database,
)

__all__ = [
    "get_database",
    "get_cosmos_client",
    "get_cosmos_db",
    "get_container",
    "cosmos_session",
    "close_cosmos",
]
