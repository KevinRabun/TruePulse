import asyncio
from db.session import async_session
from sqlalchemy import text

async def query_users():
    async with async_session() as session:
        result = await session.execute(text("SELECT id, email, username, display_name FROM users"))
        for row in result:
            print(f"ID: {row.id}, Email: {row.email}, Username: {row.username}, Display: {row.display_name}")

asyncio.run(query_users())
