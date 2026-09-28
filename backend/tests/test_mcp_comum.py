import unittest
from unittest.mock import patch

from backend.exceptions import BadRequestError, NotFoundError
from backend.mcp_crm.ferramentas import _comum
from backend.tests.mcp_apoio import contexto_falso, oportunidade_falsa

MOD = "backend.mcp_crm.ferramentas._comum"


class ComumTests(unittest.TestCase):
    def test_limitar_pagina(self) -> None:
        self.assertEqual(_comum.limitar_pagina(0, 500), (1, 50))
        self.assertEqual(_comum.limitar_pagina(3, 0), (3, 1))
        self.assertEqual(_comum.limitar_pagina(2, 20), (2, 20))

    def test_oportunidade_ativa_usa_a_empresa_da_chave(self) -> None:
        s = contexto_falso(emp_id=7)
        opo = oportunidade_falsa()
        with patch(f"{MOD}.oportunidade_service.get_oportunidade", return_value=opo) as get:
            self.assertIs(_comum.obter_oportunidade_ativa(s, 5), opo)
        get.assert_called_once_with(s.db, 5, 7)

    def test_oportunidade_inativa_vira_nao_encontrada(self) -> None:
        s = contexto_falso()
        with patch(f"{MOD}.oportunidade_service.get_oportunidade", return_value=oportunidade_falsa(opoAtivo=False)):
            with self.assertRaises(NotFoundError) as cm:
                _comum.obter_oportunidade_ativa(s, 5)
        self.assertEqual(cm.exception.detail, "Oportunidade não encontrada")

    def test_oportunidade_de_outra_empresa_vira_nao_encontrada(self) -> None:
        s = contexto_falso()
        with patch(f"{MOD}.oportunidade_service.get_oportunidade", side_effect=NotFoundError("Oportunidade não encontrada")):
            with self.assertRaises(NotFoundError):
                _comum.obter_oportunidade_ativa(s, 5)

    def test_prefixar(self) -> None:
        self.assertEqual(_comum.prefixar(contexto_falso(nome="Claude"), "  Ligou.  "), "[via MCP · Claude] Ligou.")

    def test_validar_produto_de_outra_empresa(self) -> None:
        s = contexto_falso()
        s.db.scalar.return_value = None
        with self.assertRaises(BadRequestError) as cm:
            _comum.validar_produto(s, 99)
        self.assertEqual(cm.exception.detail, "Produto 99 não existe nesta empresa.")

    def test_validar_produto_existente(self) -> None:
        s = contexto_falso()
        s.db.scalar.return_value = 1
        _comum.validar_produto(s, 1)


if __name__ == "__main__":
    unittest.main()
