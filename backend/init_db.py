"""Create all SQLAlchemy tables for a fresh database."""
from app.core.database import Base, engine
import app.models  # noqa: F401 — register models


def main():
    Base.metadata.create_all(bind=engine)
    print("Database tables created.")


if __name__ == "__main__":
    main()
