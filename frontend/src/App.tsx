import { Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "./pages/Login/LoginPage";
import DashboardPage from "./pages/Dashboard/DashboardPage";
import ComoConheceuPage from "./pages/ComoConheceu/ComoConheceuPage";
import EmpresasPage from "./pages/Empresas/EmpresasPage";
import MotivoCancelamentoPage from "./pages/MotivoCancelamento/MotivoCancelamentoPage";
import ProdutosPage from "./pages/Produtos/ProdutosPage";
import EtapasKanbanPage from "./pages/EtapasKanban/EtapasKanbanPage";
import UsuariosPage from "./pages/Usuarios/UsuariosPage";
import OportunidadesPage from "./pages/Oportunidades/OportunidadesPage";
import OportunidadeDetalhePage from "./pages/Oportunidades/OportunidadeDetalhePage";
import OportunidadesKanbanPage from "./pages/Oportunidades/OportunidadesKanbanPage";
import PropostaEditorPage from "./pages/Propostas/PropostaEditorPage";
import PropostasCadastrosPage from "./pages/Propostas/PropostasCadastrosPage";
import LlmAgentesPage from "./pages/LlmAgentes/LlmAgentesPage";
import ContratosCadastrosPage from "./pages/Contratos/ContratosCadastrosPage";
import ContratoNovoPage from "./pages/Contratos/ContratoNovoPage";
import ContratoEditorPage from "./pages/Contratos/ContratoEditorPage";
import { ProtectedRoute } from "./components/ProtectedRoute";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/como-conheceu"
        element={
          <ProtectedRoute>
            <ComoConheceuPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/motivos-cancelamento"
        element={
          <ProtectedRoute>
            <MotivoCancelamentoPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/produtos"
        element={
          <ProtectedRoute>
            <ProdutosPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/etapas-kanban"
        element={
          <ProtectedRoute>
            <EtapasKanbanPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/empresas"
        element={
          <ProtectedRoute>
            <EmpresasPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/usuarios"
        element={
          <ProtectedRoute>
            <UsuariosPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/oportunidades"
        element={
          <ProtectedRoute>
            <OportunidadesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/oportunidades-kanban"
        element={
          <ProtectedRoute>
            <OportunidadesKanbanPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/upsell/oportunidades"
        element={
          <ProtectedRoute>
            <OportunidadesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/upsell/oportunidades-kanban"
        element={
          <ProtectedRoute>
            <OportunidadesKanbanPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/oportunidades/:opoId"
        element={
          <ProtectedRoute>
            <OportunidadeDetalhePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/upsell/oportunidades/:opoId"
        element={
          <ProtectedRoute>
            <OportunidadeDetalhePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/propostas/:prpId/editor"
        element={
          <ProtectedRoute>
            <PropostaEditorPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/cadastros/propostas"
        element={
          <ProtectedRoute>
            <PropostasCadastrosPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/cadastros/agentes-ia"
        element={
          <ProtectedRoute>
            <LlmAgentesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/cadastros/contratos"
        element={
          <ProtectedRoute>
            <ContratosCadastrosPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/contratos/novo"
        element={
          <ProtectedRoute>
            <ContratoNovoPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/oportunidades/:opoId/contrato/novo"
        element={
          <ProtectedRoute>
            <ContratoNovoPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/upsell/oportunidades/:opoId/contrato/novo"
        element={
          <ProtectedRoute>
            <ContratoNovoPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/contratos/:ctrId/editor"
        element={
          <ProtectedRoute>
            <ContratoEditorPage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;

