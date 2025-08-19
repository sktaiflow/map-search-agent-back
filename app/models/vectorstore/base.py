import uuid
from sqlalchemy.orm import declarative_base
from sqlalchemy import select, update, inspect
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy import Column, DateTime, func, delete
from sqlalchemy.dialects.postgresql import insert
from typing import Optional, Type, TypeVar
from sqlalchemy import text
from contextvars import ContextVar, Token


from datetime import datetime, timedelta, timezone
from utils.logger import logger
from utils.decorators import session_required

_T = TypeVar("_T", bound="BaseModel")

Base = declarative_base()


class BaseModel(Base):
    __tablename__ = None
    __abstract__ = True
    _session_ctx: ContextVar[AsyncSession | None] = ContextVar("session", default=None)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    expire_at = Column(DateTime(timezone=True), nullable=True, index=True)
    EXPIRE_DAYS = 30  # 30 days
    USE_HNSW = True

    @classmethod
    async def create_table_and_hnsw_index(
        cls,
        engine: AsyncEngine = None,
        vector_column: str = "vector",
        m: int = 16,
        ef_construction: int = 64,
    ):
        """
        테이블 및 (옵션) HNSW VS IVFFLAT 중 HNSW 인덱스를 생성합니다. -> HNSW로 default 설정 (정교한 검색 결과를 위해)
        이미 테이블이 존재하면 PASS.
        """
        async with engine.begin() as conn:
            logger.info("Ensuring 'vector' extension is installed (if not exists)")
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

            logger.info("'vector' extension is installed (if not exists)")

            def _has_table(sync_conn):
                """inspect 함수는 sync 함수이므로, 비동기 커넥션에서 사용하기 위해 래핑함"""
                insp = inspect(sync_conn)
                return insp.has_table(cls.__tablename__)

            table_exists = await conn.run_sync(_has_table)
            logger.info(f"Checking if table '{cls.__tablename__}' exists: {table_exists}")

            if not table_exists:
                logger.info(f"Table {cls.__tablename__} does not exist...")
            else:
                logger.info(f"Table '{cls.__tablename__}' already exists. Skipping.")

        # 인덱스는 IF NOT EXISTS로 처리
        if cls.USE_HNSW:
            index_name = f"idx_{cls.__tablename__}_{vector_column}_hnsw"
            async with engine.begin() as conn:
                logger.info("Ensuring 'vector' extension is installed (if not exists)")
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

                logger.info(f"Creating HNSW index '{index_name}' (if not exists)")
                await conn.execute(
                    text(
                        f"""
                        CREATE INDEX IF NOT EXISTS {index_name}
                        ON {cls.__tablename__}
                        USING hnsw ({vector_column} vector_cosine_ops)
                        WITH (m = {m}, ef_construction = {ef_construction});
                    """
                    )
                )

    @classmethod
    def set_session(cls: Type[_T], session: AsyncSession) -> Token:
        return cls._session_ctx.set(session)

    @classmethod
    def get_session(cls) -> AsyncSession:
        session = cls._session_ctx.get()
        if session is None:
            raise RuntimeError("세션이 설정되지 않았습니다.")
        return session

    @classmethod
    def reset_session(cls: Type[_T], token: Token) -> None:
        cls._session_ctx.reset(token)

    @classmethod
    @session_required
    async def aselect(cls, session: AsyncSession, id_: str, **kwargs) -> Optional[_T]:
        if isinstance(id_, str):
            id_ = uuid.UUID(id_)
        result = await session.execute(select(cls).where(cls.id == id_))
        return result.scalar_one_or_none()

    @session_required
    async def ainsert(self, session: AsyncSession) -> _T:
        """
        insert a new record into the vector store
        """
        now = datetime.now(tz=timezone.utc)
        self.created_at = now
        self.updated_at = now
        if self.expire_at is None:
            self.expire_at = now + timedelta(days=self.EXPIRE_DAYS)

        session.add(self)
        await session.commit()
        await session.refresh(self)
        return self

    @classmethod
    @session_required
    async def aupdate_partial(cls: Type[_T], session: AsyncSession, id_, values: dict) -> None:
        """
        update a record in the vector store
        """
        if isinstance(id_, str):
            id_ = uuid.UUID(id_)

        now = datetime.now(tz=timezone.utc)
        values["updated_at"] = now

        # expire_at이 명시적으로 제공되지 않은 경우에만 기본값 설정
        if "expire_at" not in values or values["expire_at"] is None:
            values["expire_at"] = now + timedelta(days=cls.EXPIRE_DAYS)

        await session.execute(update(cls).where(cls.id == id_).values(**values))
        await session.commit()

    @session_required
    async def aupdate(self, session: AsyncSession) -> _T:
        """
        DB에 인스턴스의 변경사항을 반영 (update).
        """

        now = datetime.now(tz=timezone.utc)
        if self.created_at is None:
            self.created_at = now
        self.updated_at = now

        # expire_at이 명시적으로 설정되지 않은 경우에만 기본값 적용
        if not hasattr(self, "expire_at") or self.expire_at is None:
            self.expire_at = now + timedelta(days=self.EXPIRE_DAYS)

        session.add(self)
        await session.commit()
        await session.refresh(self)
        return self

    @classmethod
    @session_required
    async def alist(cls: Type[_T], session: AsyncSession, **filters) -> list[_T]:
        """
        조건에 맞는 row들을 모두 조회합니다.
        예: await Document.alist(user_id=1)
        """

        stmt = select(cls).filter_by(**filters)
        result = await session.execute(stmt)
        return result.scalars().all()

    @classmethod
    @session_required
    async def aexists(cls: Type[_T], session: AsyncSession, **filters) -> bool:
        """
        조건에 맞는 row가 존재하는지 확인합니다.
        예: await Document.aexists(user_id=1)
        """

        stmt = select(cls).filter_by(**filters).limit(1)
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None

    @classmethod
    @session_required
    async def acount(cls: Type[_T], session: AsyncSession, **filters) -> int:
        """
        조건에 맞는 row의 개수를 반환합니다.
        """
        stmt = select(func.count()).select_from(cls).filter_by(**filters)
        result = await session.execute(stmt)
        return result.scalar_one()

    @classmethod
    @session_required
    async def asearch_by_vector(
        cls: Type[_T],
        session: AsyncSession,
        embedding: list[float],
        *,
        limit: int = 3,
        filters: dict = None,
        similarity_cutoff: float = 0.3,
    ) -> list[tuple[_T, float]]:
        """
        Embedding 검색을 수행합니다.

        Args:
            embedding (list[float]): 검색할 벡터
            limit (int): 검색 결과 제한
            filters (dict, optional): 추가 필터 조건
            similarity_cutoff (float): 최소 유사도 점수 (0.0 ~ 1.0). 기본값 0.35

        Returns:
            list[tuple[_T, float]]: 검색된 객체와 점수 리스트
        """
        filters = filters or {}
        vector_column = getattr(cls, "VECTOR_COLUMN", "vector")

        stmt = text(
            f"""
            WITH similarity_calc AS (
                SELECT
                    public.{cls.__tablename__}.*,
                    1 - ({vector_column} <=> :embedding) AS score
                FROM
                    public.{cls.__tablename__}
                WHERE {cls.__tablename__}.{vector_column} IS NOT NULL
                {"AND " + " AND ".join(f"{key} = :{key}" for key in filters.keys()) if filters else ""}
            )
            SELECT * FROM similarity_calc
            WHERE score >= :similarity_cutoff
            ORDER BY score DESC
            LIMIT :limit
            """
        )

        # Execute the query
        params = {
            "embedding": f"[{', '.join(map(str, embedding))}]",
            **filters,
            "limit": limit,
            "similarity_cutoff": similarity_cutoff,
        }
        result = await session.execute(stmt, params)
        rows = result.mappings().all()  # 컬럼 이름으로 안전하게 가져옴

        objects_and_scores = [
            (cls(**{col.name: row[col.name] for col in cls.__table__.columns}), row["score"])
            for row in rows
        ]

        return objects_and_scores

    @classmethod
    @session_required
    async def asearch_by_vectors(
        cls,
        session: AsyncSession,
        filters: dict,
        embeddings: list[float] | list[list[float]],
        limit: int = 100,
        similarity_cutoff: float = 0.35,
    ):
        """
        여러개의 Embedding 벡터를 기반으로 검색을 수행합니다.

        Args:
            session (AsyncSession): DB 세션
            filters (dict): 필터 조건 (예: user_id 등)
            embeddings (list[float] | list[list[float]]): 검색할 벡터 또는 벡터 리스트
            limit (int): 검색 결과 제한 (기본: 100)
            similarity_cutoff (float): 최소 유사도 점수 (0.0 ~ 1.0, 기본: 0.35)

        Returns:
            list: 검색 결과 (memory, score) 튜플 리스트
        """
        vector_column = getattr(cls, "VECTOR_COLUMN", "vector")

        # 필터 조건 구성
        filter_conditions = []
        for key, value in filters.items():
            filter_conditions.append(f"{key} = :{key}")

        filter_sql = " AND ".join(filter_conditions) if filter_conditions else ""
        if filter_sql:
            filter_sql = f"AND {filter_sql}"

        # If a single vector is provided as a flat list, wrap it in another list
        if embeddings and (not isinstance(embeddings[0], list)):
            embeddings = [embeddings]

        try:
            embeddings_array = ", ".join(
                f"ARRAY[{', '.join(map(str, embedding))}]::vector" for embedding in embeddings
            )
        except Exception as e:
            raise ValueError(
                f"Failed to process embeddings: {e}. Embeddings must be a list of float lists."
            )

        # Raw SQL 쿼리 구성 - 여러 임베딩 지원
        stmt = text(
            f"""
            WITH input_vectors AS (
                SELECT UNNEST(ARRAY[{embeddings_array}]) AS query_vector
            ),
            similarity_calc AS (
                SELECT
                    public.{cls.__tablename__}.*,
                    1 - (input_vectors.query_vector <=> {cls.__tablename__}.{vector_column}) AS score
                FROM
                    input_vectors,
                    public.{cls.__tablename__}
                WHERE {cls.__tablename__}.{vector_column} IS NOT NULL
                {filter_sql}
                AND (memory_type = 'user_info' AND payload->>'category' IN ('extra_information', 'health_information', 'relationship'))
            )
            SELECT * FROM similarity_calc
            WHERE score >= :similarity_cutoff
            ORDER BY score DESC
            LIMIT :limit
            """
        )

        # 쿼리 파라미터 구성
        params = {**filters, "limit": limit, "similarity_cutoff": similarity_cutoff}
        # 쿼리 실행
        result = await session.execute(stmt, params)
        rows = result.fetchall()

        # 중복 제거 및 결과 처리
        seen = set()
        objects_and_scores = []

        for row in rows:
            obj_id = row[0]  # 첫 번째 열이 id로 가정합니다
            if obj_id not in seen:
                seen.add(obj_id)
                obj = cls(**{col.name: row[idx] for idx, col in enumerate(cls.__table__.columns)})
                objects_and_scores.append((obj, row[-1]))
            if len(objects_and_scores) >= int(limit):
                break

        return objects_and_scores

    @classmethod
    @session_required
    async def adelete(cls: Type[_T], session: AsyncSession, id_: str) -> Optional[_T]:
        """
        DB에서 인스턴스를 삭제합니다.
        """

        if isinstance(id_, str):
            id_ = uuid.UUID(id_)

        obj = await cls.aselect(session=session, id_=id_)
        if not obj:
            return None

        await session.delete(obj)
        await session.commit()
        return obj

    @classmethod
    @session_required
    async def abulk_delete_expired(cls: Type[_T], session: AsyncSession) -> _T:
        """
        만료된 데이터를 삭제(bulk delete)합니다.
        """

        stmt = delete(cls).where(cls.expire_at < func.now()).returning(cls.id)
        result = await session.execute(stmt)

        deleted_ids = result.scalars().all()
        logger.info(f"Bulk delete expired data: {deleted_ids}")
        await session.commit()
        return deleted_ids

    @classmethod
    @session_required
    async def aupsert(cls: Type[_T], session: AsyncSession, values: dict) -> _T:
        """
        Insert or Update by ID.
        """

        values = values or {}
        now = datetime.now(tz=timezone.utc)
        values["created_at"] = now
        values["updated_at"] = now

        # expire_at이 명시적으로 제공되지 않은 경우에만 기본값 설정
        if "expire_at" not in values or values["expire_at"] is None:
            values["expire_at"] = now + timedelta(days=cls.EXPIRE_DAYS)

        if isinstance(values.get("id"), str):
            values["id"] = uuid.UUID(values["id"])

        stmt = insert(cls).values(**values)

        update_dict = {
            key: stmt.excluded[key] for key in values if key not in ["id", "created_at"]
        }  # id, created_at 은 업데이트하지 않음

        stmt = stmt.on_conflict_do_update(index_elements=["id"], set_=update_dict)
        try:
            await session.execute(stmt)
            await session.commit()
        except Exception as e:
            print("Error: ", e)
            await session.rollback()
            raise
        return await cls.aselect(session=session, id_=values["id"])
