import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def init():
    conn = await asyncpg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD"),
        database=os.getenv("POSTGRES_DATABASE", "security_db")
    )
    
    with open("schema.sql", "r") as f:
        schema = f.read()
    
    # Split schema into individual commands (very simple split for this case)
    commands = schema.split(";")
    for cmd in commands:
        if cmd.strip():
            await conn.execute(cmd)
    
    await conn.close()
    print("Database initialized successfully.")

if __name__ == "__main__":
    asyncio.run(init())
