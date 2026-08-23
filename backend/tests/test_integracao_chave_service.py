import os
import unittest

# O pepper e obrigatorio em producao; nos testes fixamos um valor conhecido.
os.environ.setdefault("API_KEY_PEPPER", "pepper-de-teste")

from backend.exceptions import BadRequestError
from backend.services import integracao_chave_service as servico


class GeracaoDeChaveTests(unittest.TestCase):
    def test_formato_e_prefixo(self) -> None:
        plana, prefixo, _hash = servico.gerar_chave()
        self.assertTrue(plana.startswith("sdcrm_"))
        self.assertEqual(servico.extrair_prefixo(plana), prefixo)
        self.assertEqual(len(prefixo), len("sdcrm_") + 12)

    def test_chaves_sao_distintas(self) -> None:
        geradas = {servico.gerar_chave()[0] for _ in range(50)}
        self.assertEqual(len(geradas), 50)

    def test_hash_determinístico(self) -> None:
        plana, _prefixo, h = servico.gerar_chave()
        self.assertEqual(servico.calcular_hash(plana), h)

    def test_um_caractere_diferente_nao_confere(self) -> None:
        plana, _prefixo, h = servico.gerar_chave()
        mutada = plana[:-1] + ("a" if plana[-1] != "a" else "b")
        self.assertNotEqual(servico.calcular_hash(mutada), h)

    def test_hash_depende_do_pepper(self) -> None:
        plana, _prefixo, h = servico.gerar_chave()
        original = servico.settings.API_KEY_PEPPER
        try:
            servico.settings.API_KEY_PEPPER = "outro-pepper"
            self.assertNotEqual(servico.calcular_hash(plana), h)
        finally:
            servico.settings.API_KEY_PEPPER = original


class ExtracaoDePrefixoTests(unittest.TestCase):
    def test_entrada_malformada_nao_levanta(self) -> None:
        for valor in (None, "", "lixo", "sdcrm_", "sdcrm_ZZZ_abc", "Bearer abc"):
            self.assertIsNone(servico.extrair_prefixo(valor), valor)

    def test_log_nunca_expoe_o_segredo(self) -> None:
        plana, prefixo, _hash = servico.gerar_chave()
        registrado = servico.prefixo_para_log(plana)
        self.assertEqual(registrado, prefixo)
        # o segredo (o que vem depois do prefixo) nao pode aparecer
        self.assertNotIn(plana.split("_")[-1], registrado)

    def test_log_de_valor_invalido(self) -> None:
        self.assertEqual(servico.prefixo_para_log("lixo"), "(malformado)")
        self.assertEqual(servico.prefixo_para_log(None), "(malformado)")


class EscoposTests(unittest.TestCase):
    def test_padrao_quando_vazio(self) -> None:
        self.assertEqual(servico.normalizar_escopos(None), "leads:write")
        self.assertEqual(servico.normalizar_escopos([]), "leads:write")

    def test_deduplica_e_ordena_pelo_catalogo(self) -> None:
        self.assertEqual(
            servico.normalizar_escopos(["mcp:read", "leads:write", "leads:write"]),
            "leads:write,mcp:read",
        )

    def test_escopo_desconhecido_recusado(self) -> None:
        with self.assertRaises(BadRequestError):
            servico.normalizar_escopos(["inventado:x"])


if __name__ == "__main__":
    unittest.main()
