import unittest
from types import SimpleNamespace

from backend.services.lead_intake_service import (
    CAMPOS_INTOCAVEIS,
    aplicar_merge,
    chave_de_lock,
    decidir_acao,
    derivar_titulo,
)


def payload(**kwargs):
    base = dict(
        source="planilha_leads",
        external_id=None,
        name=None,
        company=None,
        email=None,
        phone=None,
        utm_source=None,
        utm_medium=None,
        utm_campaign=None,
        utm_content=None,
        utm_term=None,
        notes=None,
        value=None,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


class DecidirAcaoTests(unittest.TestCase):
    def test_external_id_tem_precedencia(self) -> None:
        d = decidir_acao(match_external=10, match_aberto=(20, "email"), match_fechado=30)
        self.assertEqual((d.acao, d.opo_id, d.deduped_by), ("atualizar", 10, "external_id"))

    def test_match_aberto_por_email_atualiza(self) -> None:
        d = decidir_acao(None, (20, "email"), None)
        self.assertEqual((d.acao, d.opo_id, d.deduped_by), ("atualizar", 20, "email"))

    def test_match_aberto_por_telefone_atualiza(self) -> None:
        d = decidir_acao(None, (21, "phone"), None)
        self.assertEqual((d.acao, d.opo_id, d.deduped_by), ("atualizar", 21, "phone"))

    def test_match_apenas_fechado_cria_novo_ciclo(self) -> None:
        # Decisao de projeto: ciclo encerrado nunca vira atualizacao.
        d = decidir_acao(None, None, 30)
        self.assertEqual(d.acao, "criar")
        self.assertIsNone(d.opo_id)
        self.assertEqual(d.ciclo_anterior_id, 30)

    def test_sem_match_algum_cria(self) -> None:
        d = decidir_acao(None, None, None)
        self.assertEqual(d.acao, "criar")
        self.assertIsNone(d.ciclo_anterior_id)


class DerivarTituloTests(unittest.TestCase):
    def test_nome_e_empresa(self) -> None:
        self.assertEqual(
            derivar_titulo("Maria Silva", "ACME", None, None, "x"), "Maria Silva - ACME"
        )

    def test_cai_para_email_depois_telefone(self) -> None:
        self.assertEqual(derivar_titulo(None, None, "maria.silva@x.com", None, "s"), "Maria Silva")
        self.assertEqual(derivar_titulo(None, None, None, "+55 41 99999-0000", "s"), "+55 41 99999-0000")

    def test_nunca_vazio_e_respeita_limite(self) -> None:
        self.assertTrue(derivar_titulo(None, None, None, None, "planilha", "row_1"))
        self.assertLessEqual(len(derivar_titulo("N" * 400, "E" * 400, None, None, "s")), 300)


class AplicarMergeTests(unittest.TestCase):
    def test_nunca_sobrescreve_trabalho_humano(self) -> None:
        existente = {"opoEtkId": 7, "opoUsuResponsavelId": 3, "opoStatusFechamento": None}
        mudancas, _ = aplicar_merge(existente, payload(name="Outro", email="a@b.com"))
        for campo in CAMPOS_INTOCAVEIS:
            self.assertNotIn(campo, mudancas)

    def test_nome_existente_nao_e_apagado(self) -> None:
        existente = {"opoNomeContato": "Maria Silva"}
        mudancas, _ = aplicar_merge(existente, payload(name="M. Silva"))
        self.assertNotIn("opoNomeContato", mudancas)

    def test_nome_vazio_e_preenchido(self) -> None:
        mudancas, _ = aplicar_merge({"opoNomeContato": ""}, payload(name="Maria"))
        self.assertEqual(mudancas["opoNomeContato"], "Maria")

    def test_utm_sobrescreve_quando_vem_preenchida(self) -> None:
        mudancas, _ = aplicar_merge({"opoUtmSource": "google"}, payload(utm_source="meta"))
        self.assertEqual(mudancas["opoUtmSource"], "meta")

    def test_utm_vazia_nao_apaga_a_existente(self) -> None:
        mudancas, _ = aplicar_merge({"opoUtmSource": "google"}, payload(utm_source=None))
        self.assertNotIn("opoUtmSource", mudancas)

    def test_email_divergente_gera_observacao_e_nao_troca(self) -> None:
        existente = {"opoEmail": "maria@exemplo.com"}
        mudancas, observacoes = aplicar_merge(existente, payload(email="nova@outro.com"))
        self.assertNotIn("opoEmail", mudancas)
        self.assertEqual(len(observacoes), 1)
        self.assertIn("difere do cadastrado", observacoes[0])

    def test_mesmo_email_em_outro_formato_nao_gera_ruido(self) -> None:
        existente = {"opoEmail": "maria@exemplo.com"}
        _, observacoes = aplicar_merge(existente, payload(email="  MARIA@Exemplo.COM "))
        self.assertEqual(observacoes, [])


class ChaveDeLockTests(unittest.TestCase):
    def test_cabe_no_limite_do_mysql(self) -> None:
        self.assertLess(len(chave_de_lock(1, "m" * 200 + "@x.com", None)), 64)

    def test_estavel_e_distinta_por_empresa(self) -> None:
        a = chave_de_lock(1, "maria@exemplo.com", None)
        self.assertEqual(a, chave_de_lock(1, "maria@exemplo.com", None))
        self.assertNotEqual(a, chave_de_lock(2, "maria@exemplo.com", None))


if __name__ == "__main__":
    unittest.main()
