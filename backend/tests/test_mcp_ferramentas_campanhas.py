import json
import unittest
from datetime import date, datetime
from unittest.mock import patch

from backend.mcp_crm.ferramentas import campanhas
from backend.schemas.meta_ads import (
    MetaAdsAlertaResponse,
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


if __name__ == "__main__":
    unittest.main()
