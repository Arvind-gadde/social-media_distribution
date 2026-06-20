"""Dev-only: create all tables from SQLAlchemy models (bypass alembic).

Project ships only a baseline migration; real schema lives in model files.
This script imports every domain's models so registration is complete, then
runs `Base.metadata.create_all` against the configured DATABASE_URL.
"""
import asyncio
import importlib
import pkgutil

from app.db.session import Base, engine


def _import_all_models() -> None:
    importlib.import_module("app.models.models")
    domains_pkg = importlib.import_module("app.domains")
    for _finder, name, _ispkg in pkgutil.iter_modules(domains_pkg.__path__):
        try:
            importlib.import_module(f"app.domains.{name}.models")
        except ModuleNotFoundError:
            continue


async def main() -> None:
    _import_all_models()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("schema created")


if __name__ == "__main__":
    asyncio.run(main())
