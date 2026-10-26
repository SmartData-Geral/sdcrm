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

    def test_paging_next_com_token_e_removido_da_url(self) -> None:
        pagina1 = {
            "data": [{"id": "1", "name": "A"}],
            "paging": {
                "next": "https://graph.facebook.com/v99.0/act_1/campaigns?after=x&access_token=" + TOKEN
            },
        }
        pagina2 = {"data": [{"id": "2", "name": "B"}], "paging": {}}
        cliente, feitas, _ = _cliente([(200, pagina1), (200, pagina2)])
        with cliente:
            campanhas = cliente.listar_campanhas("act_1")
        self.assertEqual([c.id for c in campanhas], ["1", "2"])
        self.assertNotIn(TOKEN, str(feitas[1].url))
        self.assertNotIn("access_token", str(feitas[1].url))

    def test_paging_next_de_outro_host_nao_e_seguido(self) -> None:
        pagina1 = {
            "data": [{"id": "1", "name": "A"}],
            "paging": {"next": "https://evil.example.com/x"},
        }
        cliente, feitas, _ = _cliente([(200, pagina1)])
        with cliente, self.assertRaises(g.MetaGraphErro) as ctx:
            cliente.listar_campanhas("act_1")
        self.assertEqual(len(feitas), 1)
        self.assertNotIn("evil.example.com", ctx.exception.mensagem)

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


class PermissoesTests(unittest.TestCase):
    def test_so_leitura_passa(self):
        self.assertEqual(g.permissoes_de_escrita({"ads_read", "read_insights"}), set())

    def test_escrita_detectada(self):
        self.assertEqual(
            g.permissoes_de_escrita({"ads_read", "ads_management", "pages_manage_ads", "publish_video", "business_management"}),
            {"ads_management", "pages_manage_ads", "publish_video", "business_management"},
        )

    def test_listar_permissoes_so_granted(self):
        corpo = {"data": [{"permission": "ads_read", "status": "granted"}, {"permission": "ads_management", "status": "declined"}]}
        cliente, feitas, _ = _cliente([(200, corpo)])
        with cliente:
            self.assertEqual(cliente.listar_permissoes(), {"ads_read"})
        self.assertIn("/me/permissions", str(feitas[0].url))


class AnuncioTests(unittest.TestCase):
    def test_listar_anuncios_extrai_motivo(self):
        corpo = {"data": [
            {"id": "1", "name": "A", "adset_id": "s", "campaign_id": "c", "effective_status": "DISAPPROVED",
             "created_time": "2026-09-10T12:00:00-0300", "issues_info": [{"error_summary": "Anúncio reprovado"}]},
            {"id": "2", "name": "B", "adset_id": "s", "campaign_id": "c", "effective_status": "DISAPPROVED",
             "ad_review_feedback": {"global": {"POLICY": "Texto"}}},
        ]}
        cliente, feitas, _ = _cliente([(200, corpo)])
        with cliente:
            anuncios = cliente.listar_anuncios("act_1")
        self.assertEqual(anuncios[0].motivo, "Anúncio reprovado")
        self.assertEqual(anuncios[0].criado_em, date(2026, 9, 10))
        self.assertEqual(anuncios[1].motivo, "Texto")
        self.assertIsNone(anuncios[1].criado_em)
        self.assertEqual(anuncios[0].conjunto_id, "s")
        self.assertIn("/act_1/ads", str(feitas[0].url))
        self.assertEqual(feitas[0].url.params["limit"], "500")

    def test_insights_anuncio_converte(self):
        corpo = {"data": [{
            "ad_id": "1", "ad_name": "A", "adset_id": "s", "campaign_id": "c", "date_start": "2026-10-01",
            "spend": "12.30", "impressions": "1000", "reach": "800", "clicks": "40",
            "inline_link_clicks": "25", "actions": [{"action_type": "lead", "value": "2"}],
        }]}
        cliente, feitas, _ = _cliente([(200, corpo)])
        with cliente:
            linhas = cliente.listar_insights_anuncios("act_1", date(2026, 10, 1), date(2026, 10, 2))
        self.assertEqual(
            linhas,
            [g.InsightAnuncioDia("1", "A", "s", "c", date(2026, 10, 1), Decimal("12.30"), 1000, 800, 40, 25, 2)],
        )
        self.assertEqual(feitas[0].url.params["level"], "ad")
        self.assertEqual(feitas[0].url.params["time_increment"], "1")

    def test_frequencia_sem_time_increment(self):
        corpo = {"data": [{"ad_id": "1", "impressions": "1000", "reach": "300", "frequency": "3.4"}]}
        cliente, feitas, _ = _cliente([(200, corpo)])
        with cliente:
            r = cliente.frequencia_7_dias("act_1", date(2026, 10, 1), date(2026, 10, 7))
        self.assertNotIn("time_increment", feitas[0].url.params)
        self.assertEqual(r, [g.FrequenciaAnuncio("1", 1000, 300, 3.4)])

    def test_status_conta(self):
        cliente, _, _ = _cliente([(200, {"account_status": 3, "disable_reason": 0})])
        with cliente:
            self.assertEqual(cliente.obter_status_conta("act_1"), g.StatusConta(3, 0))

    def test_conjuntos_paginam(self):
        p1 = {"data": [{"id": "1", "name": "A", "campaign_id": "c", "effective_status": "ACTIVE"}],
              "paging": {"next": "https://graph.facebook.com/v99.0/act_1/adsets?after=x"}}
        p2 = {"data": [{"id": "2", "name": "B", "campaign_id": "c"}]}
        cliente, _, _ = _cliente([(200, p1), (200, p2)])
        with cliente:
            conjuntos = cliente.listar_conjuntos("act_1")
        self.assertEqual([c.id for c in conjuntos], ["1", "2"])
        self.assertIsNone(conjuntos[1].status)


if __name__ == "__main__":
    unittest.main()
