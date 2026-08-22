import React, { useEffect, useState } from 'react';
import { Sliders, Save, CheckCircle, Cpu, Key, CheckCircle2, AlertTriangle, Play, History, Building2, SlidersHorizontal, Database, Users, Plus, Trash2, ShieldCheck, Mail, Phone, Lock, Edit2, UserCheck, KeyRound } from 'lucide-react';
import api from '../api';
import { AIProviderConfigItem, AICallLogItem, AdminUser } from '../types';

interface TaskType {
  key: string;
  label: string;
  defaultProvider: string;
  defaultModel: string;
}

const modelOptions: Record<string, string[]> = {
  gemini: ['gemini-3.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro'],
  claude: ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022'],
  gpt: ['gpt-4o', 'gpt-4o-mini']
};

interface AppSettingsAITaskCardProps {
  task: TaskType;
  cfg: AIProviderConfigItem;
  onSave: (taskType: string, provider: string, modelName: string, apiKey?: string) => void;
  onTest: (provider: string, modelName: string, apiKey?: string) => void;
}

const AppSettingsAITaskCard: React.FC<AppSettingsAITaskCardProps> = ({ task, cfg, onSave, onTest }) => {
  const [selectedProvider, setSelectedProvider] = useState<string>(cfg.provider || 'gemini');
  const [selectedModel, setSelectedModel] = useState<string>(cfg.model_name || 'gemini-3.5-flash');
  const [apiKeyInput, setApiKeyInput] = useState('');

  useEffect(() => {
    setSelectedProvider(cfg.provider || 'gemini');
    setSelectedModel(cfg.model_name || 'gemini-3.5-flash');
  }, [cfg]);

  return (
    <div className="bg-dark-800/90 p-5 rounded-2xl border border-slate-800 space-y-4 flex flex-col justify-between shadow-xl">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold text-white">{task.label}</h3>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 font-semibold uppercase">
            {cfg.provider || 'gemini'}
          </span>
        </div>

        <div>
          <label className="text-[11px] font-semibold text-slate-300 block mb-1">Active Provider</label>
          <select
            value={selectedProvider}
            onChange={(e) => {
              const p = e.target.value;
              setSelectedProvider(p);
              setSelectedModel(modelOptions[p] ? modelOptions[p][0] : 'gemini-1.5-flash');
            }}
            className="w-full bg-dark-900 border border-slate-700/80 px-3 py-2 rounded-xl text-xs text-white"
          >
            <option value="gemini">Gemini (Default Free Tier)</option>
            <option value="claude">Claude (Anthropic)</option>
            <option value="gpt">GPT (OpenAI)</option>
          </select>
        </div>

        <div>
          <label className="text-[11px] font-semibold text-slate-300 block mb-1">Model Name</label>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="w-full bg-dark-900 border border-slate-700/80 px-3 py-2 rounded-xl text-xs text-white"
          >
            {(modelOptions[selectedProvider] || []).map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-[11px] font-semibold text-slate-300 block mb-1">
            API Key {cfg.api_key_masked && <span className="text-slate-500 font-mono">({cfg.api_key_masked})</span>}
          </label>
          <div className="relative">
            <Key className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
            <input
              type="password"
              placeholder={cfg.api_key_masked ? "Leave blank to keep existing key" : "Enter API key"}
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
              className="w-full bg-dark-900 border border-slate-700/80 pl-9 pr-3 py-2 rounded-xl text-xs text-white"
            />
          </div>
        </div>
      </div>

      <div className="pt-3 flex items-center justify-between gap-2 border-t border-slate-800">
        <button
          type="button"
          onClick={() => onTest(selectedProvider, selectedModel, apiKeyInput)}
          className="text-xs font-semibold text-purple-400 hover:text-purple-300 flex items-center gap-1"
        >
          <Play className="w-3 h-3" /> Test Connection
        </button>

        <button
          type="button"
          onClick={() => onSave(task.key, selectedProvider, selectedModel, apiKeyInput)}
          className="text-xs font-semibold bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/40 px-3.5 py-1.5 rounded-xl flex items-center gap-1 transition-all"
        >
          <Save className="w-3 h-3" /> Save Config
        </button>
      </div>
    </div>
  );
};

export const AppSettingsView: React.FC = () => {
  const [activeSubTab, setActiveSubTab] = useState<'branding' | 'ai' | 'automation' | 'admins'>('branding');
  const [settingsMap, setSettingsMap] = useState<Record<string, string>>({});
  const [savingBranding, setSavingBranding] = useState(false);
  const [brandingSaved, setBrandingSaved] = useState(false);

  // My Profile state
  const [myProfile, setMyProfile] = useState<{ id: number; name: string; email: string; phone?: string; role: string } | null>(null);
  const [profName, setProfName] = useState('');
  const [profEmail, setProfEmail] = useState('');
  const [profPhone, setProfPhone] = useState('');
  const [profCurrPassword, setProfCurrPassword] = useState('');
  const [profNewPassword, setProfNewPassword] = useState('');
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileSuccess, setProfileSuccess] = useState('');
  const [profileError, setProfileError] = useState('');

  // Admin users state
  const [admins, setAdmins] = useState<AdminUser[]>([]);
  const [loadingAdmins, setLoadingAdmins] = useState(false);
  const [showAddAdminModal, setShowAddAdminModal] = useState(false);
  const [newAdminName, setNewAdminName] = useState('');
  const [newAdminEmail, setNewAdminEmail] = useState('');
  const [newAdminPassword, setNewAdminPassword] = useState('');
  const [newAdminPhone, setNewAdminPhone] = useState('');
  const [addingAdmin, setAddingAdmin] = useState(false);
  const [adminError, setAdminError] = useState('');

  // Edit Admin Modal state
  const [editingAdmin, setEditingAdmin] = useState<AdminUser | null>(null);
  const [editAdminName, setEditAdminName] = useState('');
  const [editAdminEmail, setEditAdminEmail] = useState('');
  const [editAdminPhone, setEditAdminPhone] = useState('');
  const [editAdminPassword, setEditAdminPassword] = useState('');
  const [savingEditAdmin, setSavingEditAdmin] = useState(false);
  const [editAdminError, setEditAdminError] = useState('');

  // AI Provider state
  const [configs, setConfigs] = useState<AIProviderConfigItem[]>([]);
  const [callLogs, setCallLogs] = useState<AICallLogItem[]>([]);
  const [loadingAi, setLoadingAi] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);
  const [testing, setTesting] = useState(false);

  // Admin Telegram Alert State
  const [testingAlert, setTestingAlert] = useState(false);
  const [alertStatusMsg, setAlertStatusMsg] = useState<{ success: boolean; text: string } | null>(null);

  const taskTypes: TaskType[] = [
    { key: 'criteria_parsing', label: 'Criteria Parsing (Conversational Agent)', defaultProvider: 'gemini', defaultModel: 'gemini-3.5-flash' },
    { key: 'listing_parsing', label: 'Telegram Unformatted Listing Parser', defaultProvider: 'gemini', defaultModel: 'gemini-3.5-flash' },
    { key: 'match_scoring', label: 'Match Scoring Engine', defaultProvider: 'gemini', defaultModel: 'gemini-3.5-flash' },
  ];

  const loadSettings = async () => {
    try {
      const res = await api.get('/settings');
      if (res.data) {
        setSettingsMap((prev) => ({ ...prev, ...res.data }));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadMyProfile = async () => {
    try {
      const res = await api.get('/auth/me');
      if (res.data) {
        setMyProfile(res.data);
        setProfName(res.data.name || '');
        setProfEmail(res.data.email || '');
        setProfPhone(res.data.phone || '');
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadAdmins = async () => {
    setLoadingAdmins(true);
    try {
      const res = await api.get('/auth/admins');
      setAdmins(res.data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingAdmins(false);
    }
  };

  const loadAiConfigs = async () => {
    setLoadingAi(true);
    try {
      const [cRes, lRes] = await Promise.all([
        api.get('/ai-config'),
        api.get('/ai-config/logs').catch(() => ({ data: [] }))
      ]);
      setConfigs(cRes.data || []);
      setCallLogs(lRes.data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingAi(false);
    }
  };

  useEffect(() => {
    loadSettings();
    loadAiConfigs();
    loadAdmins();
    loadMyProfile();
  }, []);

  const handleUpdateMyProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileError('');
    setProfileSuccess('');
    setSavingProfile(true);
    try {
      const res = await api.put('/auth/profile', {
        name: profName,
        email: profEmail,
        phone: profPhone || undefined,
        current_password: profCurrPassword || undefined,
        new_password: profNewPassword || undefined
      });
      setMyProfile(res.data);
      setProfCurrPassword('');
      setProfNewPassword('');
      setProfileSuccess('Your administrator profile has been updated successfully!');
      setTimeout(() => setProfileSuccess(''), 4000);
      await loadAdmins();
    } catch (e: any) {
      setProfileError(e.response?.data?.detail || 'Failed to update administrator profile.');
    } finally {
      setSavingProfile(false);
    }
  };

  const handleOpenEditAdmin = (adm: AdminUser) => {
    setEditingAdmin(adm);
    setEditAdminName(adm.name);
    setEditAdminEmail(adm.email);
    setEditAdminPhone(adm.phone || '');
    setEditAdminPassword('');
    setEditAdminError('');
  };

  const handleSaveEditAdmin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingAdmin) return;
    setEditAdminError('');
    setSavingEditAdmin(true);
    try {
      await api.put(`/auth/admins/${editingAdmin.id}`, {
        name: editAdminName,
        email: editAdminEmail,
        phone: editAdminPhone || undefined,
        password: editAdminPassword || undefined
      });
      setEditingAdmin(null);
      await loadAdmins();
      await loadMyProfile();
    } catch (e: any) {
      setEditAdminError(e.response?.data?.detail || 'Failed to update administrator.');
    } finally {
      setSavingEditAdmin(false);
    }
  };

  const handleCreateAdmin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAdminError('');
    setAddingAdmin(true);
    try {
      await api.post('/auth/admins', {
        name: newAdminName,
        email: newAdminEmail,
        password: newAdminPassword,
        phone: newAdminPhone || undefined
      });
      setShowAddAdminModal(false);
      setNewAdminName('');
      setNewAdminEmail('');
      setNewAdminPassword('');
      setNewAdminPhone('');
      await loadAdmins();
    } catch (e: any) {
      setAdminError(e.response?.data?.detail || 'Failed to create administrator account.');
    } finally {
      setAddingAdmin(false);
    }
  };

  const handleDeleteAdmin = async (adminId: number, adminName: string) => {
    if (!window.confirm(`Are you sure you want to remove administrator "${adminName}"?`)) return;
    try {
      await api.delete(`/auth/admins/${adminId}`);
      await loadAdmins();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Failed to remove administrator.');
    }
  };

  const handleSaveBranding = async (e: React.FormEvent) => {
    e.preventDefault();
    setBrandingSaved(false);
    setSavingBranding(true);
    try {
      await api.post('/settings', { settings: settingsMap });
      setBrandingSaved(true);
      setTimeout(() => setBrandingSaved(false), 3000);
    } catch (e) {
      console.error(e);
    } finally {
      setSavingBranding(false);
    }
  };

  const getConfigForTask = (taskType: string): AIProviderConfigItem => {
    return configs.find(c => c.task_type === taskType) || {
      id: 0,
      task_type: taskType as any,
      provider: 'gemini',
      model_name: 'gemini-3.5-flash',
      api_key_masked: '',
      is_active: true,
      updated_at: new Date().toISOString()
    };
  };

  const handleSaveAiConfig = async (taskType: string, provider: string, modelName: string, apiKey?: string) => {
    try {
      await api.post('/ai-config', {
        task_type: taskType,
        provider,
        model_name: modelName,
        api_key: apiKey || undefined
      });
      loadAiConfigs();
    } catch (e) {
      console.error(e);
    }
  };

  const handleTestConnection = async (provider: string, modelName: string, apiKey?: string) => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await api.post('/ai-config/test-connection', {
        provider,
        model_name: modelName,
        api_key: apiKey
      });
      setTestResult(res.data);
    } catch (e: any) {
      setTestResult({ success: false, error: e.message });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-dark-800/80 border border-slate-800 p-6 rounded-2xl shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center">
              <Sliders className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white tracking-tight">System Settings & Configurations</h2>
              <p className="text-xs text-slate-400">Manage runtime app parameters, admin accounts, AI Provider models, and automation</p>
            </div>
          </div>
        </div>

        {/* Sub-Navigation Tabs */}
        <div className="flex items-center gap-1 bg-dark-900/90 p-1.5 rounded-xl border border-slate-800 self-start sm:self-auto flex-wrap">
          <button
            onClick={() => setActiveSubTab('branding')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeSubTab === 'branding'
                ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Building2 className="w-3.5 h-3.5" />
            <span>App Branding & Info</span>
          </button>

          <button
            onClick={() => setActiveSubTab('admins')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeSubTab === 'admins'
                ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            <span>Admin Users ({admins.length})</span>
          </button>

          <button
            onClick={() => setActiveSubTab('ai')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeSubTab === 'ai'
                ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Cpu className="w-3.5 h-3.5" />
            <span>AI Provider Config</span>
          </button>

          <button
            onClick={() => setActiveSubTab('automation')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeSubTab === 'automation'
                ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>Scraper Defaults</span>
          </button>
        </div>
      </div>

      {/* SUB-TAB 1: App Branding & Runtime Settings */}
      {activeSubTab === 'branding' && (
        <form onSubmit={handleSaveBranding} className="bg-dark-800/90 p-6 rounded-2xl border border-slate-800 space-y-5 shadow-xl">
          <div>
            <h3 className="text-base font-bold text-white mb-1">Runtime App Branding & Contact</h3>
            <p className="text-xs text-slate-400">These parameters populate bot greetings, dashboard titles, and customer support links dynamically.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-300 font-semibold block mb-1">Application Name (`app_name`)</label>
              <input
                type="text"
                required
                value={settingsMap['app_name'] || ''}
                onChange={(e) => setSettingsMap({ ...settingsMap, app_name: e.target.value })}
                className="w-full bg-dark-900 border border-slate-700/80 px-3.5 py-2.5 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
              />
              <span className="text-[11px] text-slate-500 mt-1 block">
                Used in Telegram/WhatsApp bot headers & user welcomes.
              </span>
            </div>

            <div>
              <label className="text-xs text-slate-300 font-semibold block mb-1">Support Phone (`support_phone`)</label>
              <input
                type="text"
                value={settingsMap['support_phone'] || ''}
                onChange={(e) => setSettingsMap({ ...settingsMap, support_phone: e.target.value })}
                className="w-full bg-dark-900 border border-slate-700/80 px-3.5 py-2.5 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
              />
            </div>
          </div>

          <div>
            <label className="text-xs text-slate-300 font-semibold block mb-1">Custom SaaS Logo URL (`app_logo_url`)</label>
            <input
              type="text"
              placeholder="https://example.com/logo.png"
              value={settingsMap['app_logo_url'] || ''}
              onChange={(e) => setSettingsMap({ ...settingsMap, app_logo_url: e.target.value })}
              className="w-full bg-dark-900 border border-slate-700/80 px-3.5 py-2.5 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
            />
          </div>

          <div className="pt-4 border-t border-slate-800 space-y-4">
            <div>
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <span className="p-1 bg-blue-500/10 rounded-lg text-blue-400">🏢</span>
                <span>Satıcı (Reseller) Paket Qiymət və Sınaq Qaydaları</span>
              </h4>
              <p className="text-xs text-slate-400 mt-0.5">
                Satıcıların öz agentləri üçün paket yaradarkən riayət etməli olduğu minimum qiymət və maksimum pulsuz sınaq günləri.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-slate-300 font-semibold block mb-1">
                  Ödənişli Paketlər üçün Minimum Qiymət (AZN) (`seller_min_package_price`)
                </label>
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={settingsMap['seller_min_package_price'] || '29'}
                  onChange={(e) => setSettingsMap({ ...settingsMap, seller_min_package_price: e.target.value })}
                  className="w-full bg-dark-900 border border-slate-700/80 px-3.5 py-2.5 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                />
                <span className="text-[11px] text-slate-500 mt-1 block">
                  Satıcılar ödənişli paket yaradarkən bu qiymətdən aşağı təyin edə bilməzlər. (Pulsuz sınağa təsir etmir)
                </span>
              </div>

              <div>
                <label className="text-xs text-slate-300 font-semibold block mb-1">
                  Maksimum Pulsuz Sınaq Müddəti (Gün) (`seller_max_trial_days`)
                </label>
                <input
                  type="number"
                  min="1"
                  max="90"
                  value={settingsMap['seller_max_trial_days'] || '14'}
                  onChange={(e) => setSettingsMap({ ...settingsMap, seller_max_trial_days: e.target.value })}
                  className="w-full bg-dark-900 border border-slate-700/80 px-3.5 py-2.5 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                />
                <span className="text-[11px] text-slate-500 mt-1 block">
                  Satıcının qurduğu 0 AZN pulsuz sınaq paketlərinin maksimum aktivlik müddəti.
                </span>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800 space-y-4">
            <div>
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <span className="p-1 bg-purple-500/10 rounded-lg text-purple-400">🚨</span>
                <span>Admin Telegram Xəbərdarlıqları və Scraper Monitorinqi</span>
              </h4>
              <p className="text-xs text-slate-400 mt-0.5">
                Scraper bloklamaları (503/403), sayt strukturu dəyişiklikləri və satıcıların pul çıxarış tələbləri anında bu Telegram çatına göndərilir.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-slate-300 font-semibold block mb-1">
                  Admin Telegram Chat ID (`admin_telegram_chat_id`)
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="məs: 123456789"
                    value={settingsMap['admin_telegram_chat_id'] || ''}
                    onChange={(e) => setSettingsMap({ ...settingsMap, admin_telegram_chat_id: e.target.value })}
                    className="flex-1 bg-dark-900 border border-slate-700/80 px-3.5 py-2.5 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                  />
                  <button
                    type="button"
                    disabled={testingAlert || !settingsMap['admin_telegram_chat_id']}
                    onClick={async () => {
                      setTestingAlert(true);
                      setAlertStatusMsg(null);
                      try {
                        const res = await api.post('/settings/test-admin-alert');
                        setAlertStatusMsg({ success: true, text: res.data?.message || 'Sınaq bildirişi uğurla çatdırıldı!' });
                      } catch (err: any) {
                        setAlertStatusMsg({ success: false, text: err.response?.data?.detail || 'Xəta baş verdi.' });
                      } finally {
                        setTestingAlert(false);
                      }
                    }}
                    className="px-4 py-2.5 bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/40 text-purple-300 hover:text-white rounded-xl text-xs font-semibold transition-all disabled:opacity-40"
                  >
                    {testingAlert ? 'Göndərilir...' : 'Sınaq Göndər'}
                  </button>
                </div>
                {alertStatusMsg && (
                  <div className={`mt-2 text-xs p-2.5 rounded-lg border ${alertStatusMsg.success ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-rose-500/10 border-rose-500/30 text-rose-300'}`}>
                    {alertStatusMsg.text}
                  </div>
                )}
              </div>

              <div className="bg-dark-900/60 p-3.5 rounded-xl border border-slate-800 space-y-1.5 text-xs text-slate-300">
                <div className="font-semibold text-purple-300 flex items-center gap-1.5">
                  <span>ℹ️</span> <span>Telegram ID-ni necə tapmaq olar?</span>
                </div>
                <ol className="list-decimal list-inside text-[11px] text-slate-400 space-y-1">
                  <li>Telegram-da <a href="https://t.me/userinfobot" target="_blank" rel="noreferrer" className="text-purple-400 underline font-mono">@userinfobot</a> botuna <code className="text-purple-300">/start</code> yazın və ID rəqəmlərinizi kopyalayın.</li>
                  <li>Sistemin əsas botuna (məs: botunuza) daxil olub ən az 1 dəfə <code className="text-purple-300">/start</code> vurun.</li>
                  <li>Kopyaladığınız rəqəmləri yuxarıdakı xanaya yazıb yadda saxlayın və <strong>"Sınaq Göndər"</strong> düyməsinə klikləyin.</li>
                </ol>
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
            {brandingSaved && (
              <span className="text-xs text-emerald-400 font-medium flex items-center gap-1">
                <CheckCircle className="w-4 h-4" /> Settings updated cleanly in database!
              </span>
            )}
            <button
              type="submit"
              disabled={savingBranding}
              className="ml-auto flex items-center gap-2 bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-400 hover:to-indigo-500 text-white text-sm font-semibold px-5 py-2.5 rounded-xl transition-all shadow-lg shadow-purple-500/20 disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              <span>{savingBranding ? 'Saving...' : 'Save Branding Settings'}</span>
            </button>
          </div>
        </form>
      )}

      {/* SUB-TAB 2: AI Provider Abstraction Config */}
      {activeSubTab === 'ai' && (
        <div className="space-y-6">
          {/* Task Config Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {taskTypes.map((task) => (
              <AppSettingsAITaskCard
                key={task.key}
                task={task}
                cfg={getConfigForTask(task.key)}
                onSave={handleSaveAiConfig}
                onTest={handleTestConnection}
              />
            ))}
          </div>

          {/* Connection Test Output Result */}
          {testResult && (
            <div className={`p-4 rounded-xl border text-xs ${testResult.success ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-rose-500/10 border-rose-500/30 text-rose-300'}`}>
              <div className="font-bold flex items-center gap-2">
                {testResult.success ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                Connection Test Result for {testResult.provider} ({testResult.model_name}) — Latency: {testResult.latency_ms}ms
              </div>
              {testResult.success ? (
                <div className="mt-1 text-slate-300">Parsed Test Output: "{testResult.test_output}"</div>
              ) : (
                <div className="mt-1 font-mono text-rose-400">{testResult.error}</div>
              )}
            </div>
          )}

          {/* AI Call Logs Table */}
          <div className="bg-dark-800/90 rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
            <div className="p-4 bg-dark-800 border-b border-slate-800 flex items-center gap-2 text-sm font-semibold text-white">
              <History className="w-4 h-4 text-purple-400" />
              Recent AI Provider Call Logs
            </div>
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-dark-900/60 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="p-3">Time</th>
                  <th className="p-3">Provider</th>
                  <th className="p-3">Task Type</th>
                  <th className="p-3">Model</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {callLogs.map((log) => (
                  <tr key={log.id}>
                    <td className="p-3 text-slate-400">{new Date(log.created_at).toLocaleTimeString()}</td>
                    <td className="p-3 capitalize font-sans">{log.provider}</td>
                    <td className="p-3 font-sans text-slate-400">{log.task_type}</td>
                    <td className="p-3">{log.model_name}</td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-sans font-semibold ${
                        log.status === 'success' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
                      }`}>
                        {log.status}
                      </span>
                    </td>
                    <td className="p-3">{log.latency_ms} ms</td>
                  </tr>
                ))}
                {callLogs.length === 0 && (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-slate-500 font-sans">
                      No AI call logs recorded yet. Call logs populate automatically during criteria parsing and match scoring.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SUB-TAB 3: Scraper & Automation Defaults */}
      {activeSubTab === 'automation' && (
        <form onSubmit={handleSaveBranding} className="bg-dark-800/90 p-6 rounded-2xl border border-slate-800 space-y-5 shadow-xl">
          <div>
            <h3 className="text-base font-bold text-white mb-1">Scraper Engine & AI Automation Defaults</h3>
            <p className="text-xs text-slate-400">Configure global AI Makler detection threshold scores and default co-brokering commission splits.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-300 font-semibold block mb-1">Makler Detection Score Threshold (`makler_threshold`)</label>
              <input
                type="number"
                step="0.05"
                min="0"
                max="1"
                value={settingsMap['makler_threshold'] || '0.7'}
                onChange={(e) => setSettingsMap({ ...settingsMap, makler_threshold: e.target.value })}
                className="w-full bg-dark-900 border border-slate-700/80 px-3.5 py-2.5 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
              />
              <span className="text-[11px] text-slate-500 mt-1 block">
                Listings with a Makler score above this threshold (0.0 to 1.0) are flagged as masked agencies.
              </span>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
            {brandingSaved && (
              <span className="text-xs text-emerald-400 font-medium flex items-center gap-1">
                <CheckCircle className="w-4 h-4" /> Automation parameters updated cleanly!
              </span>
            )}
            <button
              type="submit"
              disabled={savingBranding}
              className="ml-auto flex items-center gap-2 bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-400 hover:to-indigo-500 text-white text-sm font-semibold px-5 py-2.5 rounded-xl transition-all shadow-lg shadow-purple-500/20 disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              <span>{savingBranding ? 'Saving...' : 'Save Automation Defaults'}</span>
            </button>
          </div>
        </form>
      )}

      {/* SUB-TAB 4: Team Administrators Management */}
      {activeSubTab === 'admins' && (
        <div className="space-y-4">
          <div className="bg-dark-800/90 p-6 rounded-2xl border border-slate-800 shadow-xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-purple-400" />
                  All Platform Administrators ({admins.length})
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Manage accounts with full superadmin privileges to configure system rules, agents, plans, and AI integrations.
                </p>
              </div>

              <button
                type="button"
                onClick={() => {
                  setAdminError('');
                  setShowAddAdminModal(true);
                }}
                className="flex items-center gap-2 bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-400 hover:to-indigo-500 text-white text-xs font-semibold px-4 py-2.5 rounded-xl transition-all shadow-lg shadow-purple-500/20"
              >
                <Plus className="w-4 h-4" />
                <span>Add Administrator</span>
              </button>
            </div>

            {loadingAdmins ? (
              <div className="py-12 text-center text-xs text-slate-500">Loading administrators...</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {admins.map((adm) => (
                  <div
                    key={adm.id}
                    className="p-4 rounded-xl bg-dark-900 border border-slate-800 hover:border-slate-700/80 transition-all flex items-start justify-between gap-3 shadow-md"
                  >
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-purple-500/20 border border-purple-500/30 flex items-center justify-center text-purple-300 font-bold text-xs">
                          {adm.name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div className="text-xs font-bold text-white flex items-center gap-1.5">
                            {adm.name}
                            {myProfile?.id === adm.id ? (
                              <span className="text-[10px] px-2 py-0.2 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-mono font-semibold">
                                You
                              </span>
                            ) : (
                              <span className="text-[10px] px-2 py-0.2 rounded-full bg-purple-500/10 text-purple-400 font-mono font-semibold">
                                Superadmin
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-slate-400 flex items-center gap-1 mt-0.5">
                            <Mail className="w-3 h-3 text-slate-500" /> {adm.email}
                          </div>
                        </div>
                      </div>

                      {adm.phone && (
                        <div className="text-[11px] text-slate-400 flex items-center gap-1 pl-10">
                          <Phone className="w-3 h-3 text-slate-500" /> {adm.phone}
                        </div>
                      )}

                      {adm.created_at && (
                        <div className="text-[10px] text-slate-500 pl-10">
                          Created: {new Date(adm.created_at).toLocaleDateString()}
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => handleOpenEditAdmin(adm)}
                        className="text-slate-400 hover:text-purple-300 p-1.5 rounded-lg hover:bg-purple-500/10 transition-all"
                        title="Edit Administrator"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>

                      {myProfile?.id !== adm.id && (
                        <button
                          type="button"
                          onClick={() => handleDeleteAdmin(adm.id, adm.name)}
                          className="text-slate-500 hover:text-red-400 p-1.5 rounded-lg hover:bg-red-500/10 transition-all"
                          title="Remove Administrator"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}

                {admins.length === 0 && (
                  <div className="col-span-full py-8 text-center text-xs text-slate-500">
                    No administrators found.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Edit Administrator Modal */}
      {editingAdmin && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card w-full max-w-md p-6 rounded-2xl border border-slate-800 space-y-4 shadow-2xl">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Edit2 className="w-5 h-5 text-purple-400" />
                Edit Administrator: {editingAdmin.name}
              </h3>
              <button
                type="button"
                onClick={() => setEditingAdmin(null)}
                className="text-slate-400 hover:text-white"
              >
                &times;
              </button>
            </div>

            {editAdminError && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{editAdminError}</span>
              </div>
            )}

            <form onSubmit={handleSaveEditAdmin} className="space-y-3 text-xs">
              <div>
                <label className="text-slate-300 font-semibold block mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  value={editAdminName}
                  onChange={(e) => setEditAdminName(e.target.value)}
                  className="w-full bg-dark-900 border border-slate-700/80 px-3 py-2 rounded-xl text-white focus:outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="text-slate-300 font-semibold block mb-1">Email Address</label>
                <div className="relative">
                  <Mail className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
                  <input
                    type="email"
                    required
                    value={editAdminEmail}
                    onChange={(e) => setEditAdminEmail(e.target.value)}
                    className="w-full bg-dark-900 border border-slate-700/80 pl-9 pr-3 py-2 rounded-xl text-white focus:outline-none focus:border-purple-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-300 font-semibold block mb-1">Phone Number (Optional)</label>
                <div className="relative">
                  <Phone className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
                  <input
                    type="text"
                    placeholder="+994501234567"
                    value={editAdminPhone}
                    onChange={(e) => setEditAdminPhone(e.target.value)}
                    className="w-full bg-dark-900 border border-slate-700/80 pl-9 pr-3 py-2 rounded-xl text-white focus:outline-none focus:border-purple-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-300 font-semibold block mb-1">Reset Password (Leave blank to keep unchanged)</label>
                <div className="relative">
                  <Lock className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
                  <input
                    type="password"
                    placeholder="Enter new password (optional)"
                    value={editAdminPassword}
                    onChange={(e) => setEditAdminPassword(e.target.value)}
                    className="w-full bg-dark-900 border border-slate-700/80 pl-9 pr-3 py-2 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setEditingAdmin(null)}
                  className="px-4 py-2 text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingEditAdmin}
                  className="px-5 py-2 font-semibold bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-400 hover:to-indigo-500 text-white rounded-xl flex items-center gap-1.5 shadow-lg shadow-purple-500/20 disabled:opacity-50"
                >
                  <span>{savingEditAdmin ? 'Saving...' : 'Save Changes'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Administrator Modal */}
      {showAddAdminModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card w-full max-w-md p-6 rounded-2xl border border-slate-800 space-y-4 shadow-2xl">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-purple-400" />
                Add New Administrator
              </h3>
              <button
                type="button"
                onClick={() => setShowAddAdminModal(false)}
                className="text-slate-400 hover:text-white"
              >
                &times;
              </button>
            </div>

            {adminError && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{adminError}</span>
              </div>
            )}

            <form onSubmit={handleCreateAdmin} className="space-y-3 text-xs">
              <div>
                <label className="text-slate-300 font-semibold block mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Samir Mammadov"
                  value={newAdminName}
                  onChange={(e) => setNewAdminName(e.target.value)}
                  className="w-full bg-dark-900 border border-slate-700/80 px-3 py-2 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="text-slate-300 font-semibold block mb-1">Email Address</label>
                <div className="relative">
                  <Mail className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
                  <input
                    type="email"
                    required
                    placeholder="admin@estate.az"
                    value={newAdminEmail}
                    onChange={(e) => setNewAdminEmail(e.target.value)}
                    className="w-full bg-dark-900 border border-slate-700/80 pl-9 pr-3 py-2 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-300 font-semibold block mb-1">Password</label>
                <div className="relative">
                  <Lock className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
                  <input
                    type="password"
                    required
                    minLength={6}
                    placeholder="Minimum 6 characters"
                    value={newAdminPassword}
                    onChange={(e) => setNewAdminPassword(e.target.value)}
                    className="w-full bg-dark-900 border border-slate-700/80 pl-9 pr-3 py-2 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-300 font-semibold block mb-1">Phone Number (Optional)</label>
                <div className="relative">
                  <Phone className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
                  <input
                    type="text"
                    placeholder="+994501234567"
                    value={newAdminPhone}
                    onChange={(e) => setNewAdminPhone(e.target.value)}
                    className="w-full bg-dark-900 border border-slate-700/80 pl-9 pr-3 py-2 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAddAdminModal(false)}
                  className="px-4 py-2 text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addingAdmin}
                  className="px-5 py-2 font-semibold bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-400 hover:to-indigo-500 text-white rounded-xl flex items-center gap-1.5 shadow-lg shadow-purple-500/20 disabled:opacity-50"
                >
                  <span>{addingAdmin ? 'Creating...' : 'Create Administrator'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
