import unittest
from datetime import datetime

from backend.services import webhook_signature as sig


SEGREDO = "whsec_teste_fixo"
TIMESTAMP = 1787654651
CORPO = b'{"id":"evt_000123","type":"deal.won"}'


class AssinaturaTests(unittest.TestCase):
    def test_vetor_conhecido_e_estavel(self) -> None:
        # Vetor congelado. Se este valor mudar, o esquema de assinatura mudou e TODO
        # consumidor ja integrado passa a rejeitar as entregas -- e uma quebra de
        # contrato, nao um detalhe de implementacao.
        self.assertEqual(
            sig.assinar(SEGREDO, TIMESTAMP, CORPO),
            "c3ac4cba5c49c459adb11b50f4b163909ddaa8cc32c68c06b2957bfb1366262a",
        )

    def test_muda_com_corpo_timestamp_e_segredo(self) -> None:
        base = sig.assinar(SEGREDO, TIMESTAMP, CORPO)
        self.assertNotEqual(base, sig.assinar(SEGREDO, TIMESTAMP, CORPO + b" "))
        self.assertNotEqual(base, sig.assinar(SEGREDO, TIMESTAMP + 1, CORPO))
        self.assertNotEqual(base, sig.assinar("whsec_outro", TIMESTAMP, CORPO))

    def test_assina_os_bytes_exatos_e_nao_reserializa(self) -> None:
        # Mesmo JSON com espacamento diferente = bytes diferentes = assinatura diferente.
        compacto = b'{"a":1,"b":2}'
        espacado = b'{"a": 1, "b": 2}'
        self.assertNotEqual(
            sig.assinar(SEGREDO, TIMESTAMP, compacto), sig.assinar(SEGREDO, TIMESTAMP, espacado)
        )

    def test_verificacao_aceita_dentro_da_janela(self) -> None:
        cab = sig.cabecalho_assinatura(SEGREDO, TIMESTAMP, CORPO)
        self.assertTrue(sig.verificar_assinatura(SEGREDO, cab, TIMESTAMP, CORPO, TIMESTAMP + 10))

    def test_verificacao_rejeita_replay(self) -> None:
        cab = sig.cabecalho_assinatura(SEGREDO, TIMESTAMP, CORPO)
        fora = TIMESTAMP + sig.TOLERANCIA_REPLAY_SEGUNDOS + 1
        self.assertFalse(sig.verificar_assinatura(SEGREDO, cab, TIMESTAMP, CORPO, fora))

    def test_verificacao_rejeita_assinatura_errada(self) -> None:
        self.assertFalse(
            sig.verificar_assinatura(SEGREDO, "v1=deadbeef", TIMESTAMP, CORPO, TIMESTAMP)
        )

    def test_rotacao_aceita_qualquer_um_dos_dois_segredos(self) -> None:
        cab = sig.cabecalho_rotacao("whsec_novo", "whsec_antigo", TIMESTAMP, CORPO)
        for segredo in ("whsec_novo", "whsec_antigo"):
            self.assertTrue(
                sig.verificar_assinatura(segredo, cab, TIMESTAMP, CORPO, TIMESTAMP), segredo
            )


class RetryTests(unittest.TestCase):
    def test_cronograma_de_backoff(self) -> None:
        agora = datetime(2026, 8, 22, 12, 0, 0)
        esperado = [30, 120, 600, 3600, 21600, 86400]
        for i, segundos in enumerate(esperado, start=1):
            proxima = sig.proxima_tentativa(i, agora)
            self.assertEqual((proxima - agora).total_seconds(), segundos, i)

    def test_esgota_apos_a_ultima(self) -> None:
        agora = datetime(2026, 8, 22, 12, 0, 0)
        self.assertIsNone(sig.proxima_tentativa(len(sig.BACKOFF_SEGUNDOS) + 1, agora))

    def test_retry_after_menor_e_respeitado(self) -> None:
        agora = datetime(2026, 8, 22, 12, 0, 0)
        self.assertEqual((sig.proxima_tentativa(4, agora, 60) - agora).total_seconds(), 60)

    def test_retry_after_maior_e_ignorado(self) -> None:
        # Senao um consumidor poderia adiar a entrega indefinidamente.
        agora = datetime(2026, 8, 22, 12, 0, 0)
        self.assertEqual((sig.proxima_tentativa(1, agora, 99999) - agora).total_seconds(), 30)

    def test_quem_retenta_e_quem_nao(self) -> None:
        for status in (200, 201, 204):
            self.assertFalse(sig.deve_retentar(status, False), status)
        for status in (301, 302, 400, 401, 403, 404, 410, 422):
            self.assertFalse(sig.deve_retentar(status, False), status)
        for status in (408, 429, 500, 502, 503, 504):
            self.assertTrue(sig.deve_retentar(status, False), status)
        self.assertTrue(sig.deve_retentar(None, True))


if __name__ == "__main__":
    unittest.main()
