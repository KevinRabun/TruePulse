"""
Azure Cosmos DB session management for document storage.

Uses async Cosmos DB SDK with DefaultAzureCredential for RBAC authentication.
This module provides a unified client for all Cosmos DB operations.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from azure.cosmos.aio import ContainerProxy, CosmosClient, DatabaseProxy
from azure.identity.aio import DefaultAzureCredential

from core.config import settings

logger = logging.getLogger(__name__)

# Container names
USERS_CONTAINER = "users"
POLLS_CONTAINER = "polls"
VOTES_CONTAINER = "votes"
ACHIEVEMENTS_CONTAINER = "achievements"
USER_ACHIEVEMENTS_CONTAINER = "user-achievements"
EMAIL_LOOKUP_CONTAINER = "email-lookup"
USERNAME_LOOKUP_CONTAINER = "username-lookup"
AUTH_CHALLENGES_CONTAINER = "auth-challenges"

# Global client instances (lazy-initialized)
_cosmos_client: CosmosClient | None = None
_database: DatabaseProxy | None = None
_credential: DefaultAzureCredential | None = None


async def get_cosmos_client() -> CosmosClient:
    """
    Get or create the Cosmos DB client.

    Supports two authentication modes:
    1. Connection string (for local development with Cosmos DB Emulator)
    2. DefaultAzureCredential/RBAC (for Azure deployment)

    The client is singleton and reused across requests.

    Returns:
        CosmosClient: Async Cosmos DB client
    """
    global _cosmos_client, _credential

    if _cosmos_client is None:
        # Check if using connection string (local emulator mode)
        if settings.AZURE_COSMOS_CONNECTION_STRING:
            # Parse connection string to extract endpoint and key
            # Format: AccountEndpoint=https://...;AccountKey=...;
            conn_parts = dict(
                part.split("=", 1) for part in settings.AZURE_COSMOS_CONNECTION_STRING.split(";") if "=" in part
            )
            endpoint = conn_parts.get("AccountEndpoint", "")
            key = conn_parts.get("AccountKey", "")

            if not endpoint or not key:
                raise ValueError("AZURE_COSMOS_CONNECTION_STRING must contain AccountEndpoint and AccountKey")

            # Create client with connection string auth
            # Disable SSL verification for emulator (self-signed cert)
            _cosmos_client = CosmosClient(
                url=endpoint,
                credential=key,
                connection_verify=not settings.AZURE_COSMOS_DISABLE_SSL,
            )
            logger.info(
                f"Initialized Cosmos DB client for {endpoint} (connection string mode, "
                f"SSL verification: {not settings.AZURE_COSMOS_DISABLE_SSL})"
            )
        else:
            # Use managed identity / DefaultAzureCredential (Azure deployment)
            if not settings.AZURE_COSMOS_ENDPOINT:
                raise ValueError("Either AZURE_COSMOS_ENDPOINT or AZURE_COSMOS_CONNECTION_STRING must be set")

            _credential = DefaultAzureCredential()
            _cosmos_client = CosmosClient(
                url=settings.AZURE_COSMOS_ENDPOINT,
                credential=_credential,
            )
            logger.info(f"Initialized Cosmos DB client for {settings.AZURE_COSMOS_ENDPOINT} (RBAC mode)")

    return _cosmos_client

    return _cosmos_client


async def get_database() -> DatabaseProxy:
    """
    Get the Cosmos DB database proxy.

    Returns:
        DatabaseProxy: Database proxy for the application database
    """
    global _database

    if _database is None:
        client = await get_cosmos_client()
        _database = client.get_database_client(settings.AZURE_COSMOS_DATABASE)
        logger.info(f"Connected to database: {settings.AZURE_COSMOS_DATABASE}")

    return _database


async def get_container(container_name: str) -> ContainerProxy:
    """
    Get a container proxy for the specified container.

    Args:
        container_name: Name of the container (e.g., 'users', 'polls')

    Returns:
        ContainerProxy: Container proxy for CRUD operations
    """
    database = await get_database()
    return database.get_container_client(container_name)


@asynccontextmanager
async def cosmos_session() -> AsyncGenerator[DatabaseProxy, None]:
    """
    Context manager for Cosmos DB operations.

    Unlike SQL databases, Cosmos DB doesn't have explicit transactions by default.
    This context manager provides a consistent interface and handles cleanup.

    Usage:
        async with cosmos_session() as db:
            container = db.get_container_client('users')
            user = await container.read_item(id='123', partition_key='123')

    Yields:
        DatabaseProxy: Database proxy for operations
    """
    try:
        db = await get_database()
        yield db
    except Exception as e:
        logger.error(f"Cosmos DB operation failed: {e}")
        raise


async def get_cosmos_db() -> AsyncGenerator[DatabaseProxy, None]:
    """
    FastAPI dependency to get Cosmos DB database.

    Usage:
        @router.get("/")
        async def endpoint(db: DatabaseProxy = Depends(get_cosmos_db)):
            container = db.get_container_client('users')
            ...

    Yields:
        DatabaseProxy: Database proxy for the request
    """
    db = await get_database()
    yield db


async def close_cosmos() -> None:
    """
    Close Cosmos DB connections.

    Should be called during application shutdown.
    """
    global _cosmos_client, _database, _credential

    if _cosmos_client is not None:
        await _cosmos_client.close()
        _cosmos_client = None
        _database = None
        logger.info("Closed Cosmos DB client")

    if _credential is not None:
        await _credential.close()
        _credential = None


# ============================================================================
# Utility Functions for Common Operations
# ============================================================================


async def create_item(container_name: str, item: dict[str, Any]) -> dict[str, Any]:
    """
    Create a new item in the specified container.

    Args:
        container_name: Container to create item in
        item: Item data (must include 'id' and partition key field)

    Returns:
        Created item with system properties
    """
    container = await get_container(container_name)
    return await container.create_item(body=item)


async def read_item(
    container_name: str,
    item_id: str,
    partition_key: str,
) -> dict[str, Any] | None:
    """
    Read an item by ID and partition key.

    Args:
        container_name: Container to read from
        item_id: The item's ID
        partition_key: The partition key value

    Returns:
        Item data or None if not found
    """
    container = await get_container(container_name)
    try:
        return await container.read_item(item=item_id, partition_key=partition_key)
    except Exception as e:
        if "NotFound" in str(e):
            return None
        raise


async def upsert_item(container_name: str, item: dict[str, Any]) -> dict[str, Any]:
    """
    Create or update an item in the specified container.

    Args:
        container_name: Container to upsert item in
        item: Item data (must include 'id' and partition key field)

    Returns:
        Upserted item with system properties
    """
    container = await get_container(container_name)
    return await container.upsert_item(body=item)


async def delete_item(
    container_name: str,
    item_id: str,
    partition_key: str,
) -> None:
    """
    Delete an item by ID and partition key.

    Args:
        container_name: Container to delete from
        item_id: The item's ID
        partition_key: The partition key value
    """
    container = await get_container(container_name)
    await container.delete_item(item=item_id, partition_key=partition_key)


async def query_items(
    container_name: str,
    query: str,
    parameters: list[dict[str, Any]] | None = None,
    partition_key: str | None = None,
    max_items: int | None = None,
) -> list[dict[str, Any]]:
    """
    Query items using SQL-like syntax.

    Args:
        container_name: Container to query
        query: Cosmos DB SQL query string
        parameters: Query parameters for parameterized queries
        partition_key: Optional partition key for scoped queries
        max_items: Maximum number of items to return

    Returns:
        List of matching items

    Example:
        results = await query_items(
            'users',
            'SELECT * FROM c WHERE c.email = @email',
            parameters=[{'name': '@email', 'value': 'user@example.com'}]
        )
    """
    container = await get_container(container_name)

    # Build query kwargs - note: enable_cross_partition_query is deprecated
    # in newer SDK versions and is automatically enabled when no partition_key
    query_kwargs: dict[str, Any] = {
        "query": query,
    }

    if parameters:
        query_kwargs["parameters"] = parameters

    if partition_key:
        query_kwargs["partition_key"] = partition_key

    if max_items:
        query_kwargs["max_item_count"] = max_items

    items: list[dict[str, Any]] = []
    async for item in container.query_items(**query_kwargs):
        items.append(item)
        if max_items and len(items) >= max_items:
            break

    return items


async def query_count(
    container_name: str,
    query: str,
    parameters: list[dict[str, Any]] | None = None,
    partition_key: str | None = None,
) -> int:
    """
    Execute a COUNT query and return the integer result.

    This is a convenience wrapper for queries using SELECT VALUE COUNT(1).

    Args:
        container_name: Name of the container to query
        query: The SQL query (should use SELECT VALUE COUNT(1))
        parameters: Query parameters
        partition_key: Optional partition key

    Returns:
        The count as an integer
    """
    results = await query_items(container_name, query, parameters, partition_key)
    if results and len(results) > 0:
        result = results[0]
        if isinstance(result, (int, float)):
            return int(result)
        return 0
    return 0
