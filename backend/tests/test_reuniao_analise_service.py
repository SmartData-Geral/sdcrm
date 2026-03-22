import asyncio
import io
import unittest

from fastapi import UploadFile

from backend.schemas.reuniao_analise import ReuniaoAnaliseProcessResult
from backend.services.reuniao_analise_service import _extract_files_summary, _normalize_meeting_result, _parse_csv_text


class ReuniaoAnaliseServiceTests(unittest.TestCase):
    def test_parse_csv_text(self) -> None:
        content = "coluna1,coluna2\nvalor1,valor2"
        parsed = _parse_csv_text(content)
        self.assertIn("Linha 1", parsed)
        self.assertIn("valor1 | valor2", parsed)

    def test_normalize_meeting_result(self) -> None:
        payload = {
            "resumo_reuniao": "Resumo",
            "feedback_ia": "Feedback",
            "lead_score_sugerido": "11",
            "temperatura_sugerida": "QUENTE",
            "dores_oportunidades_sugeridas": "Dores",
            "observacoes_sugeridas": "Obs",
            "proximos_passos_sugeridos": "Proximos passos",
        }
        result = _normalize_meeting_result(payload)
        self.assertIsInstance(result, ReuniaoAnaliseProcessResult)
        self.assertEqual(result.lead_score_sugerido, 10)
        self.assertEqual(result.temperatura_sugerida, "quente")

    def test_extract_files_summary_json_invalido(self) -> None:
        upload = UploadFile(filename="dados.json", file=io.BytesIO(b"{invalido"))
        items = asyncio.run(_extract_files_summary([upload]))
        self.assertEqual(len(items), 1)
        self.assertFalse(items[0].leitura_sucesso)
        self.assertIn("Falha ao ler arquivo", items[0].mensagem or "")


if __name__ == "__main__":
    unittest.main()
