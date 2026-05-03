import unittest

from backend.exceptions import BadRequestError
from backend.services.oportunidade_smart_agente_service import _validate_client_messages


class OportunidadeSmartAgenteValidacaoTests(unittest.TestCase):
    def test_rejeita_ultima_nao_usuario(self) -> None:
        with self.assertRaises(BadRequestError):
            _validate_client_messages(
                [
                    {"role": "user", "content": "a"},
                    {"role": "assistant", "content": "b"},
                ]
            )

    def test_rejeita_sem_alternancia(self) -> None:
        with self.assertRaises(BadRequestError):
            _validate_client_messages(
                [
                    {"role": "user", "content": "a"},
                    {"role": "user", "content": "b"},
                ]
            )

    def test_aceita_user_so(self) -> None:
        _validate_client_messages([{"role": "user", "content": "Olá"}])

    def test_aceita_conversa_alternada_terminando_user(self) -> None:
        _validate_client_messages(
            [
                {"role": "user", "content": "a"},
                {"role": "assistant", "content": "b"},
                {"role": "user", "content": "c"},
            ]
        )

    def test_rejeita_user_vazio(self) -> None:
        with self.assertRaises(BadRequestError):
            _validate_client_messages([{"role": "user", "content": "   "}])


if __name__ == "__main__":
    unittest.main()
