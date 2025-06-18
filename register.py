import asyncio
import sys
from copy import deepcopy
from pathlib import Path

from MeCab import Tagger  # type: ignore[import-untyped]
from ja_stopword_remover.remover import StopwordRemover  # type: ignore[import-untyped]

from database import Document, create_documents
from dto import RawAndProcessedContent

# 除去する日本語の文字。
REMOVE_CHARS = [
    "、",
    "。",
    "「",
    "」",
    "（",
    "）",
    "［",
    "］",
    "｛",
    "｝",
    "・",
    "ー",
    "…",
    "！",
    "？",
    "；",
    "：",
    "、",
    "。",
    "・",
    "ー",
    "…",
    "「",
    "」",
    "（",
    "）",
]


def get_file_data(file_paths: list[Path]) -> list[RawAndProcessedContent]:
    contents: list[RawAndProcessedContent] = []
    for file_path in file_paths:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        print(f"Registering document from {file_path}")

        # ファイルの内容を読み込む
        content = file_path.read_text(encoding="utf-8")
        # RawAndProcessedContent モデルを使用してコンテンツを作成
        raw_and_processed_content = RawAndProcessedContent(
            raw_content=content,
            processed_content=None,
        )
        contents.append(raw_and_processed_content)

    return contents


def process_content(content: RawAndProcessedContent) -> RawAndProcessedContent:
    """
    コンテンツを処理する関数。
    以下の処理を行う:
    - 空白を正規化し、改行を " " に置換する。
    - 特殊文字や句読点などを削除する。
    - 分かち書きする。
      分かち書きは、オープンソースの mecab を用いる。
    - ストップワードを除去する。
      ストップワードは、オープンソースの ja_stopword_remover を用いる。
    """
    processed_text = deepcopy(content.raw_content)

    # 空白を正規化し、改行を " " に置換する
    processed_text = processed_text.replace("\n", " ").replace("\r", " ").strip()

    # 特殊文字を削除
    print("Now in progress of removing special characters...")
    for char in REMOVE_CHARS:
        processed_text = processed_text.replace(char, "")

    # mecab を用いて分かち書きする
    # noinspection SpellCheckingInspection
    tagger = Tagger("-Owakati")
    # Mecab のバグ回避のため空文字をパースさせておく
    tagger.parse("")
    # 分かち書きの結果を取得
    processed_text = tagger.parse(processed_text)
    # noinspection SpellCheckingInspection
    print("Now in progress of wakati-gaki...")

    # ストップワードを除去
    print("Now in progress of stopword removal...")
    print("This may take a while, please wait patiently...")
    stopword_removed = StopwordRemover().remove([processed_text.split()])
    # ストップワード除去の結果を再度文字列に変換
    processed_text = " ".join(stopword_removed[0])

    result = RawAndProcessedContent(
        raw_content=content.raw_content, processed_content=processed_text
    )

    return result


async def register_documents(contents: list[RawAndProcessedContent]) -> None:
    """
    渡された file_paths の各ファイルをドキュメントとして登録する。
    """
    print("Registering documents...")

    documents = []
    for content in contents:
        # RawAndProcessedContent モデルを使用してドキュメントを作成
        documents.append(
            Document(
                raw_content=content.raw_content,
                processed_content=content.processed_content,
            )
        )

    results = await create_documents(contents)

    print(f"Registered {len(results)} documents successfully.")


async def main() -> None:
    # 登録するファイルのパスを実行時引数から取得
    if len(sys.argv) < 2:
        print("Usage: python register.py <file1> <file2> ...")
        sys.exit(1)

    file_paths = [Path(arg) for arg in sys.argv[1:]]
    contents = get_file_data(file_paths)

    processed_contents: list[RawAndProcessedContent] = []
    for content in contents:
        processed_content = process_content(content)
        processed_contents.append(processed_content)

    # ドキュメントを登録
    await register_documents(processed_contents)


if __name__ == "__main__":
    asyncio.run(main())
