"""Generate local Docker configuration; never print generated secrets or overwrite an existing file."""
import secrets
from pathlib import Path

if __name__ == "__main__":
    destination = Path(__file__).resolve().parents[1] / ".env.docker"
    password = secrets.token_urlsafe(32)
    with destination.open("x", encoding="utf-8") as output:
        output.write(f"""ENVIRONMENT=development
POSTGRES_PASSWORD={password}
DATABASE_URL=postgresql://cardiovanta:{password}@postgres:5432/cardiovanta
MONGODB_URI=mongodb://mongo:27017/cardiovanta?replicaSet=rs0
REDIS_URL=redis://redis:6379/0
AUTH_ENABLED=true
JWT_SIGNING_KEY={secrets.token_urlsafe(48)}
CRON_SECRET={secrets.token_urlsafe(48)}
APP_ORIGIN=http://localhost:3000
COOKIE_SECURE=false
CORS_ORIGINS=["http://localhost:3000"]
REALTIME_ENABLED=true
LLM_ENABLED=false
PAYMENTS_ENABLED=false
""")
    print("Created .env.docker. Run docker compose --env-file .env.docker up --build --wait.")
