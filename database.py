from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, AsyncGenerator, TypeVar, Type

from sqlalchemy import String, ForeignKey, DateTime, select, Boolean
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase

from config import DEFAULT_CONFIG
from dto import DocumentDTO

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

    title: Mapped[str] = mapped_column(String, unique=False, nullable=False)
    # 生のコンテンツ。例えば、テキストファイルの内容など。
    raw_content: Mapped[str] = mapped_column(String, unique=False, nullable=False)
    # 処理されたコンテンツ。ストップワードの除去などがすでに行われ、分かち書き形式になっている前提である。
    # 例: "吾輩 猫 名前"
    processed_content: Mapped[str | None] = mapped_column(
        String, unique=False, nullable=True
    )
    # 単語と関連付けられたかどうか
    is_associated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    associations: Mapped[List[WordDocumentAssociation]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


# 単語とドキュメントの関連付けを表す。
class WordDocumentAssociation(Base):
    __tablename__ = "word_document_associations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDString, primary_key=True, default=uuid_generator
    )
    word_id: Mapped[str] = mapped_column(
        UUIDString, ForeignKey("words.id"), nullable=False
    )
    document_id: Mapped[str] = mapped_column(
        UUIDString, ForeignKey("documents.id"), nullable=False
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
        DEFAULT_CONFIG.DATABASE_URL, echo=False
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


async def create_documents(contents: list[DocumentDTO]) -> List[Document]:
    """
    複数のドキュメントを作成する。
    documents は、Document モデルのインスタンスのリストである必要がある。
    """
    documents: list[Document] = []

    for content in contents:
        document = Document(
            title=content.title,
            raw_content=content.raw_content,
            processed_content=content.processed_content,
        )

        documents.append(document)

    created_documents = await creates(documents)

    return created_documents


async def get_all_documents() -> List[Document]:
    result = await gets(Document)

    return result


async def get_document_by_id(document_id: uuid.UUID) -> Document | None:
    """
    ID に基づいてドキュメントを取得する。
    ドキュメントが存在しない場合は None を返す。
    """
    async with get_session() as session:
        stmt = select(Document).where(Document.id == document_id)
        result = await session.execute(stmt)

    retval = result.scalars().one_or_none()

    return retval


async def get_by_document_ids(document_ids: List[uuid.UUID]) -> List[Document]:
    """
    ドキュメントの ID のリストに基づいてドキュメントを取得する。
    """
    async with get_session() as session:
        stmt = select(Document).where(Document.id.in_(document_ids))
        result = await session.execute(stmt)

    retval = list(result.scalars().all())

    return retval


async def get_all_documents_by_associated(associated: bool) -> List[Document]:
    """
    is_associated フィールドに基づいてドキュメントを取得する。
    associated が True の場合、関連付けられたドキュメントを取得し、
    False の場合は関連付けられていないドキュメントを取得する。
    """
    async with get_session() as session:
        stmt = select(Document).where(Document.is_associated == associated)
        result = await session.execute(stmt)

    retval = list(result.scalars().all())

    return retval


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
        stmt = select(Word).where(Word.text.in_(words_lower_set))
        existing_word_records = list((await session.execute(stmt)).scalars().all())
        existing_words = {word.text.lower() for word in existing_word_records}

        # 新しい単語を作成
        new_words = []
        for word in words_lower_set:
            if word not in existing_words:
                new_word = Word(text=word)
                session.add(new_word)
                new_words.append(new_word)

        # ID を取得するために flush する
        await session.flush()

        # 既存の単語と新しい単語を結合
        all_words = existing_word_records + new_words

    return all_words


async def get_all_words() -> List[Word]:
    result = await gets(Word)

    return result


async def associate_words_with_document(
    document_ids: list[uuid.UUID],
) -> List[WordDocumentAssociation]:
    """
    Document と Word の関連付けを作成する。
    Document の associations フラグが立っていれば、
    すでに関連付けられているとみなし、何もしない。
    同じ単語が複数回 Document に現れる場合は、
    複数の Association を作成する。
    """

    documents = await get_by_document_ids(document_ids)

    # 関係を作成
    associations = []
    for document in documents:
        # Document の processed_content を単語に分割
        words = document.processed_content.split() if document.processed_content else []

        # 単語を取得または作成
        word_records = await create_or_find_words(words)

        async with get_session() as session:
            for word in word_records:
                # WordDocumentAssociation を作成
                association = WordDocumentAssociation(
                    word_id=str(word.id),
                    document_id=str(document.id),
                )
                associations.append(association)
                session.add(association)

            # Document の is_associated フラグを True に設定
            document.is_associated = True

            # ID を取得するために flush する
            await session.flush()

    # 関連付けられた Association を返す
    return associations


async def get_all_associations() -> List[WordDocumentAssociation]:
    result = await gets(WordDocumentAssociation)

    return result


async def get_associations_by_document(
    document: Document,
) -> List[WordDocumentAssociation]:
    """
    Document に関連付けられた Association を取得する。
    """
    async with get_session() as session:
        stmt = select(WordDocumentAssociation).where(
            WordDocumentAssociation.document_id == document.id
        )
        result = await session.execute(stmt)

    retval = list(result.scalars().all())

    return retval


async def get_associations_by_word(word: Word) -> List[WordDocumentAssociation]:
    """
    Word に関連付けられた Association を取得する。
    """
    async with get_session() as session:
        stmt = select(WordDocumentAssociation).where(
            WordDocumentAssociation.word_id == word.id
        )
        result = await session.execute(stmt)

    retval = list(result.scalars().all())

    return retval
