import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import DB_NAME, DB_PASS, DB_USER, DB_HOST 

from .models import Base

# Database engine
async_engine = create_async_engine(f'postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}')
SQLALCHEMY_DATABASE_URI = f'postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}'
print(SQLALCHEMY_DATABASE_URI)

# Initialize models
async def create_tables():
    async with async_engine.begin() as conn:
        print("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created successfully")

async def get_tables():
    async with async_engine.connect() as conn:  
        tables = list(Base.metadata.tables.keys())  # Get table names
        return tables
    

if __name__ == "__main__":
    asyncio.run(create_tables())