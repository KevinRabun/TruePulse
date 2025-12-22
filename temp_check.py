import asyncio
import os
os.chdir('/app')
from db.session import get_engine
from sqlalchemy import text
async def main():
    engine = get_engine()
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' ORDER BY ordinal_position"))
        cols = [r[0] for r in result.fetchall()]
        for c in cols:
            print(c)
asyncio.run(main())
