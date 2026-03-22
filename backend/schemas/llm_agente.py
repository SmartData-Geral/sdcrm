from pydantic import BaseModel, Field, computed_field, field_validator


AVISO_ESTRUTURA_JSON_PADRAO = (
    "Este agente exige resposta em JSON com estrutura fixa usada pelo sistema. "
    "Não remova as instruções que definem o formato JSON; alterações podem impedir o processamento automático."
)


class LlmAgenteResponse(BaseModel):
    agnId: int
    agnEmpId: int
    agnCodigo: str
    agnNome: str
    agnDescricao: str | None = None
    agnSystemPrompt: str
    agnLlmProvider: str
    agnLlmModel: str | None = None
    agnRespostaJsonEstruturada: bool
    agnAvisoEstrutura: str | None = None

    model_config = {"from_attributes": True}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def aviso_estrutura_exibicao(self) -> str | None:
        """Texto para exibir no cadastro quando a resposta tem JSON fixo."""
        if not self.agnRespostaJsonEstruturada:
            return None
        return (self.agnAvisoEstrutura or "").strip() or AVISO_ESTRUTURA_JSON_PADRAO


class LlmAgenteListResponse(BaseModel):
    items: list[LlmAgenteResponse]
    total: int


class LlmAgenteUpdate(BaseModel):
    agnSystemPrompt: str = Field(..., min_length=10)
    agnLlmProvider: str = Field(default="openai", max_length=40)
    agnLlmModel: str | None = Field(default=None, max_length=120)

    @field_validator("agnLlmModel", mode="before")
    @classmethod
    def empty_model_to_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s if s else None
        return v

    @field_validator("agnLlmProvider", mode="before")
    @classmethod
    def strip_provider(cls, v: str) -> str:
        return str(v).strip().lower() or "openai"
