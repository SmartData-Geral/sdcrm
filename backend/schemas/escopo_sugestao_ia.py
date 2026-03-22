from pydantic import BaseModel, Field


class EscopoSugestaoBloco(BaseModel):
    titulo: str = Field(default="", max_length=300)
    subtitulo: str = Field(default="", max_length=500)
    itens: list[str] = Field(default_factory=list)


class EscopoSugestaoIaResponse(BaseModel):
    blocos: list[EscopoSugestaoBloco] = Field(default_factory=list)
    observacoes: str = Field(default="", max_length=4000)
    provider: str = ""
    model: str = ""
