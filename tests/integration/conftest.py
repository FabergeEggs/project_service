import uuid
import psycopg_pool
import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer

from migrations.migrate import up
from src.adapters.repository.postgres.project_repository import ProjectPostgresRepository


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:17") as pg:
        host = pg.get_container_host_ip()
        port = pg.get_exposed_port(5432)
        user = pg.username
        password = pg.password
        dbname = pg.dbname
        dsn = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        yoyo_dsn = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"
        up(yoyo_dsn)
        yield dsn


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def pool(postgres_container):
    async with psycopg_pool.AsyncConnectionPool(
        conninfo=postgres_container,
        min_size=1,
        max_size=2,
        open=False,
    ) as p:
        await p.open()
        yield p


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def project_repository(pool):
    return ProjectPostgresRepository(pool)


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def cleanup(pool):
    yield
    async with pool.connection() as conn:
        await conn.execute("DELETE FROM project_user_connection")
        await conn.execute("DELETE FROM post")
        await conn.execute("DELETE FROM task")
        await conn.execute("DELETE FROM project_tag_connection")
        await conn.execute("DELETE FROM project")
        await conn.execute("DELETE FROM tags")
        await conn.execute("DELETE FROM denorm_user")


@pytest_asyncio.fixture(loop_scope="session")
async def creator_id(project_repository) -> uuid.UUID:
    uid = uuid.uuid4()
    await project_repository.upsert_denorm_user(uid, {
        "name": "Test Creator",
        "avatar_url": "http://example.com/avatar.png",
    })
    return uid


@pytest_asyncio.fixture(loop_scope="session")
async def member_id(project_repository) -> uuid.UUID:
    uid = uuid.uuid4()
    await project_repository.upsert_denorm_user(uid, {
        "name": "Test Member",
        "avatar_url": "http://example.com/avatar.png",
    })
    return uid


@pytest_asyncio.fixture(loop_scope="session")
async def member_id_2(project_repository) -> uuid.UUID:
    uid = uuid.uuid4()
    await project_repository.upsert_denorm_user(uid, {
        "name": "Test Member 2",
        "avatar_url": "http://example.com/avatar.png",
    })
    return uid
