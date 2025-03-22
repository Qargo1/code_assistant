from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
import yaml
import os

def load_db_config():
    with open("config/base_config.yaml") as f:
        config = yaml.safe_load(f)
    return config['database']['postgres']

def get_engine():
    db_config = load_db_config()
    return create_engine(
        f"postgresql+psycopg2://{db_config['user']}:{db_config['password']}"
        f"@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
    )

def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("Database tables created successfully")

def get_session():
    return sessionmaker(bind=get_engine())()