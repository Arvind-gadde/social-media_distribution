import os
import pytest
import pytest_asyncio
import asyncio
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


def _test_database_url(main_url: str) -> str:
    """Derive an isolated test-database URL so tests never touch the real DB.

    Honours an explicit ``TEST_DATABASE_URL`` override; otherwise appends a
    ``_test`` suffix to the configured database name. (The previous logic did a
    ``.replace("/contentflow", ...)`` that silently no-op'd because the real DB
    is named ``social-media-distribution`` — meaning tests ran against, and
    dropped tables in, the live dev database.)
    """
    explicit = os.getenv("TEST_DATABASE_URL")
    if explicit:
        return explicit
    base, sep, name = main_url.rpartition("/")
    return f"{base}{sep}{name}_test"


async def _ensure_database_exists(test_url: str) -> None:
    """Create the test database if it does not already exist (idempotent)."""
    base, _, dbname = test_url.rpartition("/")
    # Strip any query string from the db name segment (e.g. ?ssl=...).
    dbname = dbname.split("?", 1)[0]
    admin_engine = create_async_engine(f"{base}/postgres", isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": dbname}
            )
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{dbname}"'))
    finally:
        await admin_engine.dispose()


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a test database session."""
    from app.config import get_settings
    from app.db.session import Base
    # Import all model modules so they register on Base.metadata before create_all
    import app.models.models  # noqa: F401
    import app.domains.control.models  # noqa: F401
    import app.domains.execution.models  # noqa: F401
    import app.domains.intelligence.models  # noqa: F401

    settings = get_settings()
    # Always run against an isolated *_test database so the suite can never
    # drop tables in the live dev/prod database.
    db_url = _test_database_url(settings.DATABASE_URL)
    await _ensure_database_exists(db_url)

    engine = create_async_engine(db_url, echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.rollback()
    
    # Drop tables with CASCADE to handle FK dependencies
    from sqlalchemy import text
    async with engine.begin() as conn:
        for tbl in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f'DROP TABLE IF EXISTS "{tbl.name}" CASCADE'))

    await engine.dispose()


@pytest_asyncio.fixture
async def test_workspace(db_session: AsyncSession):
    """Create a test workspace."""
    from app.domains.control.models import Workspace
    from app.models.models import User
    
    # Create test user with unique email/username
    uid = uuid.uuid4()
    suffix = str(uid)[:8]
    user = User(
        id=uid,
        email=f"test-{suffix}@example.com",
        name="Test User",
        username=f"testuser-{suffix}",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    # Create test workspace with unique slug per fixture invocation
    ws_id = uuid.uuid4()
    workspace = Workspace(
        id=ws_id,
        slug=f"test-workspace-{str(ws_id)[:8]}",
        name="Test Workspace",
        owner_id=user.id,
    )
    db_session.add(workspace)
    await db_session.commit()
    
    yield workspace
    
    # Cleanup
    await db_session.rollback()


@pytest_asyncio.fixture
async def test_budget_policy(db_session: AsyncSession, test_workspace):
    """Create a test budget policy."""
    from app.domains.control.models import BudgetPolicy
    
    policy = BudgetPolicy(
        id=uuid.uuid4(),
        workspace_id=test_workspace.id,
        monthly_llm_budget_usd=100.0,
        max_cost_per_run_usd=10.0,
        approval_required_above_usd=50.0,
        hard_stop_on_budget=False,
        auto_downgrade_threshold_pct=80,
    )
    db_session.add(policy)
    await db_session.commit()
    
    yield policy
    
    # Cleanup
    await db_session.rollback()


# Legacy fixture alias
@pytest_asyncio.fixture
async def async_db_session(db_session):
    """Legacy alias for db_session."""
    return db_session
