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
                "active": True,
                "inserted_at": datetime.now(tz=timezone("Asia/Tokyo")).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                "inserted_by": "seeder"
            },
            {
                "username": "user1",
                "email": "user1@example.com",
                "password": pwd_context.hash("user"),
                "name": "User One",
                "active": True,
                "inserted_at": datetime.now(tz=timezone("Asia/Tokyo")).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                "inserted_by": "seeder"
            },
            {
                "username": "user2",
                "email": "user2@example.com",
                "password": pwd_context.hash("user"),
                "name": "User Two",
                "active": True,
                "inserted_at": datetime.now(tz=timezone("Asia/Tokyo")).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                "inserted_by": "seeder"
            }
        ]

        roles = [{"name": "Admin", "description": "Administrator with full access rights",
                  "inserted_at": datetime.now(tz=timezone("Asia/Tokyo")).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                  "inserted_by": "seeder"},
                 {"name": "Farmer", "description": "User responsible for farm management",
                  "inserted_at": datetime.now(tz=timezone("Asia/Tokyo")).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                  "inserted_by": "seeder"},
                 {"name": "Technician", "description": "User responsible for technical maintenance",
                  "inserted_at": datetime.now(tz=timezone("Asia/Tokyo")).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                  "inserted_by": "seeder"}
                 ]

        # Insert users into the database
        result_users = await database.users.insert_many(users)
        result_roles = await database.roles.insert_many(roles)

        user_roles=[
            {
                "user_id":result_users.inserted_ids[0],
                "role_id":result_roles.inserted_ids[0]
            },
            {
                "user_id": result_users.inserted_ids[1],
                "role_id": result_roles.inserted_ids[1]
            },
            {
                "user_id": result_users.inserted_ids[2],
                "role_id": result_roles.inserted_ids[2]
            }
        ]

        await database.user_roles.insert_many(user_roles)

        print("Initial data has been seeded.")
    except Exception as e:
        print(f"An error has occurred: {e}")
        raise e


if __name__ == "__main__":
    asyncio.run(seed())
