# check_config.py
import yaml
from dotenv import load_dotenv

load_dotenv()

with open("config/base_config.yaml") as f:
    config = yaml.safe_load(f)

print("Current Configuration:")
print(f"Project Name: {config['project']['name']}")
print(f"Database Host: {config['database']['postgres']['host']}")
print(f"Log Level: {config['logging']['level']}")