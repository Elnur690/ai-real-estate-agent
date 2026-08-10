import React, { useEffect, useState } from 'react';
import { LayoutDashboard, Users, DollarSign, Cpu, Database, Sliders, Building } from 'lucide-react';
import api from './api';
import { DashboardView } from './components/DashboardView';
import { TenantsView } from './components/TenantsView';
import { PaymentsView } from './components/PaymentsView';
import { AIConfigView } from './components/AIConfigView';
import { AppSettingsView } from './components/AppSettingsView';
import { ScrapersView } from './components/ScrapersView';

export function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'tenants' | 'payments' | 'ai-config' | 'scrapers' | 'settings'>('dashboard');
  const [appName, setAppName] = useState('RealEstate AI Agent');

  useEffect(() => {
    api.get('/settings').then(res => {
      if (res.data && res.data.app_name) {
        setAppName(res.data.app_name);
      }
    }).catch(console.error);
  }, []);

  const navItems = [
    { key: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { key: 'tenants', label: 'Tenants & Agents', icon: Users },
    { key: 'payments', label: 'Cash Payments', icon: DollarSign },
    { key: 'ai-config', label: 'AI Provider Config', icon: Cpu },
    { key: 'scrapers', label: 'Scrapers & Pipeline', icon: Database },
    { key: 'settings', label: 'App Settings', icon: Sliders },
  ];

  return (
    <div className="min-h-screen bg-dark-900 text-slate-100 flex flex-col md:flex-row">
      {/* Sidebar */}
      <aside className="w-full md:w-64 bg-dark-800/90 border-r border-slate-800 p-5 flex flex-col justify-between shrink-0">
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <Building className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-white text-base leading-tight">{appName}</h1>
              <span className="text-[10px] font-semibold text-emerald-400 tracking-wider uppercase">SaaS Admin Dashboard</span>
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

        <div className="pt-6 border-t border-slate-800 text-xs text-slate-500 space-y-1">
          <div>Platform Version 1.0</div>
          <div>All Phases 1–4 Built</div>
        </div>
      </aside>

      {/* Main Workspace */}
      <main className="flex-1 p-6 md:p-8 max-w-7xl mx-auto w-full overflow-y-auto">
        {activeTab === 'dashboard' && <DashboardView onNavigate={(tab) => setActiveTab(tab as any)} />}
        {activeTab === 'tenants' && <TenantsView />}
        {activeTab === 'payments' && <PaymentsView />}
        {activeTab === 'ai-config' && <AIConfigView />}
        {activeTab === 'scrapers' && <ScrapersView />}
        {activeTab === 'settings' && <AppSettingsView />}
      </main>
    </div>
  );
}

export default App;
