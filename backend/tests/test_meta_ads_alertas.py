import unittest
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models.etapa_kanban import EtapaKanban
from backend.models.meta_ads_alerta import MetaAdsAlerta
from backend.models.meta_ads_conta import STATUS_AVISO, STATUS_OK, STATUS_TOKEN_INVALIDO
from backend.models.meta_ads_sync_log import MetaAdsSyncLog
from backend.models.oportunidade_etapa_historico import OportunidadeEtapaHistorico
from backend.routers import meta_ads_router
from backend.services.meta_ads import alertas as a
from backend.services.meta_ads import cliente_graph as g
from backend.services.meta_ads import sincronizacao as s
from backend.services.meta_ads.config_monitor import obter_config
from backend.tests import banco_sqlite as b

HOJE = date(2026, 10, 26)
ONTEM = date(2026, 10, 25)
# 15:00 UTC = 12:00 em Sao Paulo, dia 26.
AGORA = datetime(2026, 10, 26, 15, 0)


class ClienteFalso:
    """Substitui ClienteGraph nas avaliacoes. Registra as chamadas feitas."""

    def __init__(
        self,
        *,
        campanhas=(),
        anuncios=(),
        status=None,
        frequencias=(),
        erro=None,
        erro_em=(),
        permissoes=None,
    ):
        self.campanhas = list(campanhas)
        self.anuncios = list(anuncios)
        self.status = status or g.StatusConta(1, 0)
        self.frequencias = list(frequencias)
        self.erro = erro
        self.erro_em = set(erro_em)
        self.permissoes = permissoes if permissoes is not None else {"ads_read"}
        self.chamadas = []
        self.periodos = []
        self.token = None

    def __call__(self, token):
        self.token = token
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def _registrar(self, nome):
        self.chamadas.append(nome)
        if self.erro is not None and nome in self.erro_em:
            raise self.erro

    def listar_permissoes(self):
        return self.permissoes

    def listar_campanhas(self, _act):
        self._registrar("campanhas")
        return self.campanhas

    def listar_anuncios(self, _act):
        self._registrar("anuncios")
        return self.anuncios

    def obter_status_conta(self, _act):
        self._registrar("status")
        return self.status

    def frequencia_7_dias(self, _act, inicio, fim):
        self._registrar("frequencia")
        self.periodos.append((inicio, fim))
        return self.frequencias


def _anuncio_meta(externo, status="ACTIVE", motivo=None, campanha="c1"):
    return g.AnuncioMeta(externo, "Anúncio", "s1", campanha, status, motivo, None)


class BaseAlertas(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)
        self.e = self.emp.empId
        self.conta = b.criar_conta(self.db, self.e)
        self.conta.macStatus = STATUS_OK
        self.conta.macUltimaSync = datetime(2026, 10, 26, 7, 5)  # 04:05 em SP, hoje
        self.db.commit()
        self.log_ok = self._log_sync(date(2026, 9, 26), HOJE)
        self.camp = b.criar_campanha(self.db, self.conta, "c1", "Campanha 1")
        self.conj = b.criar_conjunto(self.db, self.camp, "s1", "Conjunto 1")
        self.anu = b.criar_anuncio(self.db, self.conj, "a1", "Anúncio 1")
        self.cfg = obter_config(self.db, self.e)

    def _log_sync(self, inicio, fim, status=STATUS_OK, quando=datetime(2026, 10, 26, 7, 5)):
        log = MetaAdsSyncLog(
            mslMacId=self.conta.macId, mslInicio=inicio, mslFim=fim, mslOrigem="agendada",
            mslStatus=status, mslDataExecucao=quando,
        )
        self.db.add(log)
        self.db.commit()
        return log

    def _alertas(self, tipo=None):
        q = select(MetaAdsAlerta).where(MetaAdsAlerta.malEmpId == self.e)
        if tipo:
            q = q.where(MetaAdsAlerta.malTipo == tipo)
        return list(self.db.execute(q.order_by(MetaAdsAlerta.malId)).scalars())

    def _abrir(self, tipo, chave, status="aberto"):
        alerta = MetaAdsAlerta(
            malEmpId=self.e,
            malTipo=tipo,
            malChave=chave,
            malStatus=status,
            malMensagem="antigo",
            malDados={},
            malPrimeiroEm=datetime(2026, 10, 20),
            malUltimoEm=datetime(2026, 10, 20),
        )
        self.db.add(alerta)
        self.db.commit()
        return alerta


class SincronizarDisparosTests(BaseAlertas):
    def _d(self, msg="m", chave="anuncio:1"):
        return a.Disparo("gasto", chave, msg, {"gasto_7d": 160.0})

    def test_alerta_nao_duplica_e_resolve(self) -> None:
        d1, d2, d3, d4 = (datetime(2026, 10, i, 8) for i in (1, 2, 3, 4))
        r = a.sincronizar_disparos(self.db, self.e, {"gasto"}, [self._d("m1")], d1)
        self.assertEqual(r["criados"], 1)
        a.sincronizar_disparos(self.db, self.e, {"gasto"}, [self._d("m2")], d2)
        linhas = self._alertas()
        self.assertEqual(len(linhas), 1)
        self.assertEqual(
            (linhas[0].malStatus, linhas[0].malMensagem, linhas[0].malPrimeiroEm, linhas[0].malUltimoEm),
            ("aberto", "m2", d1, d2),
        )
        r = a.sincronizar_disparos(self.db, self.e, {"gasto"}, [], d3)
        self.assertEqual(r["resolvidos"], 1)
        linha = self._alertas()[0]
        self.assertEqual((linha.malStatus, linha.malResolvidoEm), ("resolvido", d3))
        a.sincronizar_disparos(self.db, self.e, {"gasto"}, [self._d("m4")], d4)
        linhas = self._alertas()
        self.assertEqual(len(linhas), 2)
        self.assertEqual([l.malStatus for l in linhas], ["resolvido", "aberto"])

    def test_ciente_continua_ciente_enquanto_dispara(self) -> None:
        a.sincronizar_disparos(self.db, self.e, {"gasto"}, [self._d("m1")], datetime(2026, 10, 1))
        mal_id = self._alertas()[0].malId
        self.assertEqual(a.marcar_ciente(self.db, self.e, mal_id).malStatus, "ciente")
        a.sincronizar_disparos(self.db, self.e, {"gasto"}, [self._d("m2")], datetime(2026, 10, 2))
        linhas = self._alertas()
        self.assertEqual(len(linhas), 1)
        self.assertEqual((linhas[0].malStatus, linhas[0].malMensagem), ("ciente", "m2"))
        a.sincronizar_disparos(self.db, self.e, {"gasto"}, [], datetime(2026, 10, 3))
        a.sincronizar_disparos(self.db, self.e, {"gasto"}, [self._d("m4")], datetime(2026, 10, 4))
        self.assertEqual([l.malStatus for l in self._alertas()], ["resolvido", "aberto"])

    def test_tipo_nao_avaliado_nao_e_resolvido(self) -> None:
        self._abrir("cpl", "anuncio:1")
        a.sincronizar_disparos(self.db, self.e, {"gasto"}, [], datetime(2026, 10, 3))
        self.assertEqual(self._alertas("cpl")[0].malStatus, "aberto")

    def test_preservar_nao_resolve(self) -> None:
        self._abrir("gasto", "anuncio:1")
        self._abrir("gasto", "anuncio:2")
        a.sincronizar_disparos(
            self.db, self.e, {"gasto"}, [], datetime(2026, 10, 3),
            preservar={("gasto", "anuncio:1")},
        )
        self.assertEqual([l.malStatus for l in self._alertas()], ["aberto", "resolvido"])

    def test_mensagem_longa_truncada(self) -> None:
        a.sincronizar_disparos(self.db, self.e, {"gasto"}, [self._d("x" * 900)], datetime(2026, 10, 1))
        self.assertEqual(len(self._alertas()[0].malMensagem), 500)

    def test_nao_mexe_em_outra_empresa(self) -> None:
        outra = b.criar_empresa(self.db, "Outra")
        self.db.add(MetaAdsAlerta(
            malEmpId=outra.empId, malTipo="gasto", malChave="anuncio:1", malStatus="aberto",
            malMensagem="x", malDados={}, malPrimeiroEm=datetime(2026, 10, 1),
            malUltimoEm=datetime(2026, 10, 1),
        ))
        self.db.commit()
        a.sincronizar_disparos(self.db, self.e, {"gasto"}, [], datetime(2026, 10, 3))
        alerta = self.db.execute(
            select(MetaAdsAlerta).where(MetaAdsAlerta.malEmpId == outra.empId)
        ).scalar_one()
        self.assertEqual(alerta.malStatus, "aberto")


class AvaliarDiariosTests(BaseAlertas):
    def _dias(self, inicio: date, n: int, inv: float, **kw):
        for i in range(n):
            b.criar_insight_anuncio(self.db, self.anu, inicio + timedelta(days=i), inv, **kw)

    def test_avaliar_diarios_gasto_sem_lead(self) -> None:
        self._dias(date(2026, 10, 19), 6, 20)
        self._dias(ONTEM, 1, 40)
        cliente = ClienteFalso()
        a.avaliar_diarios(self.db, self.e, HOJE, fabrica_cliente=cliente)
        alertas = self._alertas()
        self.assertEqual([(x.malTipo, x.malChave) for x in alertas], [("gasto", f"anuncio:{self.anu.manId}")])
        self.assertAlmostEqual(alertas[0].malDados["gasto_7d"], 160.0, places=2)
        self.assertEqual(cliente.periodos, [(date(2026, 10, 19), ONTEM)])

    def test_gasto_fora_da_janela_nao_conta(self) -> None:
        self._dias(date(2026, 10, 18), 1, 100)  # 8 dias atras: fora dos ultimos 7
        self._dias(date(2026, 10, 19), 7, 10)
        a.avaliar_diarios(self.db, self.e, HOJE, fabrica_cliente=ClienteFalso())
        self.assertEqual(self._alertas(), [])

    def test_avaliar_diarios_respeita_desligado(self) -> None:
        self._abrir("gasto", "anuncio:999")
        self.cfg.mmcAlertaGasto = False
        self.cfg.mmcAlertaFrequencia = False
        self.db.commit()
        self._dias(date(2026, 10, 19), 7, 30)
        cliente = ClienteFalso()
        a.avaliar_diarios(self.db, self.e, HOJE, fabrica_cliente=cliente)
        self.assertEqual([x.malStatus for x in self._alertas("gasto")], ["resolvido"])
        self.assertNotIn("frequencia", cliente.chamadas)

    def test_cpl(self) -> None:
        self._dias(date(2026, 10, 18), 7, 40, leads=1)
        self._dias(ONTEM, 1, 100, leads=1)
        a.avaliar_diarios(self.db, self.e, HOJE, fabrica_cliente=ClienteFalso())
        alertas = self._alertas()
        self.assertEqual([x.malTipo for x in alertas], ["cpl"])
        self.assertEqual((alertas[0].malDados["cpl_ontem"], alertas[0].malDados["cpl_base"]), (100.0, 40.0))

    def test_ctr(self) -> None:
        self.anu.manPrimeiroDia = date(2026, 10, 12)  # 14 dias ate ontem
        self.db.commit()
        self._dias(date(2026, 10, 12), 7, 5, impressoes=1000, cliques=30)
        self._dias(date(2026, 10, 19), 7, 5, impressoes=1000, cliques=15)
        a.avaliar_diarios(self.db, self.e, HOJE, fabrica_cliente=ClienteFalso())
        alertas = self._alertas()
        self.assertEqual([x.malTipo for x in alertas], ["ctr"])
        self.assertEqual((alertas[0].malDados["ctr_inicial"], alertas[0].malDados["ctr_atual"]), (3.0, 1.5))

    def test_ctr_com_13_dias_nao_avalia(self) -> None:
        self.anu.manPrimeiroDia = date(2026, 10, 13)
        self.db.commit()
        self._dias(date(2026, 10, 13), 6, 5, impressoes=2000, cliques=60)
        self._dias(date(2026, 10, 19), 7, 5, impressoes=1000, cliques=5)
        a.avaliar_diarios(self.db, self.e, HOJE, fabrica_cliente=ClienteFalso())
        self.assertEqual(self._alertas(), [])

    def test_frequencia(self) -> None:
        cliente = ClienteFalso(frequencias=[
            g.FrequenciaAnuncio("a1", 5000, 1000, 5.0),
            g.FrequenciaAnuncio("desconhecido", 5000, 1000, 9.0),
        ])
        a.avaliar_diarios(self.db, self.e, HOJE, fabrica_cliente=cliente)
        alertas = self._alertas()
        self.assertEqual([(x.malTipo, x.malChave) for x in alertas], [("frequencia", f"anuncio:{self.anu.manId}")])

    def test_erro_na_frequencia_nao_resolve_abertos(self) -> None:
        self._abrir("frequencia", f"anuncio:{self.anu.manId}")
        self._abrir("gasto", f"anuncio:{self.anu.manId}")
        cliente = ClienteFalso(erro=g.ErroTemporario("Meta fora"), erro_em={"frequencia"})
        r = a.avaliar_diarios(self.db, self.e, HOJE, fabrica_cliente=cliente)
        self.assertEqual(r["erros"], 1)
        self.assertEqual(self._alertas("frequencia")[0].malStatus, "aberto")
        # O resto da avaliacao segue normalmente: o gasto (do banco) foi resolvido.
        self.assertEqual(self._alertas("gasto")[0].malStatus, "resolvido")

    def test_token_invalido_nao_chama_meta_e_preserva_frequencia(self) -> None:
        self.conta.macStatus = STATUS_TOKEN_INVALIDO
        self.db.commit()
        self._abrir("frequencia", f"anuncio:{self.anu.manId}")
        cliente = ClienteFalso()
        a.avaliar_diarios(self.db, self.e, HOJE, fabrica_cliente=cliente)
        self.assertEqual(cliente.chamadas, [])
        self.assertEqual(self._alertas("frequencia")[0].malStatus, "aberto")

    def test_sync_com_falha_nao_resolve_alertas_da_conta(self) -> None:
        self.conta.macStatus = STATUS_AVISO
        self.db.commit()
        self._abrir("gasto", f"anuncio:{self.anu.manId}")
        a.avaliar_diarios(self.db, self.e, HOJE, fabrica_cliente=ClienteFalso())
        self.assertEqual(self._alertas("gasto")[0].malStatus, "aberto")

    def test_conta_de_outra_empresa_nao_entra(self) -> None:
        outra = b.criar_empresa(self.db, "Outra")
        conta2 = b.criar_conta(self.db, outra.empId, act="act_222")
        camp2 = b.criar_campanha(self.db, conta2, "c2", "C2")
        anu2 = b.criar_anuncio(self.db, b.criar_conjunto(self.db, camp2, "s2", "S2"), "a2", "A2")
        for i in range(7):
            b.criar_insight_anuncio(self.db, anu2, date(2026, 10, 19) + timedelta(days=i), 100)
        a.avaliar_diarios(self.db, self.e, HOJE, fabrica_cliente=ClienteFalso())
        self.assertEqual(self._alertas(), [])


class AvaliarHorariosTests(BaseAlertas):
    def _cliente_ok(self, **kw):
        base = dict(
            campanhas=[g.CampanhaMeta("c1", "Campanha 1", None, "PAUSED")],
            anuncios=[_anuncio_meta("a1")],
            status=g.StatusConta(1, 0),
        )
        base.update(kw)
        return ClienteFalso(**base)

    def test_parado_usa_status_fresco_da_meta(self) -> None:
        # No banco tudo parece normal; a Meta diz o contrario.
        self.camp.mcgStatus = "PAUSED"
        self.db.commit()
        cliente = self._cliente_ok(
            campanhas=[g.CampanhaMeta("c1", "Campanha 1", None, "ACTIVE")],
            # a2 ainda nao sincronizado: nao entra como anuncio, mas conta como anuncio ativo da campanha.
            anuncios=[_anuncio_meta("a1", "DISAPPROVED", "Texto proibido"), _anuncio_meta("a2")],
            status=g.StatusConta(3, 0),
        )
        a.avaliar_horarios(self.db, self.e, AGORA, fabrica_cliente=cliente)
        chaves = {x.malChave for x in self._alertas("parado")}
        self.assertEqual(
            chaves,
            {f"anuncio:{self.anu.manId}", f"campanha:{self.camp.mcgId}", f"conta:{self.conta.macId}"},
        )
        self.assertEqual({"campanhas", "anuncios", "status"}, set(cliente.chamadas))

    def test_status_velho_do_banco_nao_dispara(self) -> None:
        self.anu.manStatus = "DISAPPROVED"
        self.db.commit()
        a.avaliar_horarios(self.db, self.e, AGORA, fabrica_cliente=self._cliente_ok())
        self.assertEqual(self._alertas("parado"), [])

    def test_campanha_ativa_com_impressao_ontem_nao_dispara(self) -> None:
        b.criar_insight(self.db, self.camp, ONTEM, 10, impressoes=500)
        cliente = self._cliente_ok(campanhas=[g.CampanhaMeta("c1", "Campanha 1", None, "ACTIVE")])
        a.avaliar_horarios(self.db, self.e, AGORA, fabrica_cliente=cliente)
        self.assertEqual(self._alertas("parado"), [])

    def test_sem_sync_hoje_nao_avalia_campanha(self) -> None:
        self.conta.macUltimaSync = datetime(2026, 10, 25, 7, 5)  # ontem
        self.db.commit()
        self._abrir("parado", f"campanha:{self.camp.mcgId}")
        cliente = self._cliente_ok(campanhas=[g.CampanhaMeta("c1", "Campanha 1", None, "ACTIVE")])
        a.avaliar_horarios(self.db, self.e, AGORA, fabrica_cliente=cliente)
        alertas = self._alertas("parado")
        self.assertEqual([(x.malChave, x.malStatus) for x in alertas], [(f"campanha:{self.camp.mcgId}", "aberto")])

    def test_campanha_ativa_com_todos_anuncios_pausados_nao_dispara(self) -> None:
        cliente = self._cliente_ok(
            campanhas=[g.CampanhaMeta("c1", "Campanha 1", None, "ACTIVE")],
            anuncios=[_anuncio_meta("a1", "PAUSED"), _anuncio_meta("a9", "ACTIVE", campanha="outra")],
        )
        a.avaliar_horarios(self.db, self.e, AGORA, fabrica_cliente=cliente)
        self.assertEqual(self._alertas("parado"), [])

    def test_campanha_ativa_com_um_anuncio_ativo_dispara(self) -> None:
        cliente = self._cliente_ok(
            campanhas=[g.CampanhaMeta("c1", "Campanha 1", None, "ACTIVE")],
            anuncios=[_anuncio_meta("a1", "PAUSED"), _anuncio_meta("a2", "ACTIVE")],
        )
        a.avaliar_horarios(self.db, self.e, AGORA, fabrica_cliente=cliente)
        self.assertEqual([x.malChave for x in self._alertas("parado")], [f"campanha:{self.camp.mcgId}"])

    def test_sync_de_hoje_que_nao_cobriu_ontem_nao_avalia_campanha(self) -> None:
        # A ultima sync ok de hoje foi um reprocessamento de setembro: o "ontem" do banco nao e confiavel.
        self._log_sync(date(2026, 9, 1), date(2026, 9, 30), quando=datetime(2026, 10, 26, 9, 0))
        self._log_sync(date(2026, 10, 1), HOJE, status="erro", quando=datetime(2026, 10, 26, 10, 0))
        self._abrir("parado", f"campanha:{self.camp.mcgId}")
        cliente = self._cliente_ok(campanhas=[g.CampanhaMeta("c1", "Campanha 1", None, "ACTIVE")])
        a.avaliar_horarios(self.db, self.e, AGORA, fabrica_cliente=cliente)
        alertas = self._alertas("parado")
        # Preservado como estava: nem resolvido nem reavaliado (mensagem antiga).
        self.assertEqual(
            [(x.malChave, x.malStatus, x.malMensagem) for x in alertas],
            [(f"campanha:{self.camp.mcgId}", "aberto", "antigo")],
        )

    def test_sem_log_de_sync_ok_nao_avalia_campanha(self) -> None:
        self.db.delete(self.log_ok)
        self.db.commit()
        cliente = self._cliente_ok(campanhas=[g.CampanhaMeta("c1", "Campanha 1", None, "ACTIVE")])
        a.avaliar_horarios(self.db, self.e, AGORA, fabrica_cliente=cliente)
        self.assertEqual(self._alertas("parado"), [])

    def test_fabrica_padrao_nao_retenta(self) -> None:
        cliente = self._cliente_ok()
        with patch.object(a, "ClienteGraph", return_value=cliente) as construtor:
            a.avaliar_horarios(self.db, self.e, AGORA)
        construtor.assert_called_once_with("EAAB-token-de-teste-1234", esperas=())
        self.assertEqual({"campanhas", "anuncios", "status"}, set(cliente.chamadas))

    def test_volta_ao_normal_resolve(self) -> None:
        self._abrir("parado", f"conta:{self.conta.macId}")
        a.avaliar_horarios(self.db, self.e, AGORA, fabrica_cliente=self._cliente_ok())
        self.assertEqual(self._alertas("parado")[0].malStatus, "resolvido")

    def test_erro_da_meta_nao_resolve_parado_da_conta(self) -> None:
        self._abrir("parado", f"conta:{self.conta.macId}")
        self._abrir("parado", f"anuncio:{self.anu.manId}")
        cliente = self._cliente_ok(erro=g.MetaGraphErro("falhou"), erro_em={"anuncios"})
        r = a.avaliar_horarios(self.db, self.e, AGORA, fabrica_cliente=cliente)
        self.assertEqual(r["erros"], 1)
        self.assertEqual([x.malStatus for x in self._alertas("parado")], ["aberto", "aberto"])

    def test_permissao_de_escrita_conta_como_erro(self) -> None:
        self._abrir("parado", f"conta:{self.conta.macId}")
        cliente = self._cliente_ok(permissoes={"ads_read", "ads_management"})
        r = a.avaliar_horarios(self.db, self.e, AGORA, fabrica_cliente=cliente)
        self.assertEqual(r["erros"], 1)
        self.assertEqual(cliente.chamadas, [])
        self.assertEqual(self._alertas("parado")[0].malStatus, "aberto")

    def test_lead_sem_contato_ignora_backlog(self) -> None:
        contatos = EtapaKanban(etkEmpId=self.e, etkNome="Contatos", etkOrdem=1)
        qualificado = EtapaKanban(etkEmpId=self.e, etkNome="Qualificado", etkOrdem=2)
        self.db.add_all([contatos, qualificado])
        self.cfg.mmcSemContatoDesde = datetime(2026, 10, 20)
        self.db.commit()
        b.criar_oportunidade(
            self.db, self.e, opoTitulo="Antigo", opoNomeContato="José", opoTelefone="1188887777",
            opoMetaLeadId="L1", opoDataCriacao=datetime(2026, 10, 19, 12),
        )
        novo = b.criar_oportunidade(
            self.db, self.e, opoTitulo="Novo", opoNomeContato="Maria", opoTelefone="11999990000",
            opoMetaLeadId="L2", opoDataCriacao=AGORA - timedelta(hours=25),
        )
        b.criar_oportunidade(  # sem sinal da Meta
            self.db, self.e, opoTitulo="Site", opoNomeContato="Ana",
            opoDataCriacao=AGORA - timedelta(hours=30),
        )
        b.criar_oportunidade(  # recente demais
            self.db, self.e, opoTitulo="Recente", opoMetaLeadId="L3",
            opoDataCriacao=AGORA - timedelta(hours=23),
        )
        b.criar_oportunidade(  # fechado
            self.db, self.e, opoTitulo="Perdido", opoMetaLeadId="L4", opoStatusFechamento="perdido",
            opoDataCriacao=AGORA - timedelta(hours=30),
        )
        a.avaliar_horarios(self.db, self.e, AGORA, fabrica_cliente=self._cliente_ok())
        alertas = self._alertas("sem_contato")
        self.assertEqual([x.malChave for x in alertas], [f"lead:{novo.opoId}"])
        self.assertIn("Maria", alertas[0].malMensagem)
        self.assertIn("11999990000", alertas[0].malMensagem)

        self.db.add(OportunidadeEtapaHistorico(
            oehEmpId=self.e, oehOpoId=novo.opoId, oehEtkIdDe=contatos.etkId,
            oehEtkIdPara=qualificado.etkId, oehData=AGORA + timedelta(minutes=10), oehOrigem="ui",
        ))
        self.db.commit()
        a.avaliar_horarios(self.db, self.e, AGORA + timedelta(hours=1), fabrica_cliente=self._cliente_ok())
        self.assertEqual(self._alertas("sem_contato")[0].malStatus, "resolvido")

    def test_agora_com_fuso_e_normalizado(self) -> None:
        from datetime import timezone

        self.cfg.mmcSemContatoDesde = datetime(2026, 10, 20)
        self.db.commit()
        b.criar_oportunidade(
            self.db, self.e, opoTitulo="Novo", opoMetaLeadId="L2",
            opoDataCriacao=AGORA - timedelta(hours=25),
        )
        a.avaliar_horarios(
            self.db, self.e, AGORA.replace(tzinfo=timezone.utc), fabrica_cliente=self._cliente_ok()
        )
        alerta = self._alertas("sem_contato")[0]
        self.assertEqual(alerta.malUltimoEm, AGORA)

    def test_sem_contato_desligado_resolve_e_nao_cria(self) -> None:
        self._abrir("sem_contato", "lead:1")
        self.cfg.mmcAlertaSemContato = False
        self.cfg.mmcSemContatoDesde = datetime(2026, 10, 20)
        self.db.commit()
        b.criar_oportunidade(
            self.db, self.e, opoTitulo="Novo", opoMetaLeadId="L2",
            opoDataCriacao=AGORA - timedelta(hours=25),
        )
        a.avaliar_horarios(self.db, self.e, AGORA, fabrica_cliente=self._cliente_ok())
        self.assertEqual([x.malStatus for x in self._alertas("sem_contato")], ["resolvido"])

    def test_dados_sem_pessoais_fora_do_sem_contato(self) -> None:
        cliente = self._cliente_ok(
            campanhas=[g.CampanhaMeta("c1", "Campanha 1", None, "ACTIVE")],
            anuncios=[_anuncio_meta("a1", "WITH_ISSUES", None)],
            status=g.StatusConta(2, 5),
        )
        a.avaliar_horarios(self.db, self.e, AGORA, fabrica_cliente=cliente)
        for alerta in self._alertas("parado"):
            self.assertFalse({"contato", "telefone"} & set(alerta.malDados))


class ListarECienteTests(BaseAlertas):
    def test_listar_por_status_com_nome_do_alvo(self) -> None:
        self._abrir("gasto", f"anuncio:{self.anu.manId}")
        self._abrir("parado", f"campanha:{self.camp.mcgId}", status="ciente")
        self._abrir("parado", f"conta:{self.conta.macId}", status="resolvido")
        abertos = a.listar(self.db, self.e, "aberto")
        self.assertEqual([(x.malTipo, x.alvoNome) for x in abertos], [("gasto", "Anúncio 1")])
        todos = a.listar(self.db, self.e, None)
        self.assertEqual({x.alvoNome for x in todos}, {"Anúncio 1", "Campanha 1", "Conta"})

    def test_marcar_ciente_de_outra_empresa_404(self) -> None:
        outra = b.criar_empresa(self.db, "Outra")
        alerta = self._abrir("gasto", "anuncio:1")
        with self.assertRaises(HTTPException) as ctx:
            a.marcar_ciente(self.db, outra.empId, alerta.malId)
        self.assertEqual(ctx.exception.status_code, 404)
        self.db.refresh(alerta)
        self.assertEqual(alerta.malStatus, "aberto")

    def test_rotas(self) -> None:
        alerta = self._abrir("gasto", f"anuncio:{self.anu.manId}")
        app = FastAPI()
        app.include_router(meta_ads_router.router)
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(usuId=1, usuAdmin=False)
        http = TestClient(app)
        h = {"X-Company-Id": str(self.e)}
        # Usuario comum da empresa (nao admin) pode ler e marcar ciente.
        with patch.object(meta_ads_router, "require_user_in_company") as exigir:
            r = http.get("/api/meta-ads/alertas?status=aberto", headers=h)
            self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual([x["malId"] for x in r.json()["items"]], [alerta.malId])
            self.assertEqual(r.json()["items"][0]["alvoNome"], "Anúncio 1")
            r = http.post(f"/api/meta-ads/alertas/{alerta.malId}/ciente", headers=h)
            self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual(r.json()["malStatus"], "ciente")
            r = http.get("/api/meta-ads/alertas?status=aberto", headers=h)
            self.assertEqual(r.json()["items"], [])
            self.assertEqual(len(http.get("/api/meta-ads/alertas", headers=h).json()["items"]), 1)
            self.assertEqual(http.get("/api/meta-ads/alertas?status=xyz", headers=h).status_code, 422)
            self.assertEqual(http.post("/api/meta-ads/alertas/9999/ciente", headers=h).status_code, 404)
        self.assertTrue(exigir.called)


class ClienteDaContaTests(BaseAlertas):
    def test_recusa_token_com_escrita(self) -> None:
        cliente = ClienteFalso(permissoes={"ads_read", "ads_management"})
        with self.assertRaises(g.PermissaoExcessivaErro):
            with s.cliente_da_conta(self.db, self.conta.macId, fabrica_cliente=cliente):
                pass

    def test_entrega_cliente_com_token_decifrado(self) -> None:
        cliente = ClienteFalso()
        with s.cliente_da_conta(self.db, self.conta.macId, fabrica_cliente=cliente) as c:
            self.assertIs(c, cliente)
        self.assertEqual(cliente.token, "EAAB-token-de-teste-1234")


class TodasEmpresasTests(BaseAlertas):
    def test_falha_numa_empresa_nao_impede_as_outras(self) -> None:
        outra = b.criar_empresa(self.db, "Outra")
        b.criar_conta(self.db, outra.empId, act="act_222")
        sem_conta = b.criar_empresa(self.db, "Sem conta")
        self.assertEqual(a.empresas_com_conta_ativa(self.db), sorted([self.e, outra.empId]))
        self.assertNotIn(sem_conta.empId, a.empresas_com_conta_ativa(self.db))

        chamadas = []
        original = a.avaliar_horarios

        def avaliar(db, emp_id, agora, fabrica_cliente=None):
            chamadas.append(emp_id)
            if emp_id == self.e:
                raise RuntimeError("quebrou")
            return original(db, emp_id, agora, fabrica_cliente=ClienteFalso())

        engine = self.db.get_bind()
        a.avaliar_horarios = avaliar
        try:
            with patch(
                "backend.services.meta_ads.resumo.gerar_se_devido", return_value=False
            ) as devido:
                ok = a.avaliar_horarios_todas(AGORA, fabrica_sessao=lambda: Session(bind=engine))
        finally:
            a.avaliar_horarios = original
        self.assertEqual(chamadas, sorted([self.e, outra.empId]))
        self.assertEqual(ok, 1)
        # O resumo diario roda mesmo para a empresa cuja avaliacao de alertas falhou.
        self.assertEqual([c.args[1] for c in devido.call_args_list], sorted([self.e, outra.empId]))
        self.assertEqual(devido.call_args_list[0].args[2], AGORA)

    def test_falha_no_resumo_nao_bloqueia_alertas(self) -> None:
        outra = b.criar_empresa(self.db, "Outra")
        b.criar_conta(self.db, outra.empId, act="act_222")
        avaliadas = []
        original = a.avaliar_horarios

        def avaliar(db, emp_id, agora, fabrica_cliente=None):
            avaliadas.append(emp_id)
            return {"criados": 0, "atualizados": 0, "resolvidos": 0, "erros": 0}

        engine = self.db.get_bind()
        a.avaliar_horarios = avaliar
        try:
            with patch(
                "backend.services.meta_ads.resumo.gerar_se_devido", side_effect=RuntimeError("ia caiu")
            ) as devido, self.assertLogs("backend.services.meta_ads.alertas", level="ERROR") as logs:
                ok = a.avaliar_horarios_todas(AGORA, fabrica_sessao=lambda: Session(bind=engine))
        finally:
            a.avaliar_horarios = original
        self.assertEqual(avaliadas, sorted([self.e, outra.empId]))
        self.assertEqual(devido.call_count, 2)
        self.assertEqual(ok, 2)  # alertas rodaram nas duas
        self.assertTrue(all("falha no resumo diário" in m for m in logs.output))


if __name__ == "__main__":
    unittest.main()
