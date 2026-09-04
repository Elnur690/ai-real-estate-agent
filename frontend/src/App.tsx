import React, { useEffect, useState } from 'react';
import { LayoutDashboard, Users, DollarSign, Package, Database, Sliders, Building, LogOut, ShieldCheck, Globe, Menu, X, MapPin, Store } from 'lucide-react';
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
import { SellersAdminView } from './components/SellersAdminView';
import { SellerPortalView } from './components/SellerPortalView';
import { TmaCrm } from './components/TmaCrm';
import { PortfolioPublicView } from './components/PortfolioPublicView';
import { useTranslation } from './i18n';

const isCustomDomainHost = () => {
  const host = window.location.hostname.toLowerCase();
  return !(
    host === 'localhost' ||
    host === '127.0.0.1' ||
    host.endsWith('.local') ||
    host === 'realtor.erma.shop' ||
    host.endsWith('.vercel.app') ||
    host.endsWith('.onrender.com') ||
    host.endsWith('.ngrok-free.app') ||
    host.endsWith('.ngrok.io')
  );
};

export function App() {
  const isCustomDomain = isCustomDomainHost();
  const isAdminOrLoginPath = Boolean(
    window.location.pathname.startsWith('/admin') ||
    window.location.pathname.startsWith('/login') ||
    window.location.hash.startsWith('#/admin') ||
    window.location.hash.startsWith('#/login')
  );

  const isPortfolioPublic = Boolean(
    (isCustomDomain && !isAdminOrLoginPath) ||
    window.location.pathname.startsWith('/p/') ||
    window.location.pathname.startsWith('/v/') ||
    window.location.pathname.startsWith('/@') ||
    window.location.pathname.startsWith('/portfolio/') ||
    window.location.pathname.startsWith('/vitrin/') ||
    window.location.hash.startsWith('#/p/') ||
    window.location.hash.startsWith('#/v/') ||
    window.location.hash.startsWith('#/@') ||
    window.location.hash.startsWith('#/portfolio/') ||
    window.location.hash.startsWith('#/vitrin/')
  );

  const isTmaMode = Boolean(
    window.location.hash.includes('tgWebAppData') ||
    window.location.search.includes('tgWebAppData') ||
    window.location.search.includes('tgWebAppPlatform') ||
    window.location.search.includes('tgWebAppVersion') ||
    window.location.hash.includes('crm') ||
    window.location.pathname.startsWith('/crm') ||
    (window.Telegram?.WebApp?.initData && window.Telegram.WebApp.initData.length > 0) ||
    window.location.search.includes('tma=') ||
    window.location.search.includes('mock_tg')
  );

  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => !!localStorage.getItem('token'));
  const [userName, setUserName] = useState<string>(() => localStorage.getItem('user_name') || 'Admin');
  const [userRole, setUserRole] = useState<string>(() => localStorage.getItem('user_role') || 'admin');
  const [activeTab, setActiveTab] = useState<'dashboard' | 'tenants' | 'payments' | 'plans' | 'sellers' | 'scrapers' | 'map' | 'settings'>('dashboard');
  const [appName, setAppName] = useState('RealEstate AI Agent');
  const [showProfileModal, setShowProfileModal] = useState<boolean>(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);
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

  const handleLoginSuccess = (token: string, name: string, role?: string) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user_name', name);
    const assignedRole = role || 'admin';
    localStorage.setItem('user_role', assignedRole);
    setUserName(name);
    setUserRole(assignedRole);
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user_name');
    localStorage.removeItem('user_role');
    setIsAuthenticated(false);
  };

  const handleSelectTab = (tab: typeof activeTab) => {
    setActiveTab(tab);
    setMobileMenuOpen(false);
  };

  // If public portfolio / shared property link, render public view without auth
  if (isPortfolioPublic) {
    return <PortfolioPublicView />;
  }

  // If in Telegram Mini App mode, render TMA CRM directly
  if (isTmaMode) {
    return <TmaCrm />;
  }

  if (!isAuthenticated) {
    return <LoginView onLoginSuccess={handleLoginSuccess} appName={appName} />;
  }

  // If logged in as Seller, render dedicated Seller Portal
  if (userRole === 'seller') {
    return (
      <div className="min-h-screen bg-dark-900 text-slate-100 flex flex-col">
        <header className="flex items-center justify-between px-6 py-4 bg-slate-900/90 border-b border-slate-800 sticky top-0 z-30 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Store className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-white text-base leading-tight">{appName}</h1>
              <span className="text-[10px] font-semibold text-blue-400 tracking-wider uppercase block">Satıcı Portalı (Reseller Portal)</span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right hidden sm:block">
              <div className="text-xs font-bold text-white">{userName}</div>
              <div className="text-[10px] text-slate-400">Rəsmi Satıcı Hesabı</div>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-rose-500/20 hover:text-rose-400 text-slate-300 rounded-xl text-xs font-semibold border border-slate-700 transition"
              title="Çıxış"
            >
              <LogOut className="w-4 h-4" />
              <span>Çıxış</span>
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto">
          <SellerPortalView />
        </main>
      </div>
    );
  }

  const navItems = [
    { key: 'dashboard', label: t.navDashboard, icon: LayoutDashboard },
    { key: 'tenants', label: t.navTenants, icon: Users },
    { key: 'sellers', label: 'Satıcılar', icon: Store },
    { key: 'payments', label: t.navPayments, icon: DollarSign },
    { key: 'plans', label: t.navPlans, icon: Package },
    { key: 'scrapers', label: t.navScrapers, icon: Database },
    { key: 'map', label: t.navMap, icon: MapPin },
    { key: 'settings', label: t.navSettings, icon: Sliders },
  ];

  return (
    <div className="min-h-screen bg-dark-900 text-slate-100 flex flex-col md:flex-row">
      {/* Mobile Top Navigation Bar */}
      <header className="md:hidden flex items-center justify-between px-4 py-3 bg-dark-800/95 border-b border-slate-800 sticky top-0 z-30 backdrop-blur-md">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-emerald-500 to-indigo-600 flex items-center justify-center shrink-0 shadow-md shadow-emerald-500/20">
            <Building className="w-4 h-4 text-white" />
          </div>
          <div className="truncate">
            <h1 className="font-bold text-white text-sm leading-tight truncate">{appName}</h1>
            <span className="text-[9px] font-semibold text-emerald-400 tracking-wider uppercase block">{t.saasAdmin}</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Quick Language Toggle */}
          <button
            onClick={() => setLanguage(lang === 'az' ? 'en' : 'az')}
            className="px-2 py-1 rounded-lg bg-dark-900 border border-slate-800 text-xs font-semibold text-slate-300 hover:text-white transition-colors"
            title="Dili dəyiş / Switch language"
          >
            {lang === 'az' ? '🇦🇿 AZ' : '🇬🇧 EN'}
          </button>

          {/* Hamburger Menu Toggle */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-xl bg-dark-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 transition-colors"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5 text-emerald-400" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </header>

      {/* Mobile Drawer Backdrop Overlay */}
      {mobileMenuOpen && (
        <div
          onClick={() => setMobileMenuOpen(false)}
          className="fixed inset-0 bg-black/70 backdrop-blur-sm z-40 md:hidden transition-opacity"
        />
      )}

      {/* Sidebar Navigation (Desktop Fixed & Mobile Slide-over Drawer) */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] bg-dark-800/95 border-r border-slate-800 p-5 flex flex-col justify-between shrink-0 transform transition-transform duration-300 ease-in-out md:relative md:translate-x-0 md:w-64 md:z-auto ${
          mobileMenuOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full'
        }`}
      >
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
            {/* Close button inside mobile drawer */}
            <button
              onClick={() => setMobileMenuOpen(false)}
              className="md:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-dark-700"
            >
              <X className="w-5 h-5" />
            </button>
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

          {/* Navigation Links */}
          <nav className="space-y-1.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.key;
              return (
                <button
                  key={item.key}
                  onClick={() => handleSelectTab(item.key as any)}
                  className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20 shadow-sm font-semibold'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-dark-700/50'
                  }`}
                >
                  <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
                  <span className="truncate">{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* User Account & Logout Footer */}
        <div className="pt-4 border-t border-slate-800 space-y-3">
          <div className="flex items-center justify-between gap-2 p-2 rounded-xl bg-dark-900/80 border border-slate-800/80 hover:border-emerald-500/30 transition-all">
            <button
              onClick={() => {
                setShowProfileModal(true);
                setMobileMenuOpen(false);
              }}
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
      <main className="flex-1 p-4 sm:p-6 md:p-8 max-w-7xl mx-auto w-full overflow-y-auto min-w-0">
        {activeTab === 'dashboard' && <DashboardView onNavigate={(tab) => handleSelectTab(tab as any)} />}
        {activeTab === 'tenants' && <TenantsView />}
        {activeTab === 'sellers' && <SellersAdminView />}
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
