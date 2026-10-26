import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from backend.core.tempo import utcnow
from backend.models.meta_ads_anuncio import MetaAdsAnuncio
from backend.models.meta_ads_campanha import MetaAdsCampanha
from backend.models.meta_ads_conjunto import MetaAdsConjunto
from backend.models.meta_ads_insight_anuncio_diario import MetaAdsInsightAnuncioDiario
from backend.models.meta_ads_conta import (
    STATUS_AVISO,
    STATUS_ERRO,
    STATUS_OK,
    STATUS_PERMISSAO_EXCESSIVA,
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

    def __init__(
        self,
        campanhas=(),
        insights=(),
        erro=None,
        permissoes=None,
        conjuntos=(),
        anuncios=(),
        insights_anuncio=(),
        status_conta=None,
        erro_anuncio=None,
    ):
        self.conjuntos = list(conjuntos)
        self.anuncios = list(anuncios)
        self.insights_anuncio = list(insights_anuncio)
        self.status_conta = status_conta or g.StatusConta(1, 0)
        self.erro_anuncio = erro_anuncio
        self.permissoes = permissoes if permissoes is not None else {"ads_read"}
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

    def listar_permissoes(self):
        return self.permissoes

    def listar_campanhas(self, _act):
        return self.campanhas

    def listar_insights(self, _act, inicio, fim):
        self.periodos.append((inicio, fim))
        if self.erro:
            raise self.erro
        return self.insights

    def listar_conjuntos(self, _act):
        return self.conjuntos

    def listar_anuncios(self, _act):
        return self.anuncios

    def listar_insights_anuncios(self, _act, _inicio, _fim):
        if self.erro_anuncio:
            raise self.erro_anuncio
        return self.insights_anuncio

    def obter_status_conta(self, _act):
        return self.status_conta


def _ins_anu(aid, nome, dia, inv, impressoes=1000, sid="s1", cid="1"):
    return g.InsightAnuncioDia(aid, nome, sid, cid, dia, Decimal(str(inv)), impressoes, 800, 50, 30, 1)


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

    def test_permissao_de_escrita_bloqueia_sync(self):
        cliente = ClienteFalso([g.CampanhaMeta("1", "A", None, "ACTIVE")], permissoes={"ads_management"})
        r = self._sync(cliente, inicio=date(2026, 10, 1), fim=date(2026, 10, 1))
        self.assertEqual(r.status, STATUS_PERMISSAO_EXCESSIVA)
        self.assertEqual(cliente.periodos, [])          # nada foi buscado
        self.assertEqual(s.contas_da_rodada_diaria(self.db), [])

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

    def _anuncios_db(self):
        return self.db.execute(select(MetaAdsAnuncio).order_by(MetaAdsAnuncio.manAnuncioExterno)).scalars().all()

    def _insights_anuncio(self):
        return self.db.execute(
            select(MetaAdsInsightAnuncioDiario).order_by(MetaAdsInsightAnuncioDiario.miaData)
        ).scalars().all()

    def test_grava_conjuntos_anuncios_e_insights_por_anuncio(self) -> None:
        d = date(2026, 10, 1)
        cliente = ClienteFalso(
            campanhas=[g.CampanhaMeta("1", "Camp", None, "ACTIVE")],
            insights=[_insight("1", "Camp", d, 10)],
            conjuntos=[g.ConjuntoMeta("s1", "Conj", "1", "ACTIVE")],
            anuncios=[
                g.AnuncioMeta("a1", "Anu 1", "s1", "1", "ACTIVE", None, date(2026, 9, 1)),
                g.AnuncioMeta("a2", "Anu 2", "s1", "1", "PAUSED", "motivo", None),
            ],
            insights_anuncio=[
                _ins_anu("a1", "Anu 1", d, 4),
                _ins_anu("a1", "Anu 1", date(2026, 10, 2), 3),
                _ins_anu("a2", "Anu 2", d, 3),
            ],
        )
        self._sync(cliente, inicio=d, fim=date(2026, 10, 2))
        camp = self.db.execute(select(MetaAdsCampanha)).scalar_one()
        conj = self.db.execute(select(MetaAdsConjunto)).scalar_one()
        self.assertEqual((conj.mcjNome, conj.mcjMcgId), ("Conj", camp.mcgId))
        anuncios = self._anuncios_db()
        self.assertEqual([a.manAnuncioExterno for a in anuncios], ["a1", "a2"])
        self.assertTrue(all(a.manMcjId == conj.mcjId and a.manMcgId == camp.mcgId for a in anuncios))
        self.assertEqual((anuncios[0].manCriadoEmMeta, anuncios[1].manMotivo, anuncios[1].manStatus), (date(2026, 9, 1), "motivo", "PAUSED"))
        self.assertEqual(len(self._insights_anuncio()), 3)

    def test_anuncio_so_no_insight_e_criado(self) -> None:
        d = date(2026, 10, 1)
        self._sync(
            ClienteFalso(insights_anuncio=[_ins_anu("a9", "Anu 9", d, 2, sid="s9", cid="77")]),
            inicio=d,
            fim=d,
        )
        camp = self.db.execute(select(MetaAdsCampanha)).scalar_one()
        conj = self.db.execute(select(MetaAdsConjunto)).scalar_one()
        anu = self._anuncios_db()[0]
        self.assertEqual(camp.mcgCampanhaExterna, "77")
        self.assertEqual(conj.mcjConjuntoExterno, "s9")
        self.assertEqual((anu.manNome, anu.manMcjId, anu.manMcgId), ("Anu 9", conj.mcjId, camp.mcgId))
        self.assertEqual(len(self._insights_anuncio()), 1)

    def test_regrava_insights_anuncio_sem_sobras(self) -> None:
        base = dict(
            campanhas=[g.CampanhaMeta("1", "A", None, "ACTIVE")],
            conjuntos=[g.ConjuntoMeta("s1", "Conj", "1", "ACTIVE")],
            anuncios=[g.AnuncioMeta("a1", "Anu", "s1", "1", "ACTIVE", None, None)],
        )
        self._sync(
            ClienteFalso(**base, insights_anuncio=[_ins_anu("a1", "Anu", date(2026, 9, 30), 5), _ins_anu("a1", "Anu", date(2026, 10, 1), 7)]),
            inicio=date(2026, 9, 30),
            fim=date(2026, 10, 1),
        )
        self._sync(ClienteFalso(**base), inicio=date(2026, 10, 1), fim=date(2026, 10, 1))
        self.assertEqual([l.miaData for l in self._insights_anuncio()], [date(2026, 9, 30)])

    def test_primeiro_dia_e_menor_dia_com_impressao(self) -> None:
        base = dict(
            campanhas=[g.CampanhaMeta("1", "A", None, "ACTIVE")],
            conjuntos=[g.ConjuntoMeta("s1", "Conj", "1", "ACTIVE")],
            anuncios=[g.AnuncioMeta("a1", "Anu", "s1", "1", "ACTIVE", None, None)],
        )
        self._sync(
            ClienteFalso(**base, insights_anuncio=[_ins_anu("a1", "Anu", date(2026, 10, 5), 0, impressoes=0), _ins_anu("a1", "Anu", date(2026, 10, 6), 4, impressoes=100)]),
            inicio=date(2026, 10, 5),
            fim=date(2026, 10, 6),
        )
        self.assertEqual(self._anuncios_db()[0].manPrimeiroDia, date(2026, 10, 6))
        self._sync(
            ClienteFalso(**base, insights_anuncio=[_ins_anu("a1", "Anu", date(2026, 10, 3), 2, impressoes=50)]),
            inicio=date(2026, 10, 3),
            fim=date(2026, 10, 3),
        )
        self.db.expire_all()
        self.assertEqual(self._anuncios_db()[0].manPrimeiroDia, date(2026, 10, 3))

    def test_grava_status_da_conta(self) -> None:
        self._sync(ClienteFalso(status_conta=g.StatusConta(3, 0)), inicio=date(2026, 10, 1), fim=date(2026, 10, 1))
        self.db.refresh(self.conta)
        self.assertEqual((self.conta.macAccountStatus, self.conta.macDisableReason), (3, 0))

    def test_erro_no_nivel_anuncio_nao_grava_nada(self) -> None:
        d = date(2026, 10, 1)
        r = self._sync(
            ClienteFalso(
                campanhas=[g.CampanhaMeta("1", "A", None, "ACTIVE")],
                insights=[_insight("1", "A", d, 5)],
                erro_anuncio=g.MetaGraphErro("Erro do Meta: anuncio", 100),
            ),
            inicio=d,
            fim=d,
        )
        self.assertEqual(r.status, STATUS_ERRO)
        self.assertEqual(self._insights(), [])
        self.assertEqual(self.db.execute(select(MetaAdsCampanha)).scalars().all(), [])


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
