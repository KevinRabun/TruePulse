#!/usr/bin/env python3
"""
Initialize Cosmos DB Emulator with TruePulse database and containers.

This script creates the required database and containers in the local Cosmos DB Emulator.
Run this once after starting the emulator to set up the local development environment.

Prerequisites:
1. Install Cosmos DB Emulator: https://aka.ms/cosmosdb-emulator
2. Start the emulator (it runs on https://localhost:8081)
3. Run this script: python scripts/init-cosmos-emulator.py

The emulator uses a well-known key that is safe for local development only.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "src" / "backend"
sys.path.insert(0, str(backend_path))

from azure.cosmos import PartitionKey
from azure.cosmos.aio import CosmosClient

# Cosmos DB Emulator connection details (well-known credentials)
EMULATOR_ENDPOINT = "https://localhost:8081"
EMULATOR_KEY = "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="
DATABASE_NAME = "truepulse"

# Container definitions with partition keys
CONTAINERS = [
    {"name": "users", "partition_key": "/id"},
    {"name": "polls", "partition_key": "/id"},
    {"name": "votes", "partition_key": "/poll_id"},
    {"name": "achievements", "partition_key": "/id"},
    {"name": "user-achievements", "partition_key": "/user_id"},
    {"name": "email-lookup", "partition_key": "/email_hash"},
    {"name": "username-lookup", "partition_key": "/username_lower"},
]


async def init_emulator():
    """Initialize the Cosmos DB Emulator with required database and containers."""
    print(f"🚀 Connecting to Cosmos DB Emulator at {EMULATOR_ENDPOINT}...")
    
    # Disable SSL verification for emulator's self-signed certificate
    client = CosmosClient(
        url=EMULATOR_ENDPOINT,
        credential=EMULATOR_KEY,
        connection_verify=False,
    )
    
    try:
        # Create database if it doesn't exist
        print(f"\n📁 Creating database: {DATABASE_NAME}")
        database = await client.create_database_if_not_exists(id=DATABASE_NAME)
        print(f"   ✅ Database '{DATABASE_NAME}' ready")
        
        # Create containers
        print(f"\n📦 Creating containers...")
        for container_def in CONTAINERS:
            container_name = container_def["name"]
            partition_key = container_def["partition_key"]
            
            try:
                await database.create_container_if_not_exists(
                    id=container_name,
                    partition_key=PartitionKey(path=partition_key),
                )
                print(f"   ✅ Container '{container_name}' (partition: {partition_key})")
            except Exception as e:
                print(f"   ⚠️  Container '{container_name}': {e}")
        
        print("\n✨ Cosmos DB Emulator initialization complete!")
        print("\n📋 Next steps:")
        print("   1. Copy .env.example to .env in src/backend/")
        print("   2. The emulator settings are pre-configured")
        print("   3. Start the backend: cd src/backend && uvicorn main:app --reload")
        print("   4. Start the frontend: cd src/frontend && npm run dev")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Make sure Cosmos DB Emulator is running")
        print("   2. Open https://localhost:8081/_explorer/index.html in browser")
        print("   3. If certificate error, add exception or install emulator cert")
        raise
    finally:
        await client.close()


if __name__ == "__main__":
    print("=" * 60)
    print("TruePulse - Cosmos DB Emulator Initialization")
    print("=" * 60)
    asyncio.run(init_emulator())
