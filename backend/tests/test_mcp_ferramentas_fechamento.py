import unittest
from datetime import date
from unittest.mock import patch

from backend.exceptions import BadRequestError
from backend.mcp_crm.ferramentas import fechamento
from backend.mcp_crm.serializacao import Nomes
from backend.tests.mcp_apoio import contexto_falso, oportunidade_falsa, usar_sessao

FEC = "backend.mcp_crm.ferramentas.fechamento"


class MarcarGanhoTests(unittest.TestCase):
    def test_marca_ganho_com_tipo_traduzido(self) -> None:
        s = contexto_falso(emp_id=7)
        with usar_sessao(FEC, s), \
             patch(f"{FEC}.obter_oportunidade_ativa", return_value=oportunidade_falsa()), \
             patch(f"{FEC}.oportunidade_service.set_oportunidade_status_fechamento", return_value=oportunidade_falsa()) as st, \
             patch(f"{FEC}.responder_oportunidade", return_value={"id": 5}):
            fechamento.marcar_ganho(ctx=None, oportunidade_id=5, data_fechamento=date(2026, 9, 25), tipo="projeto", valor_fechado=15000.0)
        args, kwargs = st.call_args
        self.assertEqual(args[1:], (5, "ganho", 7))
        self.assertEqual((kwargs["data"].opoFechadoRecorrencia, kwargs["data"].opoValorFechado), (1, 15000.0))

    def test_ja_ganha_nao_altera(self) -> None:
        s = contexto_falso()
        with usar_sessao(FEC, s), \
             patch(f"{FEC}.obter_oportunidade_ativa", return_value=oportunidade_falsa(opoStatusFechamento="ganho")), \
             patch(f"{FEC}.oportunidade_service.set_oportunidade_status_fechamento") as st, \
             patch(f"{FEC}.responder_oportunidade", return_value={"id": 5}):
            r = fechamento.marcar_ganho(ctx=None, oportunidade_id=5, data_fechamento=date(2026, 9, 25), tipo="recorrencia", valor_fechado=1.0)
        st.assert_not_called()
        self.assertEqual(r["aviso"], "A oportunidade já está marcada como ganha.")

    def test_retorna_origem_externa_da_oportunidade_orm(self) -> None:
        """A resposta usa a instância ORM buscada no início, não o retorno do
        service (que é OportunidadeResponse e não tem opoOrigemSistema)."""
        s = contexto_falso(emp_id=7)
        with usar_sessao(FEC, s), \
             patch(f"{FEC}.obter_oportunidade_ativa", return_value=oportunidade_falsa(opoOrigemSistema="zapier")), \
             patch(f"{FEC}.oportunidade_service.set_oportunidade_status_fechamento", return_value=oportunidade_falsa()), \
             patch("backend.mcp_crm.ferramentas._comum.carregar_nomes", return_value=Nomes()):
            r = fechamento.marcar_ganho(ctx=None, oportunidade_id=5, data_fechamento=date(2026, 9, 25), tipo="projeto", valor_fechado=15000.0)
        self.assertEqual(r["origem_externa"]["sistema"], "zapier")


class MarcarPerdidoTests(unittest.TestCase):
    def test_grava_motivo_status_e_observacao_nessa_ordem(self) -> None:
        s = contexto_falso(emp_id=7, nome="Claude", usu_padrao=3)
        with usar_sessao(FEC, s), \
             patch(f"{FEC}.obter_oportunidade_ativa", return_value=oportunidade_falsa()), \
             patch(f"{FEC}.validar_motivo") as vm, \
             patch(f"{FEC}.oportunidade_service") as svc, \
             patch(f"{FEC}.oportunidade_historico_service.create_historico") as ch, \
             patch(f"{FEC}.responder_oportunidade", return_value={"id": 5}):
            fechamento.marcar_perdido(ctx=None, oportunidade_id=5, motivo_id=9, observacao="Escolheu concorrente")
        vm.assert_called_once_with(s, 9)
        self.assertEqual(svc.update_oportunidade.call_args[0][2].model_dump(exclude_unset=True), {"opoMcaId": 9})
        svc.set_oportunidade_status_fechamento.assert_called_once_with(s.db, 5, "perdido", 7)
        self.assertEqual(ch.call_args[0][2].ophConteudo, "[via MCP · Claude] Escolheu concorrente")
        self.assertEqual(ch.call_args.kwargs, {"company_id": 7, "usu_id": 3})

    def test_motivo_de_outra_empresa_nao_grava_nada(self) -> None:
        s = contexto_falso()
        with usar_sessao(FEC, s), \
             patch(f"{FEC}.obter_oportunidade_ativa", return_value=oportunidade_falsa()), \
             patch(f"{FEC}.validar_motivo", side_effect=BadRequestError("Motivo de perda 9 não existe nesta empresa.")), \
             patch(f"{FEC}.oportunidade_service") as svc, \
             patch(f"{FEC}.oportunidade_historico_service.create_historico") as ch:
            with self.assertRaises(BadRequestError):
                fechamento.marcar_perdido(ctx=None, oportunidade_id=5, motivo_id=9)
        svc.update_oportunidade.assert_not_called()
        svc.set_oportunidade_status_fechamento.assert_not_called()
        ch.assert_not_called()

    def test_ja_perdida_nao_altera(self) -> None:
        s = contexto_falso()
        with usar_sessao(FEC, s), \
             patch(f"{FEC}.obter_oportunidade_ativa", return_value=oportunidade_falsa(opoStatusFechamento="perdido")), \
             patch(f"{FEC}.validar_motivo"), \
             patch(f"{FEC}.oportunidade_service") as svc, \
             patch(f"{FEC}.responder_oportunidade", return_value={"id": 5}):
            r = fechamento.marcar_perdido(ctx=None, oportunidade_id=5, motivo_id=9)
        svc.set_oportunidade_status_fechamento.assert_not_called()
        self.assertEqual(r["aviso"], "A oportunidade já está marcada como perdida.")


class StandByEReativarTests(unittest.TestCase):
    def test_stand_by_com_data_passada_e_recusado(self) -> None:
        s = contexto_falso()
        with usar_sessao(FEC, s), \
             patch(f"{FEC}.hoje", return_value=date(2026, 9, 27)), \
             patch(f"{FEC}.obter_oportunidade_ativa", return_value=oportunidade_falsa()), \
             patch(f"{FEC}.oportunidade_service") as svc:
            with self.assertRaises(BadRequestError):
                fechamento.colocar_stand_by(ctx=None, oportunidade_id=5, data_retorno=date(2026, 9, 26))
        svc.set_oportunidade_stand_by.assert_not_called()

    def test_stand_by(self) -> None:
        s = contexto_falso(emp_id=7)
        with usar_sessao(FEC, s), \
             patch(f"{FEC}.hoje", return_value=date(2026, 9, 27)), \
             patch(f"{FEC}.obter_oportunidade_ativa", return_value=oportunidade_falsa()), \
             patch(f"{FEC}.oportunidade_service") as svc, \
             patch(f"{FEC}.responder_oportunidade", return_value={"id": 5}):
            fechamento.colocar_stand_by(ctx=None, oportunidade_id=5, data_retorno=date(2026, 10, 15))
        db, opo_id, data, emp = svc.set_oportunidade_stand_by.call_args[0]
        self.assertEqual((opo_id, data.opoDataUltimoContato, emp), (5, date(2026, 10, 15), 7))

    def test_reativar_ativa_nao_altera(self) -> None:
        s = contexto_falso()
        with usar_sessao(FEC, s), \
             patch(f"{FEC}.obter_oportunidade_ativa", return_value=oportunidade_falsa()), \
             patch(f"{FEC}.oportunidade_service") as svc, \
             patch(f"{FEC}.responder_oportunidade", return_value={"id": 5}):
            r = fechamento.reativar_oportunidade(ctx=None, oportunidade_id=5)
        svc.reativar_oportunidade_para_funil.assert_not_called()
        self.assertEqual(r["aviso"], "A oportunidade já está ativa no funil.")

    def test_reativar_perdida(self) -> None:
        s = contexto_falso(emp_id=7)
        with usar_sessao(FEC, s), \
             patch(f"{FEC}.obter_oportunidade_ativa", return_value=oportunidade_falsa(opoStatusFechamento="perdido")), \
             patch(f"{FEC}.oportunidade_service") as svc, \
             patch(f"{FEC}.responder_oportunidade", return_value={"id": 5}):
            fechamento.reativar_oportunidade(ctx=None, oportunidade_id=5)
        svc.reativar_oportunidade_para_funil.assert_called_once_with(s.db, 5, 7)


if __name__ == "__main__":
    unittest.main()
