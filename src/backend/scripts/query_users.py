import asyncio

from sqlalchemy import text

from db.session import async_session


async def query_users():
    async with async_session() as session:
        result = await session.execute(text("SELECT id, email, username, display_name FROM users"))
        for row in result:
            print(f"ID: {row.id}, Email: {row.email}, Username: {row.username}, Display: {row.display_name}")


asyncio.run(query_users())
