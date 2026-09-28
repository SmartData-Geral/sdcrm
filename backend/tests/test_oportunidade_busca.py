import unittest
from unittest.mock import MagicMock, patch

from backend.services import oportunidade_service


def _where_sql(**kwargs) -> str:
    db = MagicMock()
    db.scalar.return_value = 0
    db.scalars.return_value.all.return_value = []
    with patch.object(oportunidade_service, "_reativar_standby_vencidos", return_value=False):
        oportunidade_service.list_oportunidades(db, company_id=1, **kwargs)
    stmt = db.scalars.call_args[0][0]
    sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    return sql.split("WHERE", 1)[1]


class ListOportunidadesBuscaTests(unittest.TestCase):
    def test_busca_procura_em_titulo_contato_empresa_e_email(self) -> None:
        where = _where_sql(busca="  acme ")
        for coluna in ("opoTitulo", "opoNomeContato", "opoEmpresaContato", "opoEmail"):
            with self.subTest(coluna=coluna):
                self.assertIn(coluna, where)
        self.assertIn("%acme%", where)

    def test_temperatura_filtra_sem_diferenciar_maiusculas(self) -> None:
        where = _where_sql(temperatura="Quente")
        self.assertIn("opoTemperatura", where)
        self.assertIn("'quente'", where)

    def test_sem_parametros_novos_nao_muda_o_filtro(self) -> None:
        where = _where_sql()
        for coluna in ("opoNomeContato", "opoEmpresaContato", "opoEmail", "opoTemperatura"):
            with self.subTest(coluna=coluna):
                self.assertNotIn(coluna, where)

    def test_titulo_continua_funcionando(self) -> None:
        where = _where_sql(titulo="proposta")
        self.assertIn("opoTitulo", where)
        self.assertNotIn("opoNomeContato", where)


if __name__ == "__main__":
    unittest.main()
