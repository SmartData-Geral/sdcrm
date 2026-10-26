import unittest
from datetime import datetime

from pydantic import ValidationError

from backend.core.cripto import decifrar
from backend.exceptions import BadRequestError, ConflictError, NotFoundError
from backend.models.meta_ads_conta import (
    STATUS_PENDENTE,
    STATUS_SINCRONIZANDO,
    STATUS_TOKEN_INVALIDO,
    MetaAdsConta,
)
from backend.schemas.meta_ads import MetaAdsContaCreate, MetaAdsContaUpdate
from backend.services.meta_ads import cliente_graph as g
from backend.services.meta_ads import contas
from backend.tests import banco_sqlite as b

TOKEN = "EAABsbCS1iHgBO-token-de-teste-9876"


class FabricaFalsa:
    def __init__(self, conta=None, erro=None, permissoes=None):
        self.conta, self.erro = conta, erro
        self.permissoes = permissoes if permissoes is not None else {"ads_read"}

    def __call__(self, token, **kw):
        self.token = token
        self.kw = kw
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def listar_permissoes(self):
        return self.permissoes

    def obter_conta(self, act):
        if self.erro:
            raise self.erro
        return self.conta


class ContasTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)
        self.origem = b.criar_origem(self.db, self.emp.empId, "Anúncios")

    def _criar(self, **kw):
        dados = dict(macNome="Conta principal", macContaExterna="act_123", token=TOKEN, origens=[self.origem.ccoId])
        dados.update(kw)
        return contas.criar_conta(self.db, self.emp.empId, MetaAdsContaCreate(**dados))

    def test_cria_com_token_cifrado_e_nunca_devolvido(self) -> None:
        resp = self._criar(macContaExterna="123")
        self.assertEqual(resp.macContaExterna, "act_123")
        self.assertEqual(resp.macTokenFinal, "9876")
        self.assertEqual(resp.origens, [self.origem.ccoId])
        self.assertEqual(resp.macStatus, STATUS_PENDENTE)
        self.assertNotIn(TOKEN, resp.model_dump_json())
        conta = self.db.get(MetaAdsConta, resp.macId)
        self.assertNotEqual(conta.macToken, TOKEN)
        self.assertEqual(decifrar(conta.macToken), TOKEN)

    def test_token_e_normalizado(self) -> None:
        resp = self._criar(token=f"  {TOKEN[:10]}\n{TOKEN[10:]}  ")
        self.assertEqual(decifrar(self.db.get(MetaAdsConta, resp.macId).macToken), TOKEN)

    def test_conta_duplicada(self) -> None:
        self._criar()
        with self.assertRaises(ConflictError):
            self._criar(macContaExterna="act_123")

    def test_conta_vazia(self) -> None:
        with self.assertRaises(BadRequestError):
            self._criar(macContaExterna="act_")

    def test_origem_de_outra_empresa_recusada(self) -> None:
        outra = b.criar_empresa(self.db, "Outra")
        origem_outra = b.criar_origem(self.db, outra.empId, "Anúncios")
        with self.assertRaises(BadRequestError):
            self._criar(origens=[origem_outra.ccoId])

    def test_conta_de_outra_empresa_nao_encontrada(self) -> None:
        resp = self._criar()
        outra = b.criar_empresa(self.db, "Outra")
        with self.assertRaises(NotFoundError):
            contas.obter_conta_da_empresa(self.db, outra.empId, resp.macId)

    def test_trocar_token_volta_para_pendente(self) -> None:
        resp = self._criar()
        conta = self.db.get(MetaAdsConta, resp.macId)
        conta.macStatus, conta.macMensagem = STATUS_TOKEN_INVALIDO, "Token inválido"
        self.db.commit()
        novo = "EAAB-outro-token-de-teste-5555"
        resp = contas.atualizar_conta(self.db, self.emp.empId, resp.macId, MetaAdsContaUpdate(token=novo))
        self.assertEqual((resp.macStatus, resp.macMensagem, resp.macTokenFinal), (STATUS_PENDENTE, None, "5555"))

    def test_trocar_token_durante_sync_nao_libera_a_trava(self) -> None:
        resp = self._criar()
        conta = self.db.get(MetaAdsConta, resp.macId)
        inicio = datetime(2026, 10, 14, 10, 0, 0)
        conta.macStatus, conta.macSyncIniciadaEm = STATUS_SINCRONIZANDO, inicio
        self.db.commit()
        novo = "EAAB-outro-token-de-teste-5555"
        resp = contas.atualizar_conta(self.db, self.emp.empId, resp.macId, MetaAdsContaUpdate(token=novo))
        self.assertEqual((resp.macStatus, resp.macTokenFinal), (STATUS_SINCRONIZANDO, "5555"))
        conta = self.db.get(MetaAdsConta, resp.macId)
        self.assertEqual(conta.macSyncIniciadaEm, inicio)
        self.assertEqual(decifrar(conta.macToken), novo)

    def test_nome_so_com_espacos_e_recusado(self) -> None:
        with self.assertRaises(ValidationError):
            MetaAdsContaCreate(macNome="   ", macContaExterna="act_1", token=TOKEN)
        with self.assertRaises(ValidationError):
            MetaAdsContaUpdate(macNome="   ")
        self.assertEqual(
            MetaAdsContaCreate(macNome="  Conta  ", macContaExterna="act_1", token=TOKEN).macNome, "Conta"
        )

    def test_atualiza_origens_e_ativo(self) -> None:
        resp = self._criar()
        resp = contas.atualizar_conta(
            self.db, self.emp.empId, resp.macId, MetaAdsContaUpdate(origens=[], macAtivo=False)
        )
        self.assertEqual((resp.origens, resp.macAtivo), ([], False))

    def test_testar_conexao_ok_grava_moeda_e_fuso(self) -> None:
        resp = self._criar()
        fab = FabricaFalsa(conta=g.ContaMeta("Conta no Meta", "BRL", "America/Sao_Paulo"))
        r = contas.testar_conta(self.db, self.emp.empId, resp.macId, fabrica_cliente=fab)
        self.assertEqual((r.ok, r.nome, r.moeda), (True, "Conta no Meta", "BRL"))
        self.assertEqual(fab.token, TOKEN)
        self.assertEqual(fab.kw, {"esperas": ()})
        self.assertEqual(self.db.get(MetaAdsConta, resp.macId).macFuso, "America/Sao_Paulo")

    def test_testar_recusa_token_com_escrita(self):
        resp = self._criar()
        fab = FabricaFalsa(conta=g.ContaMeta("X", "BRL", "America/Sao_Paulo"), permissoes={"ads_read", "ads_management"})
        r = contas.testar_conta(self.db, self.emp.empId, resp.macId, fabrica_cliente=fab)
        self.assertFalse(r.ok)
        self.assertEqual(r.mensagem, g.MENSAGEM_PERMISSAO_EXCESSIVA)

    def test_testar_conexao_com_erro_devolve_mensagem(self) -> None:
        resp = self._criar()
        fab = FabricaFalsa(erro=g.TokenInvalidoErro("Token inválido", 190))
        r = contas.testar_conta(self.db, self.emp.empId, resp.macId, fabrica_cliente=fab)
        self.assertEqual((r.ok, r.mensagem), (False, "Token inválido"))

    def test_listar_e_ids_ativos(self) -> None:
        a = self._criar(macContaExterna="act_1")
        bconta = self._criar(macContaExterna="act_2")
        contas.atualizar_conta(self.db, self.emp.empId, bconta.macId, MetaAdsContaUpdate(macAtivo=False))
        self.assertEqual(len(contas.listar_contas(self.db, self.emp.empId).items), 2)
        self.assertEqual(contas.ids_contas_ativas(self.db, self.emp.empId, None), [a.macId])
        self.assertEqual(contas.ids_contas_ativas(self.db, self.emp.empId, bconta.macId), [])


if __name__ == "__main__":
    unittest.main()
