from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

TagNome = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
TagCor = Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$")]


class TagBase(BaseModel):
    tagNome: TagNome
    tagCor: TagCor


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    tagNome: TagNome | None = Field(default=None)
    tagCor: TagCor | None = Field(default=None)


class TagInDBBase(TagBase):
    tagId: int
    tagEmpId: int
    tagAtivo: bool
    tagDataCriacao: datetime
    tagDataAtualizacao: datetime | None

    class Config:
        from_attributes = True


class TagResponse(TagInDBBase):
    pass


class TagListResponse(BaseModel):
    items: list[TagResponse]
    total: int
    page: int
    page_size: int


class TagResumo(BaseModel):
    tagId: int
    tagNome: str
    tagCor: str

    class Config:
        from_attributes = True
