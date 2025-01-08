#  """
#  Copyright 2024 lepen - All Rights Reserved
#  Created by lepen on 2024-12-04 22:46:43
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2024-12-04 08:06:30
#  File: seed.py
#  Description:
#  """

import asyncio
import os
from datetime import datetime

import pytz
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
                "inserted_at": datetime.now(tz=pytz.UTC),
                "inserted_by": "seeder"
            },
            {
                "username": "user1",
                "email": "user1@example.com",
                "password": pwd_context.hash("user"),
                "name": "User One",
                "active": True,
                "inserted_at": datetime.now(tz=pytz.UTC),
                "inserted_by": "seeder"
            },
            {
                "username": "user2",
                "email": "user2@example.com",
                "password": pwd_context.hash("user"),
                "name": "User Two",
                "active": True,
                "inserted_at": datetime.now(tz=pytz.UTC),
                "inserted_by": "seeder"
            }
        ]

        roles = [{"name": "Admin", "description": "Administrator with full access rights",
                  "inserted_at": datetime.now(tz=pytz.UTC),
                  "inserted_by": "seeder"},
                 {"name": "Farmer", "description": "User responsible for farm management",
                  "inserted_at": datetime.now(tz=pytz.UTC),
                  "inserted_by": "seeder"},
                 {"name": "Technician", "description": "User responsible for technical maintenance",
                  "inserted_at": datetime.now(tz=pytz.UTC),
                  "inserted_by": "seeder"}
                 ]

        # Insert users into the database
        result_users = await database.users.insert_many(users)
        result_roles = await database.roles.insert_many(roles)

        user_roles = [
            {
                "user_id": result_users.inserted_ids[0],
                "role_id": result_roles.inserted_ids[0]
            },
            {
                "user_id": result_users.inserted_ids[0],
                "role_id": result_roles.inserted_ids[1]
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
        print(user_roles)

        await database.user_roles.insert_many(user_roles)

        print("Initial data has been seeded.")
    except Exception as e:
        print(f"An error has occurred: {e}")
        raise e


async def seed_graph():
    try:
        # Connect to the database
        client = AsyncIOMotorClient(
            f"mongodb://{os.getenv('MONGO_USER')}:{os.getenv('MONGO_PASS')}@{os.getenv('MONGO_HOST')}:{os.getenv('MONGO_PORT')}/{os.getenv('MONGO_DB')}?authSource=admin"
        )
        database = client[os.getenv('MONGO_DB')]
        print(f"Database connection established")

        # Initial users data
        widgets = [
            {
                "name": "Metric",
                "description": "Display the metric",
                "category": "metrics",
                "icon": "bi bi-hash",
                "active": True,
                "inserted_at": datetime.now(tz=pytz.UTC),
                "inserted_by": "seeder",
                "updated_at": None,
                "updated_by": None,
            },
            {
                "name": "Thermometer",
                "description": "Display the thermometer",
                "category": "metrics",
                "icon": "bi bi-thermometer-half",
                "active": True,
                "inserted_at": datetime.now(tz=pytz.UTC),
                "inserted_by": "seeder",
                "updated_at": None,
                "updated_by": None,
            },
            {
                "name": "Gauge",
                "description": "Display the gauge",
                "category": "metrics",
                "icon": "bi bi-speedometer",
                "active": True,
                "inserted_at": datetime.now(tz=pytz.UTC),
                "inserted_by": "seeder",
                "updated_at": None,
                "updated_by": None,
            },
            {
                "name": "Indicator",
                "description": "Display the indicator",
                "category": "metrics",
                "icon": "bi bi-app-indicator",
                "active": True,
                "inserted_at": datetime.now(tz=pytz.UTC),
                "inserted_by": "seeder",
                "updated_at": None,
                "updated_by": None,
            },
            {
                "name": "Tank",
                "description": "Display the tank",
                "category": "metrics",
                "icon": "bi bi-droplet",
                "active": True,
                "inserted_at": datetime.now(tz=pytz.UTC),
                "inserted_by": "seeder",
                "updated_at": None,
                "updated_by": None,
            },
            {
                "name": "Battery",
                "description": "Display the battery",
                "category": "metrics",
                "icon": "bi bi-battery-full",
                "active": True,
                "inserted_at": datetime.now(tz=pytz.UTC),
                "inserted_by": "seeder",
                "updated_at": None,
                "updated_by": None,
            },
            {
                "name": "Line chart",
                "description": "Display the for timeseries",
                "category": "charts",
                "icon": "bi bi-graph-up",
                "active": True,
                "inserted_at": datetime.now(tz=pytz.UTC),
                "inserted_by": "seeder",
                "updated_at": None,
                "updated_by": None,
            },
            {
                "name": "Bar chart",
                "description": "Compare the data",
                "category": "charts",
                "icon": "bi bi-bar-chart-line",
                "active": True,
                "inserted_at": datetime.now(tz=pytz.UTC),
                "inserted_by": "seeder",
                "updated_at": None,
                "updated_by": None,
            },
            {
                "name": "Pie chart",
                "description": "Display all of data",
                "category": "charts",
                "icon": "bi bi-pie-chart-fill",
                "active": True,
                "inserted_at": datetime.now(tz=pytz.UTC),
                "inserted_by": "seeder",
                "updated_at": None,
                "updated_by": None,
            },
        ]

        # Insert users into the database
        await database.widgets.insert_many(widgets)

        print("Initial data has been seeded.")
    except Exception as e:
        print(f"An error has occurred: {e}")
        raise e


async def seed_servers():
    try:
        # Connect to the database
        client = AsyncIOMotorClient(
            f"mongodb://{os.getenv('MONGO_USER')}:{os.getenv('MONGO_PASS')}@{os.getenv('MONGO_HOST')}:{os.getenv('MONGO_PORT')}/{os.getenv('MONGO_DB')}?authSource=admin"
        )
        database = client[os.getenv('MONGO_DB')]
        print(f"Database connection established")

        # Initial users data
        servers = [
            {
                "name": "MyMQTTServer",
                "environment": "development",
                "protocol": "mqtt",
                "host": "127.0.0.1",
                "ports": {
                    "mqtt": 1884,
                    "ws": 9001,
                },
                "parameters": {
                    "username": "uwais",
                    "password": "uwais",
                    "topics":
                        {
                            "publish": "data/response/",
                            "subscribe": "data/sensor/",
                            "subscribe_device": "data/device/sub/",
                            "unsubscribe_device": "data/device/unsub/"
                        },
                    "keep_alive": 60,
                    "qos": 1
                },
                "inserted_by": "seeder",
                "inserted_at": datetime.now(tz=pytz.UTC),
                "updated_by": None,
                "updated_at": None,
                "deleted_by": None,
                "deleted_at": None
            },
            {
                "name": "MyHTTPServer",
                "environment": "development",
                "protocol": "http",
                "host": "127.0.0.1",
                "ports": {
                    "http": 8001,
                    "https": 8002,
                },
                "parameters": {
                    "path": "/api/v1/",
                    "timeout": 30
                },
                "inserted_by": "seeder",
                "inserted_at": datetime.now(tz=pytz.UTC),
                "updated_by": None,
                "updated_at": None,
                "deleted_by": None,
                "deleted_at": None
            },
            {
                "name": "MyKafkaServer",
                "environment": "production",
                "protocol": "kafka",
                "host": "kafka.example.com",
                "ports": {
                    "http": 9002,
                    "ssl": 9003,
                },
                "parameters": {
                    "bootstrap_servers": [
                        "kafka1.example.com:9092",
                        "kafka2.example.com:9092"
                    ],
                    "topics": ["kafka_topic1", "kafka_topic2"],
                    "client_id": "kafka_client",
                    "group_id": "kafka_group"
                },
                "inserted_by": "seeder",
                "inserted_at": datetime.now(tz=pytz.UTC),
                "updated_by": None,
                "updated_at": None,
                "deleted_by": None,
                "deleted_at": None
            },
            {
                "name": "MyRabbitMQServer",
                "environment": "production",
                "protocol": "rabbitmq",
                "host": "rabbitmq.example.com",
                "ports": {
                    "http": 5672,
                    "ssl": 5673,
                },
                "parameters": {
                    "username": "rabbit_user",
                    "password": "rabbit_password",
                    "queues": ["queue1", "queue2"],
                    "exchange": "my_exchange",
                    "virtual_host": "/"
                },
                "inserted_by": "seeder",
                "inserted_at": datetime.now(tz=pytz.UTC),
                "updated_by": None,
                "updated_at": None,
                "deleted_by": None,
                "deleted_at": None
            }
        ]

        # Insert users into the database
        await database.servers.insert_many(servers)

        print("Initial data has been seeded.")
    except Exception as e:
        print(f"An error has occurred: {e}")
        raise e


if __name__ == "__main__":
    # asyncio.run(seed())
    asyncio.run(seed_servers())
