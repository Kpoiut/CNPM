"""Integration fixtures chạy transaction-isolated trên PostgreSQL thật."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from uuid import uuid4


@pytest.fixture
def db_session():
    """Mỗi test dùng savepoint; mọi commit của API được rollback khi kết thúc."""
    from src.backend.database import engine

    assert engine.dialect.name == "postgresql"
    connection = engine.connect()
    outer_transaction = connection.begin()
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection,
        join_transaction_mode="create_savepoint",
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    """FastAPI client dùng đúng PostgreSQL schema đã migrate."""
    from src.backend.database import get_db as database_get_db
    from src.backend.deps import get_db as deps_get_db
    from src.backend.main import app

    def override_get_db():
        yield db_session

    app.dependency_overrides[database_get_db] = override_get_db
    app.dependency_overrides[deps_get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(database_get_db, None)
        app.dependency_overrides.pop(deps_get_db, None)


@pytest.fixture
def auth_user(db_session):
    """Account thường dùng để kiểm tra lịch sử dự đoán theo user."""
    from src.backend.auth.models import User

    suffix = uuid4().hex[:10]
    user = User(
        username=f"it_user_{suffix}",
        email=f"it_user_{suffix}@example.test",
        hashed_password="test-hash",
        role="user",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session):
    """Admin test dùng để duyệt feedback."""
    from src.backend.auth.models import User

    suffix = uuid4().hex[:10]
    user = User(
        username=f"it_admin_{suffix}",
        email=f"it_admin_{suffix}@example.test",
        hashed_password="test-hash",
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def authenticated_client(client, auth_user):
    """Client đã đăng nhập bằng account thường."""
    from src.backend.auth.dependencies import get_current_user, get_optional_user
    from src.backend.main import app

    async def override_user():
        return auth_user

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_optional_user] = override_user
    try:
        yield client, auth_user
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_user, None)


@pytest.fixture
def admin_client(client, admin_user):
    """Client đã đăng nhập bằng admin."""
    from src.backend.auth.dependencies import get_current_user, get_optional_user
    from src.backend.main import app

    async def override_admin():
        return admin_user

    app.dependency_overrides[get_current_user] = override_admin
    app.dependency_overrides[get_optional_user] = override_admin
    try:
        yield client, admin_user
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_user, None)
