import os
import asyncio
import asyncpg
from dotenv import load_dotenv
from passlib.context import CryptContext

load_dotenv()
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

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
    
    # Split schema into individual commands
    commands = schema.split(";")
    for cmd in commands:
        if cmd.strip():
            await conn.execute(cmd)
    
    # Seed default local admin user
    admin_user = "admin"
    admin_pass = "password123" # In production, this should be changed immediately
    hashed_pass = pwd_context.hash(admin_pass)
    
    await conn.execute(
        "INSERT INTO local_users (username, hashed_password, full_name) VALUES ($1, $2, $3) ON CONFLICT (username) DO NOTHING",
        admin_user, hashed_pass, "System Administrator"
    )
    
    await conn.close()
    print("Database initialized successfully with local admin fallback.")

if __name__ == "__main__":
    asyncio.run(init())
