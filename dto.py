from pydantic import BaseModel


class RawAndProcessedContent(BaseModel):
    """
    生のコンテンツと処理済みコンテンツを保持するモデル。
    """

    raw_content: str
    processed_content: str | None = None
