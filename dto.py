from pydantic import BaseModel


class DocumentDTO(BaseModel):
    """
    Document の DTO (Data Transfer Object) クラス。
    """

    title: str
    raw_content: str
    processed_content: str | None = None
