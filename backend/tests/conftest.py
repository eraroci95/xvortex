import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest  # noqa: E402

try:  # API fixtures need the full dependency set; pure-logic tests run without it.
    import argon2  # noqa: F401
    import fastapi  # noqa: F401
    import sqlalchemy  # noqa: F401
    HAVE_API_DEPS = True
except ImportError:
    HAVE_API_DEPS = False

if HAVE_API_DEPS:
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.api.auth import reset_limiters
    from app.core.security import hash_password
    from app.db import get_db
    from app.main import app
    from app.models import Base, User, UserSettings
    from tests.helpers import PASSWORD

    @pytest.fixture()
    def client():
        """TestClient on an in-memory SQLite DB with an admin and a regular user. `client.Session` opens DB sessions."""
        engine = create_engine("sqlite+pysqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine, expire_on_commit=False)

        def override():
            with Session() as s:
                yield s

        app.dependency_overrides[get_db] = override
        reset_limiters()
        with Session() as s:
            for email, admin in (("admin@example.com", True), ("user@example.com", False)):
                u = User(email=email, password_hash=hash_password(PASSWORD), display_name=email, is_admin=admin)
                s.add(u)
                s.flush()
                s.add(UserSettings(user_id=u.id))
            s.commit()
        c = TestClient(app)
        c.Session = Session
        yield c
        app.dependency_overrides.clear()
