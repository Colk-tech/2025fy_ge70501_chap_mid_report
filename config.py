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

    CASES_SAVE_DIR: str = Field(
        default="./cases/",
        description="ケースの保存先ディレクトリ。デフォルトは ./cases/ で、存在しない場合は自動的に作成される。",
    )

    CASES_SEARCH_WORD: str = Field(
        default="図書館",
        description="ケース検索時に使用する単語。デフォルトは「図書館」。",
    )


DEFAULT_CONFIG = Config()
