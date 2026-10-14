import unittest
from datetime import date

from backend.exceptions import BadRequestError, NotFoundError
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
        cco = self.anuncios.ccoId
        # A: ligada a c1, recebida e ganha no periodo (MRR 1000)
        b.criar_oportunidade(
            self.db, self.emp.empId, opoCcoId=cco, opoMcgId=self.c1.mcgId,
            opoDataRecebimento=date(2026, 10, 5), opoStatusFechamento="ganho",
            opoDataFechamento=date(2026, 10, 20), opoValorFechado=1000, opoFechadoRecorrencia=0,
        )
        # B: ligada a c1, recebida, aberta
        b.criar_oportunidade(self.db, self.emp.empId, opoCcoId=cco, opoMcgId=self.c1.mcgId, opoDataRecebimento=date(2026, 10, 6))
        # C: origem Anuncios sem campanha, recebida e perdida
        b.criar_oportunidade(
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
            (300.0, 4, 2, 1, 1000.0, 150.0, 300.0, 40.0),
        )
        c2 = por_id[self.c2.mcgId]
        self.assertEqual((c2.investimento, c2.leadsCrm, c2.cpl), (100.0, 0, None))
        self.assertEqual([l.mcgId for l in p.campanhas], [self.c1.mcgId, self.c2.mcgId])

    def test_nao_identificada_e_total(self) -> None:
        p = self._painel()
        self.assertEqual((p.naoIdentificada.leadsCrm, p.naoIdentificada.investimento), (1, 0.0))
        self.assertEqual(
            (p.total.investimento, p.total.leadsCrm, p.total.vendas, p.total.mrr, p.total.cpl),
            (400.0, 3, 1, 1000.0, 133.33),
        )

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
