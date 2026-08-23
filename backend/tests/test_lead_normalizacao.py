import unittest

from backend.services.lead_normalizacao import (
    normalizar_email,
    normalizar_telefone,
    origem_aceitavel,
    rotular_origem,
    slugificar,
    variantes_telefone,
)


class NormalizacaoEmailTests(unittest.TestCase):
    def test_minusculas_e_sem_espacos(self) -> None:
        self.assertEqual(normalizar_email("  Maria@Exemplo.COM "), "maria@exemplo.com")

    def test_invalidos_viram_none(self) -> None:
        for valor in (None, "", "   ", "sem-arroba", "a@b", "a@@b.com", "x" * 300):
            self.assertIsNone(normalizar_email(valor), valor)

    def test_idempotente(self) -> None:
        uma = normalizar_email("Maria@Exemplo.com")
        self.assertEqual(normalizar_email(uma), uma)


class NormalizacaoTelefoneTests(unittest.TestCase):
    def test_celular_em_formatos_diferentes_converge(self) -> None:
        esperado = "5541999990000"
        for valor in ("+55 41 99999-0000", "(41) 99999-0000", "5541999990000", "41999990000"):
            self.assertEqual(normalizar_telefone(valor), esperado, valor)

    def test_celular_legado_de_8_digitos_ganha_o_nono(self) -> None:
        # E o caso que faz um lead antigo casar com um novo.
        self.assertEqual(normalizar_telefone("41 9999-0000"), "5541999990000")

    def test_fixo_nunca_ganha_o_nono_digito(self) -> None:
        self.assertEqual(normalizar_telefone("4133334444"), "554133334444")

    def test_ddd_55_de_santa_maria_nao_e_confundido_com_ddi(self) -> None:
        # 10 digitos e nacional COM DDD; o DDD 55 existe de verdade.
        self.assertEqual(normalizar_telefone("5532223333"), "555532223333")

    def test_prefixo_internacional_discado(self) -> None:
        self.assertEqual(normalizar_telefone("005541999990000"), "5541999990000")

    def test_estrangeiro_nao_e_mutilado(self) -> None:
        self.assertEqual(normalizar_telefone("+1 415 555 2671"), "14155552671")

    def test_sem_ddd_nao_e_elegivel_a_dedup(self) -> None:
        # "9999-0000" casaria com meio Brasil: melhor ficar de fora do dedup.
        for valor in ("9999-0000", "99990000", "1234", "abc", "", None):
            self.assertIsNone(normalizar_telefone(valor), valor)

    def test_ddd_invalido_recusado(self) -> None:
        self.assertIsNone(normalizar_telefone("0199990000"))

    def test_idempotente(self) -> None:
        uma = normalizar_telefone("+55 41 99999-0000")
        self.assertEqual(normalizar_telefone(uma), uma)


class VariantesTelefoneTests(unittest.TestCase):
    def test_inclui_forma_legada_sem_o_nono(self) -> None:
        self.assertEqual(
            variantes_telefone("5541999990000"), {"5541999990000", "554199990000"}
        )

    def test_fixo_tem_uma_forma_so(self) -> None:
        self.assertEqual(variantes_telefone("554133334444"), {"554133334444"})

    def test_vazio(self) -> None:
        self.assertEqual(variantes_telefone(None), set())


class SlugOrigemTests(unittest.TestCase):
    def test_slug_remove_acento_e_espaco(self) -> None:
        self.assertEqual(slugificar("Planilha de Leads"), "planilha_de_leads")
        self.assertEqual(slugificar("Indicação"), "indicacao")

    def test_rotulo_legivel(self) -> None:
        self.assertEqual(rotular_origem("planilha_leads"), "Planilha Leads")

    def test_guarda_contra_origem_lixo(self) -> None:
        self.assertTrue(origem_aceitavel("meta_ads"))
        self.assertFalse(origem_aceitavel("a"))
        self.assertFalse(origem_aceitavel(None))
        self.assertFalse(origem_aceitavel("x" * 70))


if __name__ == "__main__":
    unittest.main()
