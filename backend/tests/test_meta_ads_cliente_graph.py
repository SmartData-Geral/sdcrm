import json
import unittest
from datetime import date
from decimal import Decimal

import httpx

from backend.services.meta_ads import cliente_graph as g

TOKEN = "EAAB-token-super-secreto-9999"


def _cliente(respostas, dormidas=None):
    """`respostas`: lista de (status, corpo_dict) devolvidas em ordem; grava as requisicoes."""
    feitas = []
    fila = list(respostas)

    def handler(request: httpx.Request) -> httpx.Response:
        feitas.append(request)
        status, corpo = fila.pop(0)
        return httpx.Response(status, json=corpo)

    dormidas = dormidas if dormidas is not None else []
    cliente = g.ClienteGraph(
        TOKEN, versao="v99.0", transporte=httpx.MockTransport(handler), dormir=dormidas.append
    )
    return cliente, feitas, dormidas


def _erro(codigo, mensagem="falhou"):
    return {"error": {"message": mensagem, "type": "OAuthException", "code": codigo}}


class NormalizacaoTests(unittest.TestCase):
    def test_variacoes_de_conta(self) -> None:
        for entrada in ("act_123", "123", " act_123 ", "act-123"):
            self.assertEqual(g.normalizar_conta(entrada), "act_123", entrada)

    def test_conta_vazia_recusada(self) -> None:
        for entrada in ("", "act_", None):
            with self.assertRaises(ValueError):
                g.normalizar_conta(entrada)


class ExtrairLeadsTests(unittest.TestCase):
    def test_sem_acoes(self) -> None:
        self.assertEqual(g.extrair_leads(None), 0)
        self.assertEqual(g.extrair_leads([]), 0)

    def test_prioridade_conta_so_o_primeiro_tipo(self) -> None:
        acoes = [
            {"action_type": "offsite_conversion.fb_pixel_lead", "value": "9"},
            {"action_type": "lead", "value": "4"},
            {"action_type": "onsite_conversion.lead_grouped", "value": "4"},
        ]
        self.assertEqual(g.extrair_leads(acoes), 4)

    def test_cai_para_o_proximo_tipo(self) -> None:
        acoes = [{"action_type": "offsite_conversion.fb_pixel_lead", "value": "3"}]
        self.assertEqual(g.extrair_leads(acoes), 3)

    def test_ignora_outras_acoes(self) -> None:
        self.assertEqual(g.extrair_leads([{"action_type": "link_click", "value": "50"}]), 0)


class ClienteTests(unittest.TestCase):
    def test_token_vai_no_cabecalho_e_nunca_na_url(self) -> None:
        cliente, feitas, _ = _cliente(
            [(200, {"name": "Conta X", "currency": "BRL", "timezone_name": "America/Sao_Paulo"})]
        )
        with cliente:
            info = cliente.obter_conta("act_1")
        self.assertEqual(info, g.ContaMeta(nome="Conta X", moeda="BRL", fuso="America/Sao_Paulo"))
        self.assertEqual(feitas[0].headers["Authorization"], f"Bearer {TOKEN}")
        self.assertNotIn(TOKEN, str(feitas[0].url))
        self.assertIn("/v99.0/act_1", str(feitas[0].url))

    def test_campanhas_seguem_paginacao(self) -> None:
        pagina1 = {
            "data": [{"id": "1", "name": "A", "objective": "OUTCOME_LEADS", "effective_status": "ACTIVE"}],
            "paging": {"next": "https://graph.facebook.com/v99.0/act_1/campaigns?after=x"},
        }
        pagina2 = {"data": [{"id": "2", "name": "B"}], "paging": {}}
        cliente, feitas, _ = _cliente([(200, pagina1), (200, pagina2)])
        with cliente:
            campanhas = cliente.listar_campanhas("act_1")
        self.assertEqual([c.id for c in campanhas], ["1", "2"])
        self.assertEqual(campanhas[1].objetivo, None)
        self.assertEqual(len(feitas), 2)
        self.assertNotIn(TOKEN, str(feitas[1].url))

    def test_insights_convertem_tipos(self) -> None:
        corpo = {
            "data": [
                {
                    "campaign_id": "10",
                    "campaign_name": "Leads Outubro",
                    "date_start": "2026-10-01",
                    "date_stop": "2026-10-01",
                    "spend": "123.45",
                    "impressions": "1000",
                    "clicks": "37",
                    "reach": "800",
                    "actions": [{"action_type": "lead", "value": "5"}],
                }
            ]
        }
        cliente, feitas, _ = _cliente([(200, corpo)])
        with cliente:
            linhas = cliente.listar_insights("act_1", date(2026, 10, 1), date(2026, 10, 2))
        self.assertEqual(
            linhas,
            [
                g.InsightDia(
                    campanha_id="10",
                    campanha_nome="Leads Outubro",
                    dia=date(2026, 10, 1),
                    investimento=Decimal("123.45"),
                    impressoes=1000,
                    cliques=37,
                    alcance=800,
                    leads=5,
                )
            ],
        )
        params = feitas[0].url.params
        self.assertEqual(params["level"], "campaign")
        self.assertEqual(params["time_increment"], "1")
        self.assertEqual(
            json.loads(params["time_range"]), {"since": "2026-10-01", "until": "2026-10-02"}
        )

    def test_token_invalido_nao_retenta(self) -> None:
        cliente, feitas, dormidas = _cliente([(400, _erro(190, "Error validating access token"))])
        with cliente, self.assertRaises(g.TokenInvalidoErro) as ctx:
            cliente.obter_conta("act_1")
        self.assertEqual(len(feitas), 1)
        self.assertEqual(dormidas, [])
        self.assertEqual(ctx.exception.codigo, 190)

    def test_limite_retenta_com_espera_crescente(self) -> None:
        cliente, feitas, dormidas = _cliente(
            [(400, _erro(17)), (400, _erro(17)), (200, {"name": "ok"})]
        )
        with cliente:
            cliente.obter_conta("act_1")
        self.assertEqual(dormidas, [30, 60])
        self.assertEqual(len(feitas), 3)

    def test_limite_esgotado_vira_erro_temporario(self) -> None:
        cliente, feitas, dormidas = _cliente([(400, _erro(4))] * 4)
        with cliente, self.assertRaises(g.ErroTemporario):
            cliente.obter_conta("act_1")
        self.assertEqual(dormidas, [30, 60, 120])
        self.assertEqual(len(feitas), 4)

    def test_5xx_e_temporario(self) -> None:
        cliente, _, dormidas = _cliente([(503, {}), (200, {"name": "ok"})])
        with cliente:
            cliente.obter_conta("act_1")
        self.assertEqual(dormidas, [30])

    def test_erro_comum_nao_retenta(self) -> None:
        cliente, feitas, _ = _cliente([(400, _erro(100, "Invalid parameter"))])
        with cliente, self.assertRaises(g.MetaGraphErro) as ctx:
            cliente.obter_conta("act_1")
        self.assertNotIsInstance(ctx.exception, (g.TokenInvalidoErro, g.ErroTemporario))
        self.assertIn("Invalid parameter", ctx.exception.mensagem)
        self.assertEqual(len(feitas), 1)

    def test_mensagem_nunca_contem_o_token(self) -> None:
        cliente, _, _ = _cliente([(400, _erro(100, f"token {TOKEN} ruim"))])
        with cliente, self.assertRaises(g.MetaGraphErro) as ctx:
            cliente.obter_conta("act_1")
        self.assertNotIn(TOKEN, ctx.exception.mensagem)
        self.assertNotIn(TOKEN, str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
