import json
import unittest
from datetime import date, datetime
from unittest.mock import patch

from backend.mcp_crm.ferramentas import campanhas
from backend.schemas.meta_ads import (
    MetaAdsAlertaResponse,
    MetaAdsCockpitCriativo,
    MetaAdsCockpitEtapa,
    MetaAdsCockpitMetas,
    MetaAdsCockpitOperacao,
    MetaAdsCockpitPonto,
    MetaAdsCockpitResponse,
    MetaAdsCockpitSelos,
    MetaAdsLinha,
    MetaAdsPainelResponse,
    MetaAdsResumoDiarioResponse,
    MetaAdsRevisaoItem,
)
from backend.tests.mcp_apoio import contexto_falso, usar_sessao

CAM = "backend.mcp_crm.ferramentas.campanhas"


def _linha(nivel, id_, nome, mcg=1, opo=0, filhos=None, **kw):
    base = dict(
        nivel=nivel, id=id_, mcgId=mcg, nome=nome, status="ACTIVE", macId=1, investimento=100.0,
        impressoes=1000, cliques=50, leadsMeta=10, leadsCrm=8, mqls=4, oportunidades=opo, vendas=1,
        mrr=500.0, projeto=0.0, ctr=0.05, cpc=2.0, cpl=10.0, custoLeadCrm=12.5, custoMql=25.0,
        custoOportunidade=50.0, cac=100.0, retorno=5.0, horasPrimeiroContato=1.5, filhos=filhos or [],
    )
    base.update(kw)
    return MetaAdsLinha(**base)


def _painel():
    a1 = _linha("anuncio", 11, "Criativo A", mcg=1, opo=2)
    a2 = _linha("anuncio", 12, "Criativo B", mcg=1, opo=5)
    a3 = _linha("anuncio", 21, "Criativo C", mcg=2, opo=3)
    conj1 = _linha("conjunto", 5, "Conj 1", mcg=1, filhos=[a1, a2])
    conj2 = _linha("conjunto", 6, "Conj 2", mcg=2, filhos=[a3])
    c1 = _linha("campanha", 1, "Camp 1", mcg=1, filhos=[conj1])
    c2 = _linha("campanha", 2, "Camp 2", mcg=2, filhos=[conj2])
    return MetaAdsPainelResponse(
        temConta=True, total=_linha("total", None, "Total", mcg=None), campanhas=[c1, c2],
        naoIdentificada=None, cobertura=80.0,
        revisaoOrigem=[MetaAdsRevisaoItem(
            opoId=9, opoTitulo="Lead Joao", opoNomeContato="Joao Silva", opoDataRecebimento=None)],
    )


class ResumoCampanhasTests(unittest.TestCase):
    def test_total_e_campanhas_sem_filhos_nem_revisao(self) -> None:
        s = contexto_falso(emp_id=7)
        with usar_sessao(CAM, s), patch(f"{CAM}.indicadores.painel", return_value=_painel()) as p:
            r = campanhas.resumo_campanhas(ctx=None, data_inicial=date(2026, 10, 1))
        filtro = p.call_args.args[2]
        self.assertEqual((p.call_args.args[1], filtro.data_inicial), (7, date(2026, 10, 1)))
        self.assertEqual(set(r), {"total", "campanhas", "cobertura"})
        self.assertEqual(len(r["campanhas"]), 2)
        self.assertNotIn("filhos", r["campanhas"][0])
        self.assertNotIn("Joao", json.dumps(r, default=str))


class FunilPorCriativoTests(unittest.TestCase):
    def test_anuncios_ordenados_por_oportunidades(self) -> None:
        s = contexto_falso()
        with usar_sessao(CAM, s), patch(f"{CAM}.indicadores.painel", return_value=_painel()):
            r = campanhas.funil_por_criativo(ctx=None)
        self.assertEqual([a["nome"] for a in r["anuncios"]], ["Criativo B", "Criativo C", "Criativo A"])
        for chave in ("leadsCrm", "mqls", "oportunidades", "vendas", "investimento", "custoOportunidade", "cac"):
            self.assertIn(chave, r["anuncios"][0])
        self.assertNotIn("filhos", r["anuncios"][0])

    def test_filtra_por_campanha(self) -> None:
        s = contexto_falso()
        with usar_sessao(CAM, s), patch(f"{CAM}.indicadores.painel", return_value=_painel()):
            r = campanhas.funil_por_criativo(ctx=None, campanha_id=2)
        self.assertEqual([a["nome"] for a in r["anuncios"]], ["Criativo C"])


def _alerta(tipo, chave, msg, dados=None, nome=None):
    agora = datetime(2026, 10, 26, 10)
    return MetaAdsAlertaResponse(
        malId=1, malTipo=tipo, malChave=chave, malStatus="aberto", malMensagem=msg, malDados=dados,
        malPrimeiroEm=agora, malUltimoEm=agora, malResolvidoEm=None, alvoNome=nome,
    )


class AlertasCampanhasTests(unittest.TestCase):
    def test_alertas_sem_dados_pessoais(self) -> None:
        s = contexto_falso(emp_id=7)
        itens = [
            _alerta("sem_contato", "lead:42", "Lead Maria Souza (11999990000) recebido há 5 h sem contato.",
                    {"opo_id": 42, "contato": "Maria Souza", "telefone": "11999990000", "horas": 5}),
            _alerta("cpl", "anuncio:3", "CPL subiu", {"x": 1}, nome="Criativo A"),
        ]
        with usar_sessao(CAM, s), patch(f"{CAM}.alertas.listar", return_value=itens) as listar:
            r = campanhas.alertas_campanhas(ctx=None)
        self.assertEqual(listar.call_args.args[1:], (7, "aberto"))
        texto = json.dumps(r, default=str)
        self.assertNotIn("Maria", texto)
        self.assertNotIn("11999990000", texto)
        sem, outro = r["alertas"]
        self.assertEqual((sem["oportunidadeId"], sem["horas"]), (42, 5))
        self.assertEqual(outro["mensagem"], "CPL subiu")
        self.assertEqual(outro["alvo"], "Criativo A")


class ResumoDiarioTests(unittest.TestCase):
    def test_devolve_ultimo_quando_sem_data(self) -> None:
        s = contexto_falso(emp_id=7)
        resp = MetaAdsResumoDiarioResponse(
            mrsId=1, mrsData=date(2026, 10, 25), mrsInicio=date(2026, 10, 18), mrsFim=date(2026, 10, 24),
            mrsDados={"total": {}}, mrsLeitura="Texto", mrsAviso=None, mrsGeradoEm=datetime(2026, 10, 26, 8),
        )
        with usar_sessao(CAM, s), patch(f"{CAM}.resumo.obter", return_value=resp) as obter:
            r = campanhas.resumo_diario(ctx=None)
        self.assertEqual(obter.call_args.args[1:], (7, None))
        self.assertEqual(r["data"], "2026-10-25")
        self.assertEqual(r["leitura"], "Texto")
        self.assertEqual(r["dados"], {"total": {}})
        self.assertEqual({"data", "inicio", "fim", "dados", "leitura", "aviso", "geradoEm"}, set(r))


def _cockpit():
    criativo = MetaAdsCockpitCriativo(
        id=11, mcgId=1, nome="Criativo A", campanha="Camp 1", status="ACTIVE", ativo=True,
        investimento=100.0, leadsMeta=10, leadsCrm=8, mqls=4, cpl=10.0, taxaMql=50.0,
        quadrante="escalar", motivo=None, amostraPequena=False, recomendacao="Escalar", porque="Bom",
    )
    return MetaAdsCockpitResponse(
        temConta=True, inicio=date(2026, 10, 1), fim=date(2026, 10, 31),
        metas=MetaAdsCockpitMetas(cpl=150, taxaMql=10, custoMqlImplicito=1500, cplFator=1.5),
        total=_linha("total", None, "Total", mcg=None), taxaMql=50.0,
        anterior=_linha("total", None, "Total", mcg=None), anteriorInicio=date(2026, 8, 31),
        anteriorFim=date(2026, 9, 30), anteriorTemDados=True,
        selos=MetaAdsCockpitSelos(cpl="bom", taxaMql="bom", custoMql="bom", saude="bom"),
        funil=[MetaAdsCockpitEtapa(chave="leads", quantidade=10, taxa=None, custo=10.0, gargalo=False)],
        gargalo=None, fraseGargalo=None, intervalo="semana",
        serie=[MetaAdsCockpitPonto(
            inicio=date(2026, 10, 1), fim=date(2026, 10, 4), rotulo="1 a 4 out", investimento=100.0,
            impressoes=1000, cliques=50, leadsMeta=10, leadsCrm=8, mqls=4, cpl=10.0)],
        criativos=[criativo],
        operacao=MetaAdsCockpitOperacao(
            cobertura=80.0, horasPrimeiroContato=1.5, alertasAbertos=0, origemRevisar=1),
    )


class CockpitCampanhasTests(unittest.TestCase):
    def test_cockpit_campanhas_sem_dados_pessoais(self) -> None:
        s = contexto_falso(emp_id=7)
        with usar_sessao(CAM, s), patch(f"{CAM}.cockpit.montar", return_value=_cockpit()) as montar:
            r = campanhas.cockpit_campanhas(ctx=None, data_inicial=date(2026, 10, 1), data_final=date(2026, 10, 31))
        filtro = montar.call_args.args[2]
        self.assertEqual((montar.call_args.args[1], filtro.data_inicial, filtro.data_final), (7, date(2026, 10, 1), date(2026, 10, 31)))
        self.assertEqual(set(r), {
            "periodo", "metas", "total", "anterior", "anteriorTemDados", "taxaMql", "selos", "funil",
            "gargalo", "fraseGargalo", "intervalo", "serie", "criativos", "operacao",
        })
        self.assertNotIn("filhos", r["total"])
        texto = json.dumps(r, default=str, ensure_ascii=False)
        for proibido in ("revisaoOrigem", "Joao", "opoNomeContato", "opoTelefone", "opoEmail"):
            self.assertNotIn(proibido, texto)


if __name__ == "__main__":
    unittest.main()
