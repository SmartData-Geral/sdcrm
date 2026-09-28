import os
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.mcp_crm.serializacao import (
    Nomes,
    carregar_autores,
    carregar_nomes,
    historico_item,
    oportunidade_completa,
    resumo_oportunidade,
    status_de,
)
from backend.tests.mcp_apoio import oportunidade_falsa

NOMES = Nomes(
    etapas={4: ("Proposta", "default")},
    usuarios={2: "Ana"},
    produtos={1: "BI"},
    origens={3: "Site"},
    motivos={9: "Preço"},
)


class CarregarNomesTests(unittest.TestCase):
    def test_uma_consulta_por_tabela_com_ids(self) -> None:
        db = MagicMock()
        db.execute.return_value.all.side_effect = [
            [(4, "Proposta", "default")],
            [(2, "Ana")],
            [(1, "BI")],
            [(3, "Site")],
            [(9, "Preço")],
        ]
        nomes = carregar_nomes(db, [oportunidade_falsa(opoMcaId=9), oportunidade_falsa(opoId=6, opoMcaId=9)])
        self.assertEqual(db.execute.call_count, 5)
        self.assertEqual(nomes, NOMES)

    def test_sem_ids_nao_consulta(self) -> None:
        db = MagicMock()
        vazia = oportunidade_falsa(opoEtkId=None, opoUsuResponsavelId=None, opoProId=None, opoCcoId=None)
        self.assertEqual(carregar_nomes(db, [vazia]), Nomes())
        db.execute.assert_not_called()

    def test_autores_do_historico(self) -> None:
        db = MagicMock()
        db.execute.return_value.all.return_value = [(3, "Carlos")]
        autores = carregar_autores(db, [SimpleNamespace(ophUsuId=3), SimpleNamespace(ophUsuId=None)])
        self.assertEqual(autores, {3: "Carlos"})


class FormatoTests(unittest.TestCase):
    def test_status_ativo_quando_sem_fechamento(self) -> None:
        self.assertEqual(status_de(oportunidade_falsa()), "ativo")
        self.assertEqual(status_de(oportunidade_falsa(opoStatusFechamento="ganho")), "ganho")

    def test_resumo(self) -> None:
        self.assertEqual(
            resumo_oportunidade(oportunidade_falsa(), NOMES),
            {
                "id": 5,
                "titulo": "BI para Acme",
                "contato": "Maria",
                "empresa": "Acme",
                "status": "ativo",
                "etapa": {"id": 4, "nome": "Proposta", "pipeline": "default"},
                "responsavel": {"id": 2, "nome": "Ana"},
                "temperatura": "quente",
                "lead_score": 8,
                "valor": 12000.0,
                "data_ultimo_contato": "2026-09-20",
            },
        )

    def test_completa_ativa_sem_fechamento_e_com_url(self) -> None:
        with patch.dict(os.environ, {"VITE_PUBLIC_BASE_URL": "https://crm.exemplo.com"}):
            dados = oportunidade_completa(oportunidade_falsa(), NOMES)
        self.assertNotIn("fechamento", dados)
        self.assertEqual(dados["produto"], {"id": 1, "nome": "BI"})
        self.assertEqual(dados["origem"], {"id": 3, "nome": "Site"})
        self.assertIsNone(dados["motivo_perda"])
        self.assertEqual(dados["url"], "https://crm.exemplo.com/oportunidades/5")
        self.assertEqual(dados["criado_em"], "2026-09-01T10:00:00")
        self.assertEqual(dados["dores"], "Planilhas")

    def test_completa_ganha_traz_fechamento(self) -> None:
        opo = oportunidade_falsa(
            opoStatusFechamento="ganho",
            opoDataFechamento=date(2026, 9, 25),
            opoFechadoRecorrencia=1,
            opoValorFechado=Decimal("15000.50"),
        )
        self.assertEqual(
            oportunidade_completa(opo, NOMES)["fechamento"],
            {"data": "2026-09-25", "tipo": "projeto", "valor": 15000.5},
        )

    def test_id_sem_nome_carregado_nao_quebra(self) -> None:
        dados = resumo_oportunidade(oportunidade_falsa(opoUsuResponsavelId=77), NOMES)
        self.assertEqual(dados["responsavel"], {"id": 77, "nome": None})

    def test_historico_item(self) -> None:
        h = SimpleNamespace(
            ophId=30,
            ophUsuId=3,
            ophDataRegistro=datetime(2026, 9, 27, 13, 0, tzinfo=timezone.utc),
            ophConteudo="Reunião ok",
        )
        self.assertEqual(
            historico_item(h, {3: "Carlos"}),
            {"id": 30, "data": "2026-09-27T13:00:00+00:00", "autor": {"id": 3, "nome": "Carlos"}, "conteudo": "Reunião ok"},
        )


if __name__ == "__main__":
    unittest.main()
