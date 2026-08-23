import json
import unittest

from backend.services.integracao_log_service import redigir_payload


class RedacaoDePayloadTests(unittest.TestCase):
    def test_mascara_email_e_telefone(self) -> None:
        saida = redigir_payload({"email": "maria@exemplo.com", "phone": "+55 41 99999-0000"})
        self.assertEqual(saida["email"], "ma***@exemplo.com")
        self.assertTrue(saida["phone"].endswith("0000"))
        self.assertNotIn("9999-", saida["phone"])

    def test_allowlist_descarta_valores_desconhecidos(self) -> None:
        saida = redigir_payload({"source": "planilha", "campo_estranho": "conteudo-sensivel"})
        self.assertEqual(saida["source"], "planilha")
        self.assertNotIn("campo_estranho", saida)
        # o NOME da chave e registrado, o valor nunca
        self.assertEqual(saida["_extras"], ["campo_estranho"])
        self.assertNotIn("conteudo-sensivel", json.dumps(saida))

    def test_chave_de_api_colada_em_campo_inesperado_nao_e_persistida(self) -> None:
        # A razao de ser da allowlist.
        chave = "sdcrm_a1b2c3d4e5f6_" + "x" * 43
        saida = redigir_payload({"source": "planilha", "token": chave, "api_key": chave})
        self.assertNotIn("sdcrm_", json.dumps(saida))

    def test_vazios_sao_omitidos(self) -> None:
        saida = redigir_payload({"source": "planilha", "name": "   ", "email": None})
        self.assertNotIn("name", saida)
        self.assertNotIn("email", saida)

    def test_notes_longa_e_cortada_no_limite_do_campo(self) -> None:
        saida = redigir_payload({"source": "planilha", "notes": "n" * 50000})
        self.assertEqual(len(saida["notes"]), 2000)
        self.assertFalse(saida.get("_truncado"))

    def test_backstop_de_bytes_dispara_com_muitos_campos_grandes(self) -> None:
        # O corte por campo cobre o caso comum; este e o limite agregado.
        grande = {"notes": "n" * 5000, "observacoes": "o" * 5000}
        for campo in (
            "source", "external_id", "name", "company",
            "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
            "origem", "nome", "empresa",
        ):
            grande[campo] = "x" * 900
        saida = redigir_payload(grande)
        self.assertTrue(saida.get("_truncado"))
        self.assertGreater(saida.get("_bytes", 0), 8192)

    def test_nao_dicionario_nao_quebra(self) -> None:
        self.assertIsNone(redigir_payload(None))
        self.assertEqual(redigir_payload(["lista"])["_tipo_invalido"], "list")


if __name__ == "__main__":
    unittest.main()
