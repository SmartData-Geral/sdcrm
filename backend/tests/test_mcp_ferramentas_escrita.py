import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import ValidationError

from backend.exceptions import BadRequestError
from backend.mcp_crm.ferramentas import funil, historico, oportunidades
from backend.tests.mcp_apoio import contexto_falso, oportunidade_falsa, usar_sessao

OPO = "backend.mcp_crm.ferramentas.oportunidades"
FUN = "backend.mcp_crm.ferramentas.funil"
HIS = "backend.mcp_crm.ferramentas.historico"


class CriarLeadTests(unittest.TestCase):
    def test_passa_pelo_intake_com_chave_e_empresa(self) -> None:
        s = contexto_falso(emp_id=7)
        res = SimpleNamespace(status="created", opo_id=40, deduped_by=None, ciclo_anterior_id=None)
        with usar_sessao(OPO, s), \
             patch(f"{OPO}.lead_intake_service.processar_lead", return_value=res) as pl, \
             patch(f"{OPO}.url_da_oportunidade", return_value="https://crm/oportunidades/40"):
            r = oportunidades.criar_lead(ctx=None, nome="Maria", email="maria@acme.com", observacoes="Veio do evento")
        kwargs = pl.call_args.kwargs
        self.assertEqual((kwargs["emp_id"], kwargs["ich_id"]), (7, 11))
        payload = kwargs["payload"]
        self.assertEqual((payload.source, payload.name, payload.email, payload.notes), ("mcp", "Maria", "maria@acme.com", "Veio do evento"))
        self.assertEqual(s.opo_id, 40)
        self.assertEqual(
            r,
            {"status": "created", "oportunidade_id": 40, "deduplicado_por": None, "ciclo_anterior_id": None, "url": "https://crm/oportunidades/40"},
        )

    def test_sem_email_nem_telefone_e_recusado_antes_do_intake(self) -> None:
        s = contexto_falso()
        with usar_sessao(OPO, s), patch(f"{OPO}.lead_intake_service.processar_lead") as pl:
            with self.assertRaises(ValidationError):
                oportunidades.criar_lead(ctx=None, nome="Maria")
        pl.assert_not_called()


class AtualizarOportunidadeTests(unittest.TestCase):
    def test_envia_so_os_campos_informados(self) -> None:
        s = contexto_falso(emp_id=7)
        with usar_sessao(OPO, s), \
             patch(f"{OPO}.obter_oportunidade_ativa") as ativa, \
             patch(f"{OPO}.validar_produto") as vp, \
             patch(f"{OPO}.oportunidade_service.update_oportunidade", return_value=oportunidade_falsa()) as up, \
             patch(f"{OPO}.responder_oportunidade", return_value={"id": 5}):
            r = oportunidades.atualizar_oportunidade(ctx=None, oportunidade_id=5, titulo="Novo título", produto_id=1, valor=900.0)
        ativa.assert_called_once_with(s, 5)
        vp.assert_called_once_with(s, 1)
        db, opo_id, data, emp = up.call_args[0]
        self.assertEqual((opo_id, emp), (5, 7))
        self.assertEqual(data.model_dump(exclude_unset=True), {"opoTitulo": "Novo título", "opoProId": 1, "opoValorOportunidade": 900.0})
        self.assertEqual(r, {"id": 5})

    def test_sem_campos_e_recusado(self) -> None:
        s = contexto_falso()
        with usar_sessao(OPO, s), patch(f"{OPO}.obter_oportunidade_ativa"), \
             patch(f"{OPO}.oportunidade_service.update_oportunidade") as up:
            with self.assertRaises(BadRequestError) as cm:
                oportunidades.atualizar_oportunidade(ctx=None, oportunidade_id=5)
        self.assertEqual(cm.exception.detail, "Nenhum campo para atualizar.")
        up.assert_not_called()

    def test_oportunidade_de_outra_empresa_para_antes_de_gravar(self) -> None:
        from backend.exceptions import NotFoundError

        s = contexto_falso()
        with usar_sessao(OPO, s), \
             patch(f"{OPO}.obter_oportunidade_ativa", side_effect=NotFoundError("Oportunidade não encontrada")), \
             patch(f"{OPO}.oportunidade_service.update_oportunidade") as up:
            with self.assertRaises(NotFoundError):
                oportunidades.atualizar_oportunidade(ctx=None, oportunidade_id=5, titulo="x")
        up.assert_not_called()


class FunilEscritaTests(unittest.TestCase):
    def test_mover_etapa(self) -> None:
        s = contexto_falso(emp_id=7)
        with usar_sessao(FUN, s), \
             patch(f"{FUN}.obter_oportunidade_ativa") as ativa, \
             patch(f"{FUN}.oportunidade_service.mover_etapa", return_value=oportunidade_falsa()) as me, \
             patch(f"{FUN}.responder_oportunidade", return_value={"id": 5}):
            funil.mover_etapa(ctx=None, oportunidade_id=5, etapa_id=9)
        ativa.assert_called_once_with(s, 5)
        db, opo_id, data, emp = me.call_args[0]
        self.assertEqual((opo_id, data.opoEtkId, emp), (5, 9, 7))

    def test_qualificacao_chama_so_o_que_veio(self) -> None:
        s = contexto_falso(emp_id=7)
        with usar_sessao(FUN, s), \
             patch(f"{FUN}.obter_oportunidade_ativa", return_value=oportunidade_falsa()), \
             patch(f"{FUN}.oportunidade_service") as svc, \
             patch(f"{FUN}.responder_oportunidade", return_value={"id": 5}):
            funil.atualizar_qualificacao(ctx=None, oportunidade_id=5, temperatura="morno", reuniao_confirmada=False)
        self.assertEqual(svc.set_temperatura.call_args[0][2].opoTemperatura, "morno")
        svc.set_reuniao_confirmada.assert_called_once_with(s.db, 5, False, 7)
        svc.set_lead_score.assert_not_called()
        svc.set_proposta_enviada.assert_not_called()

    def test_qualificacao_sem_campos_e_recusada(self) -> None:
        s = contexto_falso()
        with usar_sessao(FUN, s), patch(f"{FUN}.obter_oportunidade_ativa"):
            with self.assertRaises(BadRequestError):
                funil.atualizar_qualificacao(ctx=None, oportunidade_id=5)


class RegistrarInteracaoTests(unittest.TestCase):
    def test_prefixa_e_usa_responsavel_padrao(self) -> None:
        s = contexto_falso(emp_id=7, usu_padrao=3, nome="Claude")
        criado = SimpleNamespace(ophId=30, ophUsuId=3, ophDataRegistro=datetime(2026, 9, 27, tzinfo=timezone.utc), ophConteudo="[via MCP · Claude] Ligou.")
        with usar_sessao(HIS, s), \
             patch(f"{HIS}.obter_oportunidade_ativa"), \
             patch(f"{HIS}.oportunidade_historico_service.create_historico", return_value=criado) as ch, \
             patch(f"{HIS}.carregar_autores", return_value={3: "Carlos"}):
            r = historico.registrar_interacao(ctx=None, oportunidade_id=5, conteudo="  Ligou. ")
        db, opo_id, data = ch.call_args[0]
        self.assertEqual((opo_id, data.ophConteudo), (5, "[via MCP · Claude] Ligou."))
        self.assertEqual(ch.call_args.kwargs, {"company_id": 7, "usu_id": 3})
        self.assertEqual(r["autor"], {"id": 3, "nome": "Carlos"})


if __name__ == "__main__":
    unittest.main()
