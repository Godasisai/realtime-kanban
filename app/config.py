import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

PROJECT_NAME = "Julley Real-Time Collaborative Kanban Board"
VERSION = "1.0.0"
API_V1_PREFIX = "/api"

SECRET_KEY = os.getenv("SECRET_KEY", "julley-kanban-super-secret-jwt-key-2026-production-ready")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'kanban.db'}")

CORS_ORIGINS = ["*"]
STATIC_DIR = BASE_DIR / "static"
