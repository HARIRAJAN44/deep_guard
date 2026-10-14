import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  LayoutDashboard, Shield, History, Key, BookOpen,
  LogOut, ChevronRight, Cpu
} from 'lucide-react';

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/dashboard/analyze', label: 'Analyze Image', icon: Shield },
  { to: '/dashboard/history', label: 'History', icon: History },
  { to: '/dashboard/api-keys', label: 'API Keys', icon: Key },
];

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* Top Nav */}
      <nav className="nav">
        <NavLink to="/" className="nav-brand">
          <Cpu size={22} color="var(--primary)" />
          Deep<span className="logo-dot">Guard</span>
        </NavLink>
        <div className="nav-links">
          <NavLink to="/docs" className="nav-link">API Docs</NavLink>
          <div style={{ width: 1, height: 20, background: 'var(--bg-border)', margin: '0 8px' }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--primary-light)', border: '2px solid var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.8rem', fontWeight: 700, color: 'var(--primary)' }}>
              {user?.name?.[0]?.toUpperCase() ?? 'U'}
            </div>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{user?.name}</span>
          </div>
        </div>
      </nav>

      <div style={{ display: 'flex', flex: 1 }}>
        {/* Sidebar */}
        <aside className="sidebar">
          <div className="sidebar-section-label">Navigation</div>
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `sidebar-item${isActive ? ' active' : ''}`}
            >
              <Icon size={17} />
              {label}
            </NavLink>
          ))}

          <div style={{ marginTop: 'auto' }}>
            <div className="sidebar-section-label">Developer</div>
            <NavLink to="/docs" className="sidebar-item">
              <BookOpen size={17} />
              API Docs
            </NavLink>
            <button className="sidebar-item" onClick={handleLogout} style={{ color: 'var(--danger)' }}>
              <LogOut size={17} />
              Sign Out
            </button>
          </div>
        </aside>

        {/* Main content */}
        <main style={{ flex: 1, padding: '32px', overflowX: 'hidden' }}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
