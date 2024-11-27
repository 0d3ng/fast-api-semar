import asyncio
import os
from datetime import datetime

from pytz import timezone
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed():
    try:
        # Connect to the database
        client = AsyncIOMotorClient(
            f"mongodb://{os.getenv('MONGO_USER')}:{os.getenv('MONGO_PASS')}@{os.getenv('MONGO_HOST')}:{os.getenv('MONGO_PORT')}/{os.getenv('MONGO_DB')}?authSource=admin"
        )
        database = client[os.getenv('MONGO_DB')]
        print(f"Database connection established")

        # Initial users data
        users = [
            {
                "username": "admin",
                "email": "admin@example.com",
                "password": pwd_context.hash("admin"),
                "name": "Admin User",
                "role": "admin",
                "active": True,
                "inserted_at": datetime.now(tz=timezone("Asia/Tokyo")).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                "inserted_by": "seeder"
            },
            {
                "username": "user1",
                "email": "user1@example.com",
                "password": pwd_context.hash("user"),
                "name": "User One",
                "role": "user",
                "active": True,
                "inserted_at": datetime.now(tz=timezone("Asia/Tokyo")).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                "inserted_by": "seeder"
            }
        ]

        # Insert users into the database
        await database.users.insert_many(users)

        print("Initial data has been seeded.")
    except Exception as e:
        print(f"An error has occurred: {e}")
        raise e
if __name__ == "__main__":
    asyncio.run(seed())
