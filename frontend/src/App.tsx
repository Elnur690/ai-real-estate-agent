import React, { useEffect, useState } from 'react';
import { LayoutDashboard, Users, DollarSign, Package, Database, Sliders, Building, LogOut, ShieldCheck, Globe } from 'lucide-react';
import api from './api';
import { LoginView } from './components/LoginView';
import { DashboardView } from './components/DashboardView';
import { TenantsView } from './components/TenantsView';
import { PaymentsView } from './components/PaymentsView';
import { PlansView } from './components/PlansView';
import { AppSettingsView } from './components/AppSettingsView';
import { ScrapersView } from './components/ScrapersView';
import { BakuPropertyMap } from './components/BakuPropertyMap';
import { AdminProfileModal } from './components/AdminProfileModal';
import { MapPin } from 'lucide-react';
import { useTranslation, Language } from './i18n';

export function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => !!localStorage.getItem('token'));
  const [userName, setUserName] = useState<string>(() => localStorage.getItem('user_name') || 'Admin');
  const [activeTab, setActiveTab] = useState<'dashboard' | 'tenants' | 'payments' | 'plans' | 'scrapers' | 'map' | 'settings'>('dashboard');
  const [appName, setAppName] = useState('RealEstate AI Agent');
  const [showProfileModal, setShowProfileModal] = useState<boolean>(false);
  const { t, lang, setLanguage } = useTranslation();
  const [, setRenderTrigger] = useState(0);

  useEffect(() => {
    const handleLogout = () => {
      setIsAuthenticated(false);
    };
    const handleLangChange = () => {
      setRenderTrigger(prev => prev + 1);
    };
    window.addEventListener('auth:logout', handleLogout);
    window.addEventListener('app:language_changed', handleLangChange);
    return () => {
      window.removeEventListener('auth:logout', handleLogout);
      window.removeEventListener('app:language_changed', handleLangChange);
    };
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      api.get('/settings').then(res => {
        if (res.data && res.data.app_name) {
          setAppName(res.data.app_name);
        }
      }).catch(console.error);
    }
  }, [isAuthenticated]);

  const handleLoginSuccess = (token: string, name: string) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user_name', name);
    setUserName(name);
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user_name');
    setIsAuthenticated(false);
  };

  if (!isAuthenticated) {
    return <LoginView onLoginSuccess={handleLoginSuccess} appName={appName} />;
  }

  const navItems = [
    { key: 'dashboard', label: t.navDashboard, icon: LayoutDashboard },
    { key: 'tenants', label: t.navTenants, icon: Users },
    { key: 'payments', label: t.navPayments, icon: DollarSign },
    { key: 'plans', label: t.navPlans, icon: Package },
    { key: 'scrapers', label: t.navScrapers, icon: Database },
    { key: 'map', label: t.navMap, icon: MapPin },
    { key: 'settings', label: t.navSettings, icon: Sliders },
  ];

  return (
    <div className="min-h-screen bg-dark-900 text-slate-100 flex flex-col md:flex-row">
      {/* Sidebar */}
      <aside className="w-full md:w-64 bg-dark-800/90 border-r border-slate-800 p-5 flex flex-col justify-between shrink-0">
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
                <Building className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="font-bold text-white text-base leading-tight">{appName}</h1>
                <span className="text-[10px] font-semibold text-emerald-400 tracking-wider uppercase">{t.saasAdmin}</span>
              </div>
            </div>
          </div>

          {/* Language Switcher */}
          <div className="flex items-center justify-between p-1.5 rounded-xl bg-dark-900/80 border border-slate-800/80 text-xs">
            <div className="flex items-center gap-1.5 px-2 text-slate-400 font-medium">
              <Globe className="w-3.5 h-3.5 text-emerald-400" />
              <span>Dil / Lang:</span>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setLanguage('az')}
                className={`px-2.5 py-1 rounded-lg font-semibold transition-all ${
                  lang === 'az'
                    ? 'bg-emerald-500 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                🇦🇿 AZ
              </button>
              <button
                onClick={() => setLanguage('en')}
                className={`px-2.5 py-1 rounded-lg font-semibold transition-all ${
                  lang === 'en'
                    ? 'bg-emerald-500 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                🇬🇧 EN
              </button>
            </div>
          </div>

          <nav className="space-y-1.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.key;
              return (
                <button
                  key={item.key}
                  onClick={() => setActiveTab(item.key as any)}
                  className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-dark-700/50'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
                  {item.label}
                </button>
              );
            })}
          </nav>
        </div>

        <div className="pt-4 border-t border-slate-800 space-y-3">
          <div className="flex items-center justify-between gap-2 p-2 rounded-xl bg-dark-900/80 border border-slate-800/80 hover:border-emerald-500/30 transition-all">
            <button
              onClick={() => setShowProfileModal(true)}
              className="flex items-center gap-2.5 text-left flex-1 min-w-0 group"
              title="Click to edit your admin profile & password"
            >
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-emerald-500 to-indigo-600 flex items-center justify-center text-white font-bold text-xs shrink-0 shadow-sm group-hover:scale-105 transition-transform">
                {userName.charAt(0).toUpperCase()}
              </div>
              <div className="truncate min-w-0">
                <div className="text-xs font-bold text-white group-hover:text-emerald-400 transition-colors truncate">
                  {userName}
                </div>
                <div className="text-[10px] text-slate-400 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3 text-emerald-400 shrink-0" />
                  <span>{t.adminProfile}</span>
                </div>
              </div>
            </button>

            <button
              onClick={handleLogout}
              title={t.signOut}
              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors shrink-0"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>

          <div className="text-[11px] text-slate-500 space-y-0.5 px-1">
            <div>Platform Version 1.0</div>
            <div>Baku Multi-Area AI Enabled</div>
          </div>
        </div>
      </aside>

      {/* Main Workspace */}
      <main className="flex-1 p-6 md:p-8 max-w-7xl mx-auto w-full overflow-y-auto">
        {activeTab === 'dashboard' && <DashboardView onNavigate={(tab) => setActiveTab(tab as any)} />}
        {activeTab === 'tenants' && <TenantsView />}
        {activeTab === 'payments' && <PaymentsView />}
        {activeTab === 'plans' && <PlansView />}
        {activeTab === 'scrapers' && <ScrapersView />}
        {activeTab === 'map' && <BakuPropertyMap />}
        {activeTab === 'settings' && <AppSettingsView />}
      </main>

      {/* Admin Profile Modal */}
      <AdminProfileModal
        isOpen={showProfileModal}
        onClose={() => setShowProfileModal(false)}
        onProfileUpdated={(name) => setUserName(name)}
      />
    </div>
  );
}

export default App;
