import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import { Layout } from "./components/Layout";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { PlantsPage } from "./pages/PlantsPage";
import { PlantDetailPage } from "./pages/PlantDetailPage";
import { GroupsPage } from "./pages/GroupsPage";
import { GroupDetailPage } from "./pages/GroupDetailPage";
import { ForemenPage } from "./pages/ForemenPage";
import { ForemanDetailPage } from "./pages/ForemanDetailPage";
import { KpiAnalysisPage } from "./pages/KpiAnalysisPage";
import { ActionPlansPage } from "./pages/ActionPlansPage";
import { ReportsPage } from "./pages/ReportsPage";
import { DataQualityPage } from "./pages/DataQualityPage";
import { IntegrationStatusPage } from "./pages/IntegrationStatusPage";
import { AuditLogPage } from "./pages/AuditLogPage";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm" style={{ color: "var(--text-muted)", background: "var(--page-bg)" }}>
        Yükleniyor...
      </div>
    );
  }
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="/plants" element={<ProtectedRoute><PlantsPage /></ProtectedRoute>} />
      <Route path="/plants/:plantId" element={<ProtectedRoute><PlantDetailPage /></ProtectedRoute>} />
      <Route path="/groups" element={<ProtectedRoute><GroupsPage /></ProtectedRoute>} />
      <Route path="/groups/:chiefId" element={<ProtectedRoute><GroupDetailPage /></ProtectedRoute>} />
      <Route path="/foremen" element={<ProtectedRoute><ForemenPage /></ProtectedRoute>} />
      <Route path="/foremen/:foremanId" element={<ProtectedRoute><ForemanDetailPage /></ProtectedRoute>} />
      <Route path="/kpis" element={<ProtectedRoute><KpiAnalysisPage /></ProtectedRoute>} />
      <Route path="/action-plans" element={<ProtectedRoute><ActionPlansPage /></ProtectedRoute>} />
      <Route path="/reports" element={<ProtectedRoute><ReportsPage /></ProtectedRoute>} />
      <Route path="/data-quality" element={<ProtectedRoute><DataQualityPage /></ProtectedRoute>} />
      <Route path="/integration-status" element={<ProtectedRoute><IntegrationStatusPage /></ProtectedRoute>} />
      <Route path="/audit-log" element={<ProtectedRoute><AuditLogPage /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
