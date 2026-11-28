from backend.app.db.migrate import apply_migrations
from backend.app.db.mongo_setup import setup

if __name__ == "__main__":
    apply_migrations()
    setup()
    print("PostgreSQL and MongoDB migrations complete.")
