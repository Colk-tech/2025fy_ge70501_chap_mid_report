from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, AsyncGenerator

from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase

from config import DEFAULT_CONFIG


def uuid_generator() -> uuid.UUID:
    return uuid.uuid4()


UUIDString = String(36)


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

    documents: Mapped[List[Document]] = relationship(
        "Document",
        secondary="word_document_associations",
        back_populates="words",
    )


# 1 つのドキュメントを表す。
# id, created_at, content を持ち、Words と関連付けられる。
class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDString, primary_key=True, default=uuid_generator
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    content: Mapped[str] = mapped_column(String, unique=False, nullable=False)

    associations: Mapped[List[WordDocumentAssociation]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    words: Mapped[List[Word]] = relationship(
        "Word",
        secondary="word_document_associations",
        back_populates="documents",
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
