import asyncio
import io
import unittest

from fastapi import UploadFile

from backend.exceptions import BadRequestError
from backend.services.escopo_ai_service import _normalize_escopo, _read_files


class EscopoAiServiceTests(unittest.TestCase):
    def test_normalize_escopo_completa_campos_minimos(self) -> None:
        payload = {
            "escopo_inicial": {
                "visivel": True,
                "titulo": "Fases",
                "subtitulo": "Detalhes",
                "cards": [{"titulo": "", "subtitulo": "Base", "itens": [" Item 1 ", "", "Item 2"]}],
            }
        }
        response = _normalize_escopo(payload)
        self.assertEqual(response.titulo, "Fases")
        self.assertEqual(len(response.cards), 1)
        self.assertEqual(response.cards[0].titulo, "Bloco de escopo")
        self.assertEqual(response.cards[0].itens, ["Item 1", "Item 2"])

    def test_read_files_json_invalido(self) -> None:
        upload = UploadFile(filename="dados.json", file=io.BytesIO(b"{invalido"))
        with self.assertRaises(BadRequestError):
            asyncio.run(_read_files([upload]))

    def test_read_files_txt_sucesso(self) -> None:
        upload = UploadFile(filename="entrada.txt", file=io.BytesIO("texto base".encode("utf-8")))
        payload = asyncio.run(_read_files([upload]))
        self.assertEqual(len(payload.texts), 1)
        self.assertEqual(payload.texts[0].filename, "entrada.txt")
        self.assertIn("texto base", payload.texts[0].content)


if __name__ == "__main__":
    unittest.main()
