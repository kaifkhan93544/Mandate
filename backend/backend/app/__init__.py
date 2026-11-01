import os
from dotenv import load_dotenv

load_dotenv()

SIGNING_SECRET = os.getenv(
    "MANDATE_SIGNING_SECRET",
    "local-development-only-change-me"
).encode()

DATABASE_PATH = os.getenv("DATABASE_PATH", "./mandate.db")
