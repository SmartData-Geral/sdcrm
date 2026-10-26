import unittest
from datetime import date, datetime

from backend.exceptions import BadRequestError, NotFoundError
from backend.models.etapa_kanban import EtapaKanban
from backend.models.oportunidade_etapa_historico import OportunidadeEtapaHistorico
from backend.schemas.crm_dashboard import CrmDashboardFiltroParams
from backend.services.crm_dashboard_service import _query_rankings_analiticos
from backend.services.meta_ads import indicadores as ind
from backend.tests import banco_sqlite as b

INI, FIM = date(2026, 10, 1), date(2026, 10, 31)


class DerivadosTests(unittest.TestCase):
    def test_divisoes_por_zero_viram_none(self) -> None:
        d = ind.calcular_derivados(investimento=0, leads=0, vendas=0, mrr=0, projeto=0, impressoes=0, cliques=0)
        self.assertEqual(d, {"ctr": None, "cpc": None, "cpl": None, "cac": None, "retorno": None})

    def test_formulas(self) -> None:
        d = ind.calcular_derivados(investimento=300, leads=2, vendas=1, mrr=1000, projeto=600, impressoes=2000, cliques=50)
        self.assertEqual(d, {"ctr": 2.5, "cpc": 6.0, "cpl": 150.0, "cac": 300.0, "retorno": 42.0})


class PainelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)
        self.anuncios = b.criar_origem(self.db, self.emp.empId, "Anúncios")
        self.indicacao = b.criar_origem(self.db, self.emp.empId, "Indicação")
        self.conta = b.criar_conta(self.db, self.emp.empId, origens=[self.anuncios.ccoId])
        self.c1 = b.criar_campanha(self.db, self.conta, "1", "Campanha 1")
        self.c2 = b.criar_campanha(self.db, self.conta, "2", "Campanha 2", status="PAUSED")
        b.criar_insight(self.db, self.c1, date(2026, 10, 2), 100, impressoes=1000, cliques=20, leads=3)
        b.criar_insight(self.db, self.c1, date(2026, 10, 3), 200, impressoes=1000, cliques=30, leads=1)
        b.criar_insight(self.db, self.c2, date(2026, 10, 3), 100)
        b.criar_insight(self.db, self.c1, date(2026, 9, 30), 999)  # fora do periodo
        # Arvore de c1: conjunto s1 com os anuncios a1 e a2 (gasto por anuncio soma o da campanha)
        self.s1 = b.criar_conjunto(self.db, self.c1, "11", "Conjunto 1")
        self.a1 = b.criar_anuncio(self.db, self.s1, "111", "Anúncio A")
        self.a2 = b.criar_anuncio(self.db, self.s1, "112", "Anúncio B", status="PAUSED")
        b.criar_insight_anuncio(self.db, self.a1, date(2026, 10, 2), 100, impressoes=1000, cliques=20, leads=3)
        b.criar_insight_anuncio(self.db, self.a1, date(2026, 10, 3), 50, impressoes=400, cliques=10, leads=1)
        b.criar_insight_anuncio(self.db, self.a2, date(2026, 10, 3), 150, impressoes=600, cliques=20)
        b.criar_insight_anuncio(self.db, self.a1, date(2026, 9, 30), 999)  # fora do periodo
        cco = self.anuncios.ccoId
        # A: ligada a c1 (anuncio a1), recebida e ganha no periodo (MRR 1000)
        self.opo_a = b.criar_oportunidade(
            self.db, self.emp.empId, opoCcoId=cco, opoMcgId=self.c1.mcgId,
            opoManId=self.a1.manId, opoMetaAnuncioId="111",
            opoDataRecebimento=date(2026, 10, 5), opoStatusFechamento="ganho",
            opoDataFechamento=date(2026, 10, 20), opoValorFechado=1000, opoFechadoRecorrencia=0,
        )
        # B: ligada a c1 (anuncio a2), recebida, aberta
        self.opo_b = b.criar_oportunidade(
            self.db, self.emp.empId, opoCcoId=cco, opoMcgId=self.c1.mcgId,
            opoManId=self.a2.manId, opoMetaAnuncioId="112", opoDataRecebimento=date(2026, 10, 6),
        )
        # C: origem Anuncios sem campanha e sem sinal da Meta, recebida e perdida
        self.opo_c = b.criar_oportunidade(
            self.db, self.emp.empId, opoCcoId=cco, opoDataRecebimento=date(2026, 10, 7),
            opoStatusFechamento="perdido", opoDataFechamento=date(2026, 10, 8),
        )
        # D: outra origem, sem campanha -> nao e Meta
        b.criar_oportunidade(self.db, self.emp.empId, opoCcoId=self.indicacao.ccoId, opoDataRecebimento=date(2026, 10, 7))
        # E: outra empresa
        outra = b.criar_empresa(self.db, "Outra")
        b.criar_oportunidade(self.db, outra.empId, opoDataRecebimento=date(2026, 10, 7))

    def _painel(self, **kw):
        return ind.painel(self.db, self.emp.empId, ind.FiltroPainel(INI, FIM, **kw))

    def test_linhas_por_campanha(self) -> None:
        p = self._painel()
        self.assertTrue(p.temConta)
        por_id = {l.mcgId: l for l in p.campanhas}
        c1 = por_id[self.c1.mcgId]
        self.assertEqual(
            (c1.investimento, c1.leadsMeta, c1.leadsCrm, c1.vendas, c1.mrr, c1.cpl, c1.cac, c1.retorno),
            (300.0, 4, 2, 1, 1000.0, 75.0, 300.0, 40.0),
        )
        c2 = por_id[self.c2.mcgId]
        self.assertEqual((c2.investimento, c2.leadsCrm, c2.cpl), (100.0, 0, None))
        self.assertEqual([l.mcgId for l in p.campanhas], [self.c1.mcgId, self.c2.mcgId])

    def test_nao_identificada_e_total(self) -> None:
        p = self._painel()
        self.assertEqual((p.naoIdentificada.leadsCrm, p.naoIdentificada.investimento), (1, 0.0))
        self.assertEqual(
            (p.total.investimento, p.total.leadsCrm, p.total.vendas, p.total.mrr, p.total.cpl),
            (400.0, 3, 1, 1000.0, 100.0),
        )

    def _exigir(self, conta=None, valor=True) -> None:
        conta = conta or self.conta
        conta.macExigirRastreio = valor
        self.db.commit()

    def test_cpl_principal_usa_leads_meta(self) -> None:
        c1 = next(l for l in self._painel().campanhas if l.mcgId == self.c1.mcgId)
        self.assertEqual((c1.cpl, c1.custoLeadCrm), (75.0, 150.0))

    def test_arvore_campanha_conjunto_anuncio(self) -> None:
        p = self._painel()
        c1 = next(l for l in p.campanhas if l.mcgId == self.c1.mcgId)
        self.assertEqual((c1.nivel, c1.id), ("campanha", self.c1.mcgId))
        self.assertEqual([s.id for s in c1.filhos], [self.s1.mcjId])
        s1 = c1.filhos[0]
        self.assertEqual((s1.nivel, s1.mcgId, s1.nome), ("conjunto", self.c1.mcgId, "Conjunto 1"))
        self.assertEqual(sum(f.investimento for f in c1.filhos), c1.investimento)
        self.assertEqual(sum(a.investimento for a in s1.filhos), s1.investimento)
        por_id = {a.id: a for a in s1.filhos}
        a1, a2 = por_id[self.a1.manId], por_id[self.a2.manId]
        self.assertEqual(
            (a1.nivel, a1.mcgId, a1.investimento, a1.leadsMeta, a1.cpl, a1.leadsCrm, a1.vendas, a1.mrr),
            ("anuncio", self.c1.mcgId, 150.0, 4, 37.5, 1, 1, 1000.0),
        )
        self.assertEqual(
            (a2.status, a2.investimento, a2.leadsMeta, a2.cpl, a2.leadsCrm), ("PAUSED", 150.0, 0, None, 1)
        )
        self.assertEqual((s1.leadsCrm, s1.vendas, s1.leadsMeta), (2, 1, 4))
        self.assertEqual(a1.filhos, [])
        c2 = next(l for l in p.campanhas if l.mcgId == self.c2.mcgId)
        self.assertEqual(c2.filhos, [])
        self.assertEqual((p.total.nivel, p.naoIdentificada.nivel), ("total", "nao_identificada"))

    def _etapas(self) -> dict:
        etapas = {}
        for nome, ordem in [("Contatos", 1), ("Reunião de Levantamento", 3), ("Reunião de Vendas", 4)]:
            etk = EtapaKanban(etkEmpId=self.emp.empId, etkNome=nome, etkOrdem=ordem)
            self.db.add(etk)
            self.db.commit()
            etapas[nome] = etk.etkId
        return etapas

    def _trans(self, opo, de, para, quando) -> None:
        self.db.add(OportunidadeEtapaHistorico(
            oehEmpId=self.emp.empId, oehOpoId=opo.opoId, oehEtkIdDe=de, oehEtkIdPara=para,
            oehData=quando, oehOrigem="ui"))
        self.db.commit()

    def test_funil_por_anuncio(self) -> None:
        etapas = self._etapas()
        lead = b.criar_oportunidade(
            self.db, self.emp.empId, opoCcoId=self.anuncios.ccoId, opoMcgId=self.c1.mcgId,
            opoManId=self.a2.manId, opoMetaAnuncioId="112", opoDataRecebimento=date(2026, 10, 9),
            opoDataCriacao=datetime(2026, 10, 9, 12),
        )
        lev, vendas = etapas["Reunião de Levantamento"], etapas["Reunião de Vendas"]
        self._trans(lead, None, etapas["Contatos"], datetime(2026, 10, 9, 12))
        self._trans(lead, etapas["Contatos"], lev, datetime(2026, 10, 10, 12))
        self._trans(lead, lev, vendas, datetime(2026, 10, 12, 12))
        p = self._painel()
        c1 = next(l for l in p.campanhas if l.mcgId == self.c1.mcgId)
        s1 = c1.filhos[0]
        a2 = next(a for a in s1.filhos if a.id == self.a2.manId)
        self.assertEqual((a2.leadsCrm, a2.mqls, a2.oportunidades), (2, 1, 1))
        self.assertEqual((a2.custoMql, a2.custoOportunidade), (a2.investimento, a2.investimento))
        self.assertEqual(a2.horasPrimeiroContato, 24.0)
        # A (ganho sem passagem pelos estagios) e MQL e oportunidade pela data de fechamento
        a1 = next(a for a in s1.filhos if a.id == self.a1.manId)
        self.assertEqual((a1.mqls, a1.oportunidades), (1, 1))
        self.assertEqual((s1.mqls, s1.oportunidades, c1.mqls, c1.custoMql), (2, 2, 2, 150.0))
        self.assertEqual((p.total.mqls, p.total.oportunidades, p.total.custoMql), (2, 2, 200.0))

    def test_lead_com_campanha_manual_diferente_do_anuncio(self) -> None:
        # O anuncio a1 e da campanha c1, mas o vinculo manual diz c2: o lead conta so em c2.
        b.criar_oportunidade(
            self.db, self.emp.empId, opoCcoId=self.anuncios.ccoId, opoMcgId=self.c2.mcgId,
            opoMcgManual=True, opoManId=self.a1.manId, opoMetaAnuncioId="111",
            opoDataRecebimento=date(2026, 10, 9),
        )
        p = self._painel()
        por_id = {l.mcgId: l for l in p.campanhas}
        c1, c2 = por_id[self.c1.mcgId], por_id[self.c2.mcgId]
        self.assertEqual((c1.leadsCrm, c2.leadsCrm), (2, 1))
        a1 = next(a for a in c1.filhos[0].filhos if a.id == self.a1.manId)
        self.assertEqual(a1.leadsCrm, 1)
        self.assertEqual(c2.filhos, [])
        self.assertEqual(p.total.leadsCrm, 4)

    def test_exigir_rastreio_tira_origem_sem_sinal(self) -> None:
        self._exigir()
        p = self._painel()
        self.assertIsNone(p.naoIdentificada)
        revisao = p.revisaoOrigem
        self.assertEqual([r.opoId for r in revisao], [self.opo_c.opoId])
        self.assertEqual(revisao[0].opoDataRecebimento, date(2026, 10, 7))
        self.assertEqual(
            (p.total.investimento, p.total.leadsCrm, p.total.vendas, p.total.mrr), (400.0, 2, 1, 1000.0)
        )
        self.assertEqual(p.cobertura, 100.0)

    def test_exigir_rastreio_nenhuma_manual_com_sinal_conta_como_meta(self) -> None:
        self._exigir()
        lead = b.criar_oportunidade(
            self.db, self.emp.empId, opoCcoId=self.indicacao.ccoId, opoMcgManual=True,
            opoManId=self.a1.manId, opoMetaLeadId="L1", opoDataRecebimento=date(2026, 10, 9),
        )
        p = self._painel()
        self.assertEqual(p.naoIdentificada.leadsCrm, 1)
        c1 = next(l for l in p.campanhas if l.mcgId == self.c1.mcgId)
        a1 = next(a for a in c1.filhos[0].filhos if a.id == self.a1.manId)
        self.assertEqual((c1.leadsCrm, a1.leadsCrm), (2, 1))
        self.assertNotIn(lead.opoId, [r.opoId for r in p.revisaoOrigem])
        self.assertEqual(p.total.leadsCrm, 3)

    def test_exigir_rastreio_vale_por_conta(self) -> None:
        outra = b.criar_conta(self.db, self.emp.empId, act="act_222")
        self._exigir(outra)
        # Filtro na conta sem a flag: regra da fase 1
        p = self._painel(mac_id=self.conta.macId)
        self.assertEqual((p.naoIdentificada.leadsCrm, p.revisaoOrigem), (1, []))
        # Sem filtro: basta uma conta ativa da empresa com a flag
        p = self._painel()
        self.assertIsNone(p.naoIdentificada)
        self.assertEqual([r.opoId for r in p.revisaoOrigem], [self.opo_c.opoId])
        # Conta com a flag desativada nao liga a regra
        outra.macAtivo = False
        self.db.commit()
        self.assertEqual(self._painel().revisaoOrigem, [])

    def test_exigir_rastreio_com_filtro_de_conta(self) -> None:
        self._exigir()
        com_sinal = b.criar_oportunidade(
            self.db, self.emp.empId, opoCcoId=self.anuncios.ccoId, opoMetaLeadId="L2",
            opoDataRecebimento=date(2026, 10, 9),
        )
        outra = b.criar_conta(self.db, self.emp.empId, act="act_222")
        self._exigir(outra)
        p = self._painel(mac_id=self.conta.macId)
        self.assertEqual(p.naoIdentificada.leadsCrm, 1)  # com_sinal, pela origem mapeada na conta
        self.assertEqual([r.opoId for r in p.revisaoOrigem], [self.opo_c.opoId])
        p_outra = self._painel(mac_id=outra.macId)
        self.assertIsNone(p_outra.naoIdentificada)
        self.assertEqual(p_outra.revisaoOrigem, [])
        self.assertNotIn(com_sinal.opoId, [r.opoId for r in p.revisaoOrigem])

    def test_sem_flag_mantem_regra_da_fase_1(self) -> None:
        p = self._painel()
        self.assertEqual(p.revisaoOrigem, [])
        self.assertEqual((p.naoIdentificada.leadsCrm, p.naoIdentificada.vendas), (1, 0))
        self.assertEqual(
            (p.total.leadsCrm, p.total.vendas, p.total.cac, p.total.retorno, p.total.custoLeadCrm),
            (3, 1, 400.0, 30.0, 133.33),
        )

    def test_cobertura(self) -> None:
        self.assertEqual(self._painel().cobertura, 66.67)
        vazio = ind.painel(self.db, self.emp.empId, ind.FiltroPainel(date(2030, 1, 1), date(2030, 1, 31)))
        self.assertIsNone(vazio.cobertura)

    def test_bate_com_a_aba_fontes(self) -> None:
        rankings = _query_rankings_analiticos(
            self.db, self.emp.empId, CrmDashboardFiltroParams(data_inicial=INI, data_final=FIM)
        )
        fonte = next(f for f in rankings.fontes if f.fonte == "Anúncios")
        total = self._painel().total
        self.assertEqual((total.leadsCrm, total.vendas, total.mrr), (fonte.recebidas, fonte.ganhas, fonte.mrrIncremental))

    def test_somente_ativas(self) -> None:
        p = self._painel(somente_ativas=True)
        self.assertEqual([l.mcgId for l in p.campanhas], [self.c1.mcgId])
        self.assertEqual(p.total.investimento, 300.0)

    def test_filtro_por_conta(self) -> None:
        outra = b.criar_conta(self.db, self.emp.empId, act="act_222")
        c3 = b.criar_campanha(self.db, outra, "3", "Campanha 3")
        b.criar_insight(self.db, c3, date(2026, 10, 3), 50)
        p = self._painel(mac_id=outra.macId)
        self.assertEqual([l.mcgId for l in p.campanhas], [c3.mcgId])
        self.assertIsNone(p.naoIdentificada)  # a conta nova nao tem origens mapeadas

    def test_anuncios_de_outra_empresa_nao_entram(self) -> None:
        antes = self._painel()
        outra = b.criar_empresa(self.db, "Outra com anúncio")
        conta_outra = b.criar_conta(self.db, outra.empId, act="act_999")
        camp_outra = b.criar_campanha(self.db, conta_outra, "1", "Campanha 1")  # mesmo id externo
        conj_outra = b.criar_conjunto(self.db, camp_outra, "11", "Conjunto 1")
        anu_outra = b.criar_anuncio(self.db, conj_outra, "111", "Anúncio A")
        b.criar_insight(self.db, camp_outra, date(2026, 10, 2), 5000, leads=50)
        b.criar_insight_anuncio(self.db, anu_outra, date(2026, 10, 2), 5000, leads=50)
        b.criar_oportunidade(
            self.db, outra.empId, opoMcgId=camp_outra.mcgId, opoManId=anu_outra.manId,
            opoMetaAnuncioId="111", opoDataRecebimento=date(2026, 10, 5),
        )
        depois = self._painel()
        self.assertEqual(depois.model_dump(), antes.model_dump())
        ids = []

        def coletar(linhas):
            for l in linhas:
                ids.append((l.nivel, l.id))
                coletar(l.filhos)

        coletar(depois.campanhas)
        self.assertNotIn(("anuncio", anu_outra.manId), ids)
        self.assertNotIn(("conjunto", conj_outra.mcjId), ids)
        self.assertEqual(depois.total.investimento, 400.0)

    def test_periodo_vazio(self) -> None:
        p = ind.painel(self.db, self.emp.empId, ind.FiltroPainel(date(2030, 1, 1), date(2030, 1, 31)))
        self.assertEqual(p.campanhas, [])
        self.assertIsNone(p.naoIdentificada)
        self.assertEqual((p.total.investimento, p.total.cpl, p.total.retorno), (0.0, None, None))

    def test_empresa_sem_conta(self) -> None:
        outra = b.criar_empresa(self.db, "Sem conta")
        p = ind.painel(self.db, outra.empId, ind.FiltroPainel(INI, FIM))
        self.assertFalse(p.temConta)

    def test_resumo(self) -> None:
        r = ind.resumo(self.db, self.emp.empId, INI, FIM)
        self.assertEqual((r.temConta, r.investimento, r.leadsCrm, r.vendas, r.cac), (True, 400.0, 3, 1, 400.0))

    def test_detalhe_campanha(self) -> None:
        d = ind.detalhe_campanha(self.db, self.emp.empId, self.c1.mcgId, INI, FIM)
        self.assertEqual(d.campanha.investimento, 300.0)
        self.assertEqual(
            [(s.data, s.investimento, s.leadsMeta, s.leadsCrm) for s in d.serie],
            [
                (date(2026, 10, 2), 100.0, 3, 0),
                (date(2026, 10, 3), 200.0, 1, 0),
                (date(2026, 10, 5), 0.0, 0, 1),
                (date(2026, 10, 6), 0.0, 0, 1),
            ],
        )
        self.assertEqual(len(d.leads), 2)

    def test_detalhe_de_outra_empresa(self) -> None:
        outra = b.criar_empresa(self.db, "Outra 2")
        with self.assertRaises(NotFoundError):
            ind.detalhe_campanha(self.db, outra.empId, self.c1.mcgId, INI, FIM)

    def test_opcoes(self) -> None:
        nomes = [o.nome for o in ind.opcoes_campanhas(self.db, self.emp.empId).items]
        self.assertEqual(nomes, ["Campanha 1", "Campanha 2"])  # ativas primeiro
        self.assertEqual([c.macId for c in ind.opcoes_contas(self.db, self.emp.empId).items], [self.conta.macId])


class VinculoManualTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)
        self.conta = b.criar_conta(self.db, self.emp.empId)
        self.camp = b.criar_campanha(self.db, self.conta, "1", "Campanha 1")
        self.opo = b.criar_oportunidade(self.db, self.emp.empId)

    def test_define_e_marca_manual(self) -> None:
        r = ind.definir_campanha_oportunidade(self.db, self.emp.empId, self.opo.opoId, self.camp.mcgId)
        self.assertEqual((r.opoMcgId, r.opoMcgManual), (self.camp.mcgId, True))

    def test_nenhuma_tambem_e_manual(self) -> None:
        r = ind.definir_campanha_oportunidade(self.db, self.emp.empId, self.opo.opoId, None)
        self.assertEqual((r.opoMcgId, r.opoMcgManual), (None, True))

    def test_campanha_de_outra_empresa(self) -> None:
        outra = b.criar_empresa(self.db, "Outra")
        conta_outra = b.criar_conta(self.db, outra.empId)
        camp_outra = b.criar_campanha(self.db, conta_outra, "9", "X")
        with self.assertRaises(BadRequestError):
            ind.definir_campanha_oportunidade(self.db, self.emp.empId, self.opo.opoId, camp_outra.mcgId)

    def test_oportunidade_de_outra_empresa(self) -> None:
        outra = b.criar_empresa(self.db, "Outra")
        with self.assertRaises(NotFoundError):
            ind.definir_campanha_oportunidade(self.db, outra.empId, self.opo.opoId, None)


if __name__ == "__main__":
    unittest.main()
