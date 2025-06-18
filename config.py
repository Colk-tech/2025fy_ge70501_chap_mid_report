from pydantic import Field
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """
    このアプリケーションのための設定ファイル。
    """

    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./data.sqlite3",
        description="データベースの URL で、デフォルトは直下のディレクトリを用いる。",
    )


DEFAULT_CONFIG = Config()
