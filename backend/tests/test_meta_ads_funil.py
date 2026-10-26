import unittest
from datetime import date, datetime

from backend.models.etapa_kanban import EtapaKanban
from backend.models.oportunidade import Oportunidade
from backend.models.oportunidade_etapa_historico import OportunidadeEtapaHistorico
from backend.models.oportunidade_historico import OportunidadeHistorico
from backend.models.usuario import Usuario
from backend.services.meta_ads import funil
from backend.tests import banco_sqlite as b


class FunilTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)
        self.e = self.emp.empId
        self.etapas = {}
        for nome, ordem in [
            ("Contatos", 1), ("Qualificado", 2), ("Pré Reunião", 3),
            ("Reunião de Levantamento", 3), ("Reunião de Vendas", 4), ("Negociação", 9),
        ]:
            etk = EtapaKanban(etkEmpId=self.e, etkNome=nome, etkOrdem=ordem)
            self.db.add(etk)
            self.db.commit()
            self.etapas[nome] = etk.etkId

    def _opo(self, **campos):
        return b.criar_oportunidade(self.db, self.e, **campos)

    def _trans(self, opo, de, para, quando):
        self.db.add(OportunidadeEtapaHistorico(
            oehEmpId=self.e, oehOpoId=opo.opoId,
            oehEtkIdDe=self.etapas[de] if de else None,
            oehEtkIdPara=self.etapas[para], oehData=quando, oehOrigem="ui"))
        self.db.commit()

    def test_estagios_que_contam(self) -> None:
        ids = funil.estagios_que_contam(self.db, self.etapas["Reunião de Levantamento"])
        self.assertEqual(
            set(ids),
            {self.etapas[n] for n in ("Reunião de Levantamento", "Reunião de Vendas", "Negociação")},
        )

    def test_mql_pela_primeira_chegada(self) -> None:
        opo = self._opo()
        lev = "Reunião de Levantamento"
        self._trans(opo, None, "Contatos", datetime(2026, 10, 1, 12))
        self._trans(opo, "Contatos", lev, datetime(2026, 10, 5, 12))
        self._trans(opo, lev, "Contatos", datetime(2026, 10, 6, 12))
        self._trans(opo, "Contatos", lev, datetime(2026, 10, 8, 12))
        datas = funil.primeiras_datas(self.db, self.e, self.etapas[lev])
        self.assertEqual(datas, {opo.opoId: date(2026, 10, 5)})

    def test_data_em_horario_local(self) -> None:
        opo = self._opo()
        # 01:00 UTC de 06/10 = 22:00 de 05/10 em Sao Paulo
        self._trans(opo, None, "Negociação", datetime(2026, 10, 6, 1))
        datas = funil.primeiras_datas(self.db, self.e, self.etapas["Negociação"])
        self.assertEqual(datas[opo.opoId], date(2026, 10, 5))

    def test_pular_para_estagio_posterior_conta(self) -> None:
        opo = self._opo()
        self._trans(opo, "Contatos", "Negociação", datetime(2026, 10, 7, 12))
        mql = funil.primeiras_datas(self.db, self.e, self.etapas["Reunião de Levantamento"])
        vendas = funil.primeiras_datas(self.db, self.e, self.etapas["Reunião de Vendas"])
        self.assertEqual(mql[opo.opoId], date(2026, 10, 7))
        self.assertEqual(vendas[opo.opoId], date(2026, 10, 7))

    def test_estagio_de_mesma_ordem_nao_conta(self) -> None:
        opo = self._opo()
        self._trans(opo, "Contatos", "Pré Reunião", datetime(2026, 10, 7, 12))
        datas = funil.primeiras_datas(self.db, self.e, self.etapas["Reunião de Levantamento"])
        self.assertNotIn(opo.opoId, datas)

    def test_sem_estagio_configurado(self) -> None:
        self.assertEqual(funil.primeiras_datas(self.db, self.e, None), {})

    def test_ganho_sem_passagem_usa_fechamento(self) -> None:
        opo = self._opo(opoStatusFechamento="ganho", opoDataFechamento=date(2026, 10, 20))
        perdida = self._opo(opoStatusFechamento="perdido", opoDataFechamento=date(2026, 10, 20))
        datas = funil.primeiras_datas(self.db, self.e, self.etapas["Reunião de Vendas"])
        self.assertEqual(datas, {opo.opoId: date(2026, 10, 20)})
        self.assertNotIn(perdida.opoId, datas)

    def test_interacao_humana(self) -> None:
        opo = self._opo()
        self._trans(opo, None, "Contatos", datetime(2026, 10, 1, 8))
        self.db.add(OportunidadeHistorico(
            ophEmpId=self.e, ophOpoId=opo.opoId, ophUsuId=None,
            ophDataRegistro=datetime(2026, 10, 1, 8, 30), ophConteudo="auto"))
        self.db.commit()
        self.assertNotIn(opo.opoId, funil.primeira_interacao(self.db, self.e))

        self._trans(opo, "Contatos", "Qualificado", datetime(2026, 10, 1, 10))
        self.assertEqual(funil.primeira_interacao(self.db, self.e)[opo.opoId], datetime(2026, 10, 1, 10))

        usu = Usuario(usuNome="U", usuEmail="u@x.com", usuSenhaHash="x")
        self.db.add(usu)
        self.db.commit()
        self.db.add(OportunidadeHistorico(
            ophEmpId=self.e, ophOpoId=opo.opoId, ophUsuId=usu.usuId,
            ophDataRegistro=datetime(2026, 10, 1, 9), ophConteudo="ligou"))
        self.db.add(OportunidadeHistorico(
            ophEmpId=self.e, ophOpoId=opo.opoId, ophUsuId=usu.usuId, ophAtivo=False,
            ophDataRegistro=datetime(2026, 10, 1, 7), ophConteudo="inativo"))
        self.db.commit()
        self.assertEqual(funil.primeira_interacao(self.db, self.e)[opo.opoId], datetime(2026, 10, 1, 9))

    def test_carregar_funil(self) -> None:
        opo = self._opo(
            opoDataRecebimento=date(2026, 9, 28), opoStatusFechamento="ganho",
            opoDataFechamento=date(2026, 10, 20), opoValorFechado=1000, opoFechadoRecorrencia=0,
            opoReceitaPontual=False)
        outra = self._opo()
        self._trans(opo, "Contatos", "Reunião de Levantamento", datetime(2026, 10, 2, 12))
        cfg_mql = self.etapas["Reunião de Levantamento"]
        from backend.services.meta_ads import config_monitor
        cfg = config_monitor.obter_config(self.db, self.e)
        cfg.mmcEtkMqlId = cfg_mql
        self.db.commit()
        leads = funil.carregar_funil(self.db, self.e, Oportunidade.opoId == opo.opoId)
        self.assertEqual(len(leads), 1)
        lead = leads[0]
        self.assertEqual((lead.recebido, lead.mql, lead.contrato), (date(2026, 9, 28), date(2026, 10, 2), date(2026, 10, 20)))
        self.assertEqual(lead.mrr, 1000.0)
        self.assertEqual(lead.projeto, 0.0)
        self.assertNotIn(outra.opoId, [x.opo_id for x in leads])

    def test_contar_por_evento_no_periodo(self) -> None:
        lead = funil.FunilLead(
            opo_id=1, mcg_id=1, man_id=None, recebido=date(2026, 9, 28), mql=date(2026, 10, 2),
            oportunidade=None, contrato=date(2026, 10, 20), mrr=500.0, projeto=0.0,
            horas_primeiro_contato=4.0)
        r = funil.contar([lead], date(2026, 10, 1), date(2026, 10, 31), lambda x: x.mcg_id)
        self.assertEqual(r[1]["leadsCrm"], 0)
        self.assertEqual(r[1]["mqls"], 1)
        self.assertEqual(r[1]["oportunidades"], 0)
        self.assertEqual(r[1]["contratos"], 1)
        self.assertEqual(r[1]["mrr"], 500.0)
        r2 = funil.contar([lead], date(2026, 9, 1), date(2026, 9, 30), lambda x: x.mcg_id)
        self.assertEqual(r2[1]["leadsCrm"], 1)
        self.assertEqual(r2[1]["horasPrimeiroContatoMedia"], 4.0)
        self.assertEqual(r2[1]["mrr"], 0.0)


if __name__ == "__main__":
    unittest.main()
