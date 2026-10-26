import unittest
from datetime import datetime
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth import get_current_user
from backend.database import get_db
from backend.exceptions import BadRequestError
from backend.models.etapa_kanban import EtapaKanban
from backend.models.usuario import Usuario
from backend.models.usuario_empresa import UsuarioEmpresa
from backend.routers import meta_ads_router
from backend.schemas.meta_ads import MetaAdsMonitorConfigUpdate
from backend.services.meta_ads import config_monitor
from backend.tests import banco_sqlite as b


def _etapa(db, emp_id, nome, ordem=1, pipeline="default", ativo=True):
    etapa = EtapaKanban(
        etkEmpId=emp_id, etkNome=nome, etkOrdem=ordem, etkPipeline=pipeline, etkAtivo=ativo
    )
    db.add(etapa)
    db.commit()
    return etapa


class ConfigMonitorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)

    def test_cria_com_padroes_e_acha_estagios_por_nome(self) -> None:
        mql = _etapa(self.db, self.emp.empId, "  Reunião de  Levantamento ", 1)
        opo = _etapa(self.db, self.emp.empId, "Reunião de Vendas", 2)
        cfg = config_monitor.obter_config(self.db, self.emp.empId)
        self.assertEqual(cfg.mmcEtkMqlId, mql.etkId)
        self.assertEqual(cfg.mmcEtkOportunidadeId, opo.etkId)
        self.assertEqual(float(cfg.mmcCplFator), 1.5)
        self.assertEqual(float(cfg.mmcGastoSemLead), 150)
        self.assertEqual(float(cfg.mmcFrequenciaMax), 3)
        self.assertEqual(cfg.mmcQuedaCtrPct, 30)
        self.assertEqual(cfg.mmcHorasSemContato, 24)
        self.assertEqual(float(cfg.mmcGastoMinRanking), 50)
        self.assertEqual(cfg.mmcHoraResumo, 8)
        self.assertTrue(cfg.mmcAlertaSemContato and cfg.mmcAlertaCpl)
        self.assertIsNotNone(cfg.mmcSemContatoDesde)
        # segundo acesso devolve a mesma linha
        self.assertEqual(config_monitor.obter_config(self.db, self.emp.empId).mmcId, cfg.mmcId)

    def test_estagios_inexistentes_ficam_nulos(self) -> None:
        _etapa(self.db, self.emp.empId, "Outra coisa")
        _etapa(self.db, self.emp.empId, "Reunião de Vendas", 2, ativo=False)
        cfg = config_monitor.obter_config(self.db, self.emp.empId)
        self.assertIsNone(cfg.mmcEtkMqlId)
        self.assertIsNone(cfg.mmcEtkOportunidadeId)

    def test_estagio_de_outra_empresa_recusado(self) -> None:
        outra = b.criar_empresa(self.db, "Outra")
        alheia = _etapa(self.db, outra.empId, "Reunião de Vendas")
        with self.assertRaises(BadRequestError) as ctx:
            config_monitor.atualizar_config(
                self.db, self.emp.empId, MetaAdsMonitorConfigUpdate(etapaMqlId=alheia.etkId)
            )
        self.assertEqual(ctx.exception.detail, "Estágio inválido para esta empresa")

    def test_atualiza_e_limpa_etapa(self) -> None:
        propria = _etapa(self.db, self.emp.empId, "Qualquer")
        r = config_monitor.atualizar_config(
            self.db,
            self.emp.empId,
            MetaAdsMonitorConfigUpdate(etapaMqlId=propria.etkId, cplFator=2.25, horaResumo=0),
        )
        self.assertEqual((r.etapaMqlId, r.cplFator, r.horaResumo), (propria.etkId, 2.25, 0))
        r = config_monitor.atualizar_config(
            self.db, self.emp.empId, MetaAdsMonitorConfigUpdate(etapaMqlId=None)
        )
        self.assertIsNone(r.etapaMqlId)
        self.assertEqual(r.cplFator, 2.25)

    def test_valores_invalidos_recusados(self) -> None:
        for campos in ({"cplFator": 0}, {"horaResumo": 24}, {"horaResumo": -1}, {"gastoSemLead": -5}):
            with self.assertRaises(ValueError):
                MetaAdsMonitorConfigUpdate(**campos)
        with self.assertRaises(ValueError):
            MetaAdsMonitorConfigUpdate(alertas={"inexistente": True})

    def test_religar_sem_contato_atualiza_data_inicio(self) -> None:
        cfg = config_monitor.obter_config(self.db, self.emp.empId)
        cfg.mmcSemContatoDesde = datetime(2020, 1, 1)
        self.db.commit()

        config_monitor.atualizar_config(
            self.db, self.emp.empId, MetaAdsMonitorConfigUpdate(alertas={"semContato": False})
        )
        self.assertEqual(cfg.mmcSemContatoDesde, datetime(2020, 1, 1))
        # ligado de novo: a data volta a ser "agora"
        r = config_monitor.atualizar_config(
            self.db, self.emp.empId, MetaAdsMonitorConfigUpdate(alertas={"semContato": True})
        )
        self.assertTrue(r.alertas["semContato"])
        self.assertGreater(cfg.mmcSemContatoDesde, datetime(2025, 1, 1))

    def test_manter_ligado_nao_mexe_na_data(self) -> None:
        cfg = config_monitor.obter_config(self.db, self.emp.empId)
        cfg.mmcSemContatoDesde = datetime(2020, 1, 1)
        self.db.commit()
        config_monitor.atualizar_config(
            self.db, self.emp.empId, MetaAdsMonitorConfigUpdate(alertas={"semContato": True})
        )
        self.assertEqual(cfg.mmcSemContatoDesde, datetime(2020, 1, 1))


class RotasConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = b.nova_sessao()
        self.emp = b.criar_empresa(self.db)
        self.usuario = SimpleNamespace(usuId=1, usuAdmin=True)
        app = FastAPI()
        app.include_router(meta_ads_router.router)
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.usuario
        self.http = TestClient(app)
        self.h = {"X-Company-Id": str(self.emp.empId)}
        self.url = "/api/meta-ads/monitoramento/config"

    def test_get_cria_e_put_atualiza(self) -> None:
        r = self.http.get(self.url, headers=self.h)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["cplFator"], 1.5)
        self.assertEqual(set(r.json()["alertas"]), {"cpl", "gasto", "frequencia", "ctr", "parado", "semContato"})
        r = self.http.put(self.url, headers=self.h, json={"horaResumo": 9, "alertas": {"ctr": False}})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["horaResumo"], 9)
        self.assertFalse(r.json()["alertas"]["ctr"])

    def test_put_exige_admin(self) -> None:
        self.usuario.usuAdmin = False
        r = self.http.put(self.url, headers=self.h, json={"horaResumo": 9})
        self.assertEqual(r.status_code, 403)
        # usuario comum vinculado a empresa consegue ler
        usu = Usuario(usuNome="U", usuEmail="u@x.com", usuSenhaHash="x", usuAdmin=False)
        self.db.add(usu)
        self.db.flush()
        self.db.add(UsuarioEmpresa(useUsuId=usu.usuId, useEmpId=self.emp.empId))
        self.db.commit()
        self.usuario.usuId = usu.usuId
        self.assertEqual(self.http.get(self.url, headers=self.h).status_code, 200)

    def test_put_etapa_alheia_da_400(self) -> None:
        outra = b.criar_empresa(self.db, "Outra")
        alheia = _etapa(self.db, outra.empId, "X")
        r = self.http.put(self.url, headers=self.h, json={"etapaMqlId": alheia.etkId})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["detail"], "Estágio inválido para esta empresa")


if __name__ == "__main__":
    unittest.main()
