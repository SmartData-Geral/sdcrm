from pydantic import BaseModel, Field


class EscopoAiCard(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=200)
    subtitulo: str = Field(default="", max_length=300)
    itens: list[str] = Field(default_factory=list)


class EscopoInicialAiResponse(BaseModel):
    visivel: bool = True
    titulo: str = Field(default="Fases do projeto", max_length=200)
    subtitulo: str = Field(default="Detalhamento dos itens da proposta", max_length=300)
    cards: list[EscopoAiCard] = Field(default_factory=list)


class EscopoAiGenerateResponse(BaseModel):
    escopo_inicial: EscopoInicialAiResponse
    provider: str
    model: str
