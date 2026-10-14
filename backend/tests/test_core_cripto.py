import unittest

from backend.core import cripto


class CriptoTests(unittest.TestCase):
    def test_ida_e_volta(self) -> None:
        cifrado = cripto.cifrar("EAAB-segredo-123")
        self.assertTrue(cifrado.startswith(cripto.PREFIXO))
        self.assertNotIn("segredo", cifrado)
        self.assertEqual(cripto.decifrar(cifrado), "EAAB-segredo-123")

    def test_cifras_diferentes_para_o_mesmo_texto(self) -> None:
        self.assertNotEqual(cripto.cifrar("abc"), cripto.cifrar("abc"))

    def test_chave_trocada_devolve_none(self) -> None:
        cifrado = cripto.cifrar("EAAB-segredo-123")
        original = cripto.settings.SECRETS_ENCRYPTION_KEY
        try:
            cripto.settings.SECRETS_ENCRYPTION_KEY = "outra-chave-bem-diferente"
            self.assertIsNone(cripto.decifrar(cifrado))
        finally:
            cripto.settings.SECRETS_ENCRYPTION_KEY = original

    def test_valor_invalido_devolve_none(self) -> None:
        for valor in (None, "", "texto-puro", "enc:v1:lixo"):
            self.assertIsNone(cripto.decifrar(valor), valor)


if __name__ == "__main__":
    unittest.main()
