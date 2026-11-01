import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Mandate")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mandate.db")
SECRET_KEY = os.getenv("SECRET_KEY", "development-only-secret-change-me")
