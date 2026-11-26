import { Loader2 } from "lucide-react";
import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { AppShell } from "./components/layout/AppShell";
import { ThemeProvider } from "./theme/ThemeContext";
import Account from "./pages/Account";
import Admin from "./pages/Admin";
import CommandCenter from "./pages/CommandCenter";
import Borrowers from "./pages/Borrowers";
import LoanDetail from "./pages/LoanDetail";
import Loans from "./pages/Loans";
import Paper from "./pages/Paper";
import Market from "./pages/Market";
import NewLoan from "./pages/NewLoan";
import ComingSoon from "./pages/ComingSoon";
import Login from "./pages/Login";

function RequireAuth() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) {
    return (
      <div className="flex h-full items-center justify-center" role="status" aria-label="Loading">
        <Loader2 className="h-6 w-6 animate-spin text-cyan" />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  return <Outlet />;
}

function RequireAdmin() {
  const { user } = useAuth();
  return user?.is_admin ? <Outlet /> : <Navigate to="/" replace />;
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route element={<RequireAuth />}>
              <Route element={<AppShell />}>
                <Route index element={<CommandCenter />} />
                <Route path="loans" element={<Loans />} />
                <Route path="loans/new" element={<NewLoan />} />
                <Route path="loans/borrowers" element={<Borrowers />} />
                <Route path="loans/:id" element={<LoanDetail />} />
                <Route path="market" element={<Market />} />
                <Route path="paper" element={<Paper />} />
                <Route path="analytics" element={<ComingSoon title="Analytics" phase={7}>Loan, portfolio and cash-flow reports with CSV and PDF export will be here.</ComingSoon>} />
                <Route path="assistant" element={<ComingSoon title="Assistant" phase={8}>An optional assistant that explains your data. It only sees your data if you allow it.</ComingSoon>} />
                <Route path="account" element={<Account />} />
                <Route element={<RequireAdmin />}>
                  <Route path="admin" element={<Admin />} />
                </Route>
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
