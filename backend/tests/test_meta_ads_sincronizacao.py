import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from backend.core.tempo import utcnow
from backend.models.meta_ads_campanha import MetaAdsCampanha
from backend.models.meta_ads_conta import (
    STATUS_AVISO,
    STATUS_ERRO,
    STATUS_OK,
    STATUS_SINCRONIZANDO,
    STATUS_TOKEN_INVALIDO,
)
from backend.models.meta_ads_insight_diario import MetaAdsInsightDiario
from backend.models.meta_ads_sync_log import MetaAdsSyncLog
from backend.services.meta_ads import cliente_graph as g
from backend.services.meta_ads import sincronizacao as s
from backend.tests import banco_sqlite as b


def _insight(cid, nome, dia, inv, leads=0):
    return g.InsightDia(cid, nome, dia, Decimal(str(inv)), 1000, 40, 800, leads)


class ClienteFalso:
    """Substitui ClienteGraph. Guarda o token e os periodos pedidos."""

    def __init__(self, campanhas=(), insights=(), erro=None):
        self.campanhas = list(campanhas)
        self.insights = list(insights)
        self.erro = erro
        self.token = None
        self.periodos = []

    def __call__(self, token):
        self.token = token
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def listar_campanhas(self, _act):
        return self.campanhas

    def listar_insights(self, _act, inicio, fim):
        self.periodos.append((inicio, fim))
        if self.erro:
            raise self.erro
        return self.insights


class SincronizacaoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)
        self.conta = b.criar_conta(self.db, self.emp.empId, token="EAAB-token-correto-1234")

    def _sync(self, cliente, **kw):
        self.assertTrue(s.reivindicar(self.db, self.conta.macId))
        return s.sincronizar_conta(
            self.db, self.conta.macId, origem=kw.pop("origem", "manual"), fabrica_cliente=cliente, **kw
        )

    def _insights(self):
        return self.db.execute(
            select(MetaAdsInsightDiario).order_by(MetaAdsInsightDiario.midData)
        ).scalars().all()

    def test_grava_campanhas_e_insights(self) -> None:
        cliente = ClienteFalso(
            campanhas=[g.CampanhaMeta("1", "Leads Out", "OUTCOME_LEADS", "ACTIVE")],
            insights=[_insight("1", "Leads Out", date(2026, 10, 1), "10.50", leads=2)],
        )
        r = self._sync(cliente, inicio=date(2026, 10, 1), fim=date(2026, 10, 2))
        self.assertEqual((r.status, r.linhas), (STATUS_OK, 1))
        self.assertEqual(cliente.token, "EAAB-token-correto-1234")
        camp = self.db.execute(select(MetaAdsCampanha)).scalar_one()
        self.assertEqual((camp.mcgNome, camp.mcgNomeNormalizado, camp.mcgStatus), ("Leads Out", "leads out", "ACTIVE"))
        linha = self._insights()[0]
        self.assertEqual((float(linha.midInvestimento), linha.midLeadsMeta, linha.midMcgId), (10.5, 2, camp.mcgId))
        self.db.refresh(self.conta)
        self.assertEqual(self.conta.macStatus, STATUS_OK)
        self.assertIsNone(self.conta.macSyncIniciadaEm)
        self.assertIsNotNone(self.conta.macUltimaSync)

    def test_regrava_periodo_sem_sobras_e_preserva_fora_dele(self) -> None:
        camp = [g.CampanhaMeta("1", "A", None, "ACTIVE")]
        self._sync(
            ClienteFalso(camp, [_insight("1", "A", date(2026, 9, 30), 5), _insight("1", "A", date(2026, 10, 1), 7)]),
            inicio=date(2026, 9, 30),
            fim=date(2026, 10, 1),
        )
        self._sync(ClienteFalso(camp, []), inicio=date(2026, 10, 1), fim=date(2026, 10, 1))
        self.assertEqual([l.midData for l in self._insights()], [date(2026, 9, 30)])

    def test_campanha_so_nos_insights_e_criada(self) -> None:
        self._sync(
            ClienteFalso([], [_insight("77", "Excluída", date(2026, 10, 1), 3)]),
            inicio=date(2026, 10, 1),
            fim=date(2026, 10, 1),
        )
        camp = self.db.execute(select(MetaAdsCampanha)).scalar_one()
        self.assertEqual((camp.mcgCampanhaExterna, camp.mcgNome), ("77", "Excluída"))

    def test_renomear_campanha_mantem_vinculo(self) -> None:
        self._sync(ClienteFalso([g.CampanhaMeta("1", "Nome antigo", None, "ACTIVE")]), inicio=date(2026, 10, 1), fim=date(2026, 10, 1))
        camp = self.db.execute(select(MetaAdsCampanha)).scalar_one()
        opo = b.criar_oportunidade(self.db, self.emp.empId, opoMcgId=camp.mcgId)
        self._sync(ClienteFalso([g.CampanhaMeta("1", "Nome novo", None, "PAUSED")]), inicio=date(2026, 10, 1), fim=date(2026, 10, 1))
        self.db.refresh(camp)
        self.db.refresh(opo)
        self.assertEqual((camp.mcgNome, camp.mcgStatus), ("Nome novo", "PAUSED"))
        self.assertEqual(opo.opoMcgId, camp.mcgId)

    def test_erro_no_meio_nao_grava_nada_e_registra(self) -> None:
        camp = [g.CampanhaMeta("1", "A", None, "ACTIVE")]
        self._sync(ClienteFalso(camp, [_insight("1", "A", date(2026, 10, 1), 5)]), inicio=date(2026, 10, 1), fim=date(2026, 10, 1))
        r = self._sync(
            ClienteFalso([g.CampanhaMeta("1", "Renomeada", None, "ACTIVE")], erro=g.MetaGraphErro("Erro do Meta: x", 100)),
            inicio=date(2026, 10, 1),
            fim=date(2026, 10, 1),
        )
        self.assertEqual(r.status, STATUS_ERRO)
        self.assertEqual(len(self._insights()), 1)
        self.assertEqual(self.db.execute(select(MetaAdsCampanha)).scalar_one().mcgNome, "A")
        self.db.refresh(self.conta)
        self.assertEqual((self.conta.macStatus, self.conta.macMensagem), (STATUS_ERRO, "Erro do Meta: x"))
        log = self.db.execute(select(MetaAdsSyncLog).order_by(MetaAdsSyncLog.mslId.desc())).scalars().first()
        self.assertEqual((log.mslStatus, log.mslErro, log.mslOrigem), (STATUS_ERRO, "Erro do Meta: x", "manual"))

    def test_token_invalido_marca_status_proprio(self) -> None:
        r = self._sync(ClienteFalso(erro=g.TokenInvalidoErro("Token inválido", 190)), inicio=date(2026, 10, 1), fim=date(2026, 10, 1))
        self.assertEqual(r.status, STATUS_TOKEN_INVALIDO)
        self.assertEqual(s.contas_da_rodada_diaria(self.db), [])

    def test_erro_temporario_vira_aviso(self) -> None:
        r = self._sync(ClienteFalso(erro=g.ErroTemporario("limite", 17)), inicio=date(2026, 10, 1), fim=date(2026, 10, 1))
        self.assertEqual(r.status, STATUS_AVISO)
        self.assertEqual(s.contas_da_rodada_diaria(self.db), [self.conta.macId])

    def test_token_ilegivel_vira_token_invalido(self) -> None:
        self.conta.macToken = "enc:v1:lixo"
        self.db.commit()
        r = self._sync(ClienteFalso(), inicio=date(2026, 10, 1), fim=date(2026, 10, 1))
        self.assertEqual(r.status, STATUS_TOKEN_INVALIDO)

    def test_carga_inicial_de_90_dias_e_depois_30(self) -> None:
        cliente = ClienteFalso()
        self._sync(cliente, origem="agendada")
        inicio, fim = cliente.periodos[0]
        self.assertEqual((fim - inicio).days, 90)
        log = self.db.execute(select(MetaAdsSyncLog)).scalar_one()
        self.assertEqual(log.mslOrigem, "carga_inicial")
        self._sync(cliente, origem="agendada")
        inicio, fim = cliente.periodos[1]
        self.assertEqual((fim - inicio).days, 30)

    def test_periodo_explicito_nao_marca_carga_inicial(self) -> None:
        self._sync(ClienteFalso(), origem="periodo", inicio=date(2026, 10, 1), fim=date(2026, 10, 2))
        self.db.refresh(self.conta)
        self.assertFalse(self.conta.macCargaInicialFeita)

    def test_vincula_leads_depois_de_sincronizar(self) -> None:
        b.criar_oportunidade(self.db, self.emp.empId, opoUtmSource="leads out")
        r = self._sync(ClienteFalso([g.CampanhaMeta("1", "Leads Out", None, "ACTIVE")]), inicio=date(2026, 10, 1), fim=date(2026, 10, 1))
        self.assertEqual(r.leads_vinculados, 1)


class TravaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)
        self.conta = b.criar_conta(self.db, self.emp.empId)

    def test_segunda_reivindicacao_falha(self) -> None:
        self.assertTrue(s.reivindicar(self.db, self.conta.macId))
        self.assertFalse(s.reivindicar(self.db, self.conta.macId))

    def test_trava_velha_e_liberada(self) -> None:
        self.conta.macStatus = STATUS_SINCRONIZANDO
        self.conta.macSyncIniciadaEm = utcnow() - timedelta(minutes=31)
        self.db.commit()
        self.assertTrue(s.reivindicar(self.db, self.conta.macId))

    def test_conta_inativa_nao_e_reivindicada(self) -> None:
        self.conta.macAtivo = False
        self.db.commit()
        self.assertFalse(s.reivindicar(self.db, self.conta.macId))


class DatasTests(unittest.TestCase):
    def test_hoje_no_fuso_da_conta(self) -> None:
        class Conta:
            macFuso = "America/Los_Angeles"

        # 02:00 UTC de 15/10 ainda e 14/10 em Los Angeles.
        self.assertEqual(s.hoje_da_conta(Conta(), datetime(2026, 10, 15, 2, 0)), date(2026, 10, 14))

    def test_fuso_invalido_cai_no_padrao(self) -> None:
        class Conta:
            macFuso = "Fuso/Inexistente"

        self.assertEqual(s.hoje_da_conta(Conta(), datetime(2026, 10, 15, 12, 0)), date(2026, 10, 15))


if __name__ == "__main__":
    unittest.main()
