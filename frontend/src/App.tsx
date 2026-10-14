import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ToastProvider } from './contexts/ToastContext';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import OTPPage from './pages/OTPPage';
import DashboardPage from './pages/DashboardPage';
import AnalyzePage from './pages/AnalyzePage';
import ResultPage from './pages/ResultPage';
import HistoryPage from './pages/HistoryPage';
import APIKeysPage from './pages/APIKeysPage';
import DocsPage from './pages/DocsPage';
import NotFoundPage from './pages/NotFoundPage';
import DashboardLayout from './layouts/DashboardLayout';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div className="flex items-center justify-center" style={{ minHeight: '100vh' }}><div className="animate-spin" style={{ width: 32, height: 32, border: '3px solid var(--bg-border)', borderTopColor: 'var(--primary)', borderRadius: '50%' }} /></div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            {/* Public */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/verify-otp" element={<OTPPage />} />
            <Route path="/docs" element={<DocsPage />} />

            {/* Protected — inside dashboard layout */}
            <Route path="/dashboard" element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}>
              <Route index element={<DashboardPage />} />
              <Route path="analyze" element={<AnalyzePage />} />
              <Route path="result/:requestId" element={<ResultPage />} />
              <Route path="history" element={<HistoryPage />} />
              <Route path="api-keys" element={<APIKeysPage />} />
            </Route>

            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
