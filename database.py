from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, AsyncGenerator, TypeVar, Type

from sqlalchemy import String, ForeignKey, DateTime, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase

from config import DEFAULT_CONFIG

UUIDString = String(36)


def uuid_generator() -> str:
    result = str(uuid.uuid4())

    return result


class Base(DeclarativeBase):
    pass


# 1 単語を表す。
# id, created_at, text を持ち、Documents と関連付けられる。
class Word(Base):
    __tablename__ = "words"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDString, primary_key=True, default=uuid_generator
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    text: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    associations: Mapped[List[WordDocumentAssociation]] = relationship(
        back_populates="word", cascade="all, delete-orphan"
    )


# 1 つのドキュメントを表す。
# id, created_at, content を持ち、Words と関連付けられる。
class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDString, primary_key=True, default=uuid_generator
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    raw_content: Mapped[str] = mapped_column(String, unique=False, nullable=False)
    processed_content: Mapped[str] = mapped_column(String, unique=False, nullable=False)

    associations: Mapped[List[WordDocumentAssociation]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


# 単語とドキュメントの関連付けを表す。
class WordDocumentAssociation(Base):
    __tablename__ = "word_document_associations"

    word_id: Mapped[str] = mapped_column(
        UUIDString, ForeignKey("words.id"), primary_key=True
    )
    document_id: Mapped[str] = mapped_column(
        UUIDString, ForeignKey("documents.id"), primary_key=True
    )

    word: Mapped[Word] = relationship(back_populates="associations")
    document: Mapped[Document] = relationship(back_populates="associations")


# データベースの初期化のための関数。
async def migrate() -> None:
    # Create an asynchronous engine
    async_engine: AsyncEngine = create_async_engine(
        DEFAULT_CONFIG.DATABASE_URL, echo=True
    )

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# AsyncSession を with 構文で使用できるようにするための関数。
# async with AsyncSession() as session:
# のようにすることで、with 構文でセッションを使用できる。
@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async_engine: AsyncEngine = create_async_engine(
        DEFAULT_CONFIG.DATABASE_URL, echo=True
    )
    async_session = async_sessionmaker(
        bind=async_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


T = TypeVar("T", bound=DeclarativeBase)


async def creates(records: list[T]) -> list[T]:
    """
    複数のレコードを作成する。
    records は、モデルのインスタンスのリストである必要がある。
    """
    async with get_session() as session:
        for record in records:
            session.add(record)

        # ID を取得するために flush する
        await session.flush()

    return records


async def gets(model: Type[T]) -> list[T]:
    async with get_session() as session:
        stmt = select(model)
        result = await session.execute(stmt)

        retval = list(result.scalars().all())

    return retval


async def get_all_documents() -> List[Document]:
    result = await gets(Document)

    return result


async def create_or_find_words(words: List[str]) -> List[Word]:
    """
    渡された単語のリストから、既存の単語を取得し、新しい単語を作成する。
    戻り値は、既存の単語と、新しく作られた単語のリスト。順番は保証しない。
    word はすべて小文字に変換される。
    """
    # words を小文字に変換
    words_lower_list = [word.lower() for word in words]
    # 重複を排除するため、set に変換
    words_lower_set = set(words_lower_list)

    async with get_session() as session:
        # 既存の単語を取得する。
        existing_words_query_result = await session.execute(
            Word.__table__.select().where(Word.text.in_(words_lower_set))
        )
        existing_word_records = existing_words_query_result.scalars().all()
        existing_words = {word.text.lower(): word for word in existing_word_records}

        # 新しい単語を作成
        new_words = []
        for word in words_lower_set:
            if word not in existing_words:
                new_word = Word(text=word)
                session.add(new_word)
                new_words.append(new_word)

        # 既存の単語と新しい単語を結合
        all_words = list(existing_words.values()) + new_words

        # ID を取得するために flush する
        await session.flush()

    return all_words


async def get_all_words() -> List[Word]:
    result = await gets(Word)

    return result


async def get_all_associations() -> List[WordDocumentAssociation]:
    result = await gets(WordDocumentAssociation)

    return result
