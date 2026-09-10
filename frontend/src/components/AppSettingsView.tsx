import React, { useEffect, useState } from 'react';
import { Sliders, Save, CheckCircle, Cpu, Key, CheckCircle2, AlertTriangle, Play, History, Building2, SlidersHorizontal, Database, Users, Plus, Trash2, ShieldCheck, Mail, Phone, Lock, Edit2, UserCheck, KeyRound, Globe, RefreshCw, Zap, Clock, Radio, Power, Send, Bell } from 'lucide-react';
import api from '../api';
import { AIProviderConfigItem, AICallLogItem, AdminUser } from '../types';

interface TaskType {
  key: string;
  label: string;
  defaultProvider: string;
  defaultModel: string;
}

const modelOptions: Record<string, string[]> = {
  gemini: ['gemini-3.8-flash', 'gemini-3.7-flash', 'gemini-3.6-flash', 'gemini-3.5-flash', 'gemini-3.7-pro', 'gemini-3.5-pro'],
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
  const [selectedModel, setSelectedModel] = useState<string>(cfg.model_name || 'gemini-3.8-flash');
  const [apiKeyInput, setApiKeyInput] = useState('');

  useEffect(() => {
    setSelectedProvider(cfg.provider || 'gemini');
    setSelectedModel(cfg.model_name || 'gemini-3.8-flash');
  }, [cfg]);

  return (
    <div className="bg-dark-800/90 p-5 rounded-2xl border border-slate-800 space-y-4 flex flex-col justify-between shadow-xl">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold text-white">{task.label}</h3>
          <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 font-medium capitalize">
            {cfg.provider || 'gemini'}
          </span>
        </div>

        <div>
          <label className="text-xs text-slate-400 block mb-1">Active Provider</label>
          <select
            value={selectedProvider}
            onChange={(e) => {
              const p = e.target.value;
              setSelectedProvider(p);
              setSelectedModel(modelOptions[p] ? modelOptions[p][0] : 'gemini-3.8-flash');
            }}
            className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-900 border border-slate-700"
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
          onClick={() => onSave(task.key, selectedProvider, selectedModel, apiKeyInput || undefined)}
          className="text-xs font-semibold bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/40 px-3.5 py-1.5 rounded-xl flex items-center gap-1 transition-all"
        >
          <Save className="w-3 h-3" /> Save Config
        </button>
      </div>
    </div>
  );
};

export const AppSettingsView: React.FC = () => {
  const [activeSubTab, setActiveSubTab] = useState<'branding' | 'ai' | 'automation' | 'proxy' | 'admins' | 'maintenance'>('branding');
  const [settingsMap, setSettingsMap] = useState<Record<string, string>>({});
  const [savingBranding, setSavingBranding] = useState(false);
  const [brandingSaved, setBrandingSaved] = useState(false);

  // Maintenance Mode State
  const [maintenanceStatus, setMaintenanceStatus] = useState<{
    is_maintenance: boolean;
    reason: string;
    started_at: string;
    estimated_minutes: number;
    connected_agents_count: number;
    preview_start_message: string;
    preview_end_message: string;
  } | null>(null);
  const [loadingMaintenance, setLoadingMaintenance] = useState(false);
  const [maintenanceReason, setMaintenanceReason] = useState('Planlı server profilaktikası və verilənlər bazası yenilənməsi.');
  const [maintenanceMinutes, setMaintenanceMinutes] = useState(30);
  const [maintenanceNotify, setMaintenanceNotify] = useState(true);
  const [customStartMsg, setCustomStartMsg] = useState('');
  const [customEndMsg, setCustomEndMsg] = useState('');
  const [maintenanceActionLoading, setMaintenanceActionLoading] = useState(false);
  const [maintenanceAlert, setMaintenanceAlert] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Proxy & Anti-Bot State
  const [proxyTestRunning, setProxyTestRunning] = useState(false);
  const [proxyTestResult, setProxyTestResult] = useState<{
    success: boolean;
    proxy_used?: string;
    detected_ip?: string;
    ip_status?: number;
    bina_status?: number;
    bina_title?: string;
    tap_status?: number;
    tap_title?: string;
    latency_ms?: number;
    message?: string;
    error?: string;
  } | null>(null);
  const [customTestProxyInput, setCustomTestProxyInput] = useState('');

  const handleRunProxyTest = async (overrideProxy?: string) => {
    setProxyTestRunning(true);
    setProxyTestResult(null);
    try {
      const payload: { proxy_url?: string } = {};
      const proxyToUse = overrideProxy !== undefined ? overrideProxy : customTestProxyInput.trim();
      if (proxyToUse) {
        payload.proxy_url = proxyToUse;
      }
      const res = await api.post('/settings/test-proxy', payload);
      setProxyTestResult(res.data);
    } catch (e: any) {
      setProxyTestResult({
        success: false,
        message: e.response?.data?.detail || e.message || 'Proksi sorğusu zamanı şəbəkə xətası baş verdi.',
        bina_status: 0,
        latency_ms: 0
      });
    } finally {
      setProxyTestRunning(false);
    }
  };

  // Full Pool Scan State
  const [poolScanRunning, setPoolScanRunning] = useState(false);
  const [poolScanResult, setPoolScanResult] = useState<{
    total: number;
    healthy_count: number;
    blocked_count: number;
    healthy_percent: number;
    healthy_proxies: string[];
    blocked_proxies: string[];
    results: Array<{
      proxy: string;
      detected_ip?: string;
      status?: number;
      bina_status?: number;
      tap_status?: number;
      latency_ms?: number;
      success: boolean;
      error?: string;
      message?: string;
    }>;
  } | null>(null);

  const handleScanPool = async () => {
    setPoolScanRunning(true);
    setPoolScanResult(null);
    try {
      const currentList = (settingsMap['proxy_pool_urls'] || '')
        .split('\n')
        .map(p => p.trim())
        .filter(Boolean);

      const res = await api.post('/settings/scan-proxy-pool', {
        proxies: currentList.length > 0 ? currentList : undefined
      });
      setPoolScanResult(res.data);
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Hovuz skan edilərkən xəta baş verdi.');
    } finally {
      setPoolScanRunning(false);
    }
  };

  const handleRemoveBlockedProxies = () => {
    if (!poolScanResult || !poolScanResult.healthy_proxies) return;
    const cleanText = poolScanResult.healthy_proxies.join('\n');
    setSettingsMap(prev => ({ ...prev, proxy_pool_urls: cleanText }));
    alert(`Bloklanmış ${poolScanResult.blocked_count} proksi siyahıdan təmizləndi! Yadda saxlamaq üçün "Yadda Saxla və Tətbiq Et" düyməsini sıxın.`);
  };

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
    { key: 'criteria_parsing', label: 'Criteria Parsing (Conversational Agent)', defaultProvider: 'gemini', defaultModel: 'gemini-3.8-flash' },
    { key: 'listing_parsing', label: 'Telegram Unformatted Listing Parser', defaultProvider: 'gemini', defaultModel: 'gemini-3.8-flash' },
    { key: 'match_scoring', label: 'Match Scoring Engine', defaultProvider: 'gemini', defaultModel: 'gemini-3.8-flash' },
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

  const loadMaintenanceStatus = async () => {
    try {
      setLoadingMaintenance(true);
      const res = await api.get('/settings/maintenance');
      if (res.data) {
        setMaintenanceStatus(res.data);
        if (res.data.reason) setMaintenanceReason(res.data.reason);
        if (res.data.estimated_minutes) setMaintenanceMinutes(res.data.estimated_minutes);
      }
    } catch (e) {
      console.error('Failed to load maintenance status', e);
    } finally {
      setLoadingMaintenance(false);
    }
  };

  const handleEnableMaintenance = async () => {
    const agentsCount = maintenanceStatus?.connected_agents_count || 0;
    if (!window.confirm(`Diqqət! Texniki baxış rejimini aktivləşdirmək istədiyinizdən əminsiniz?\n${maintenanceNotify ? `Bütün (${agentsCount}) qoşulmuş agentə xəbərdarlıq bildirişi göndəriləcək.` : 'Agentlərə bildiriş göndərilməyəcək.'}`)) {
      return;
    }
    setMaintenanceActionLoading(true);
    setMaintenanceAlert(null);
    try {
      const res = await api.post('/settings/maintenance/enable', {
        reason: maintenanceReason,
        estimated_minutes: Number(maintenanceMinutes),
        custom_message: customStartMsg || undefined,
        notify_agents: maintenanceNotify
      });
      setMaintenanceAlert({
        type: 'success',
        message: `Texniki baxış rejimi aktivləşdirildi! ${res.data.notified_count || 0} agentə bildiriş çatdırıldı.`
      });
      await loadMaintenanceStatus();
      await loadSettings();
    } catch (err: any) {
      setMaintenanceAlert({
        type: 'error',
        message: err.response?.data?.detail || 'Texniki baxışı aktivləşdirmək mümkün olmadı.'
      });
    } finally {
      setMaintenanceActionLoading(false);
    }
  };

  const handleDisableMaintenance = async () => {
    const agentsCount = maintenanceStatus?.connected_agents_count || 0;
    if (!window.confirm(`Texniki baxış rejimini dayandırmaq və sistemi bərpa etmək istəyirsiniz?\n${maintenanceNotify ? `Bütün (${agentsCount}) agentə sistemin bərpa olunduğu bildirişi göndəriləcək.` : 'Agentlərə bildiriş göndərilməyəcək.'}`)) {
      return;
    }
    setMaintenanceActionLoading(true);
    setMaintenanceAlert(null);
    try {
      const res = await api.post('/settings/maintenance/disable', {
        custom_message: customEndMsg || undefined,
        notify_agents: maintenanceNotify
      });
      setMaintenanceAlert({
        type: 'success',
        message: `Texniki baxış rejimi söndürüldü, sistem bərpa olundu! ${res.data.notified_count || 0} agentə bərpa bildirişi çatdırıldı.`
      });
      await loadMaintenanceStatus();
      await loadSettings();
    } catch (err: any) {
      setMaintenanceAlert({
        type: 'error',
        message: err.response?.data?.detail || 'Texniki baxışı söndürmək mümkün olmadı.'
      });
    } finally {
      setMaintenanceActionLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
    loadAiConfigs();
    loadAdmins();
    loadMyProfile();
    loadMaintenanceStatus();
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
      model_name: 'gemini-3.8-flash',
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

          <button
            onClick={() => setActiveSubTab('proxy')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeSubTab === 'proxy'
                ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Globe className="w-3.5 h-3.5" />
            <span>Proksi & Anti-Bot</span>
          </button>

          <button
            onClick={() => setActiveSubTab('maintenance')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeSubTab === 'maintenance'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30 shadow-lg shadow-amber-500/10'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            <span>Texniki Baxış</span>
            {maintenanceStatus?.is_maintenance && (
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
              </span>
            )}
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

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-300 font-semibold block mb-1">
                🤖 Telegram Bot İstifadəçi Adı (`telegram_bot_username`)
              </label>
              <input
                type="text"
                placeholder="məs: baku_realestate_ai_bot"
                value={settingsMap['telegram_bot_username'] || ''}
                onChange={(e) => setSettingsMap({ ...settingsMap, telegram_bot_username: e.target.value.replace('@', '').trim() })}
                className="w-full bg-dark-900 border border-slate-700/80 px-3.5 py-2.5 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
              />
              <span className="text-[11px] text-slate-500 mt-1 block">
                @ işarəsi olmadan yazın. Agentlərə QR kod və Telegram dəvət linkləri üçün istifadə olunur.
              </span>
            </div>

            <div>
              <label className="text-xs text-slate-300 font-semibold block mb-1">
                💬 WhatsApp Bot Nömrəsi (`whatsapp_bot_phone`)
              </label>
              <input
                type="text"
                placeholder="məs: +994501234567"
                value={settingsMap['whatsapp_bot_phone'] || ''}
                onChange={(e) => setSettingsMap({ ...settingsMap, whatsapp_bot_phone: e.target.value })}
                className="w-full bg-dark-900 border border-slate-700/80 px-3.5 py-2.5 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
              <span className="text-[11px] text-slate-500 mt-1 block">
                Agentlərə WhatsApp birbaşa əlaqə və QR linkləri üçün istifadə olunur.
              </span>
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

            <div className="mt-4 space-y-3">
              <h5 className="text-xs font-bold text-amber-400 flex items-center gap-1.5">
                <span>📦</span> Standart Arxiv Elanlar Pilləli Qiymətləri (JSON)
              </h5>
              <p className="text-[10px] text-slate-500">
                Yeni satıcılar yaratdıqda paketin default arxiv elanlar tier qiymətləri. Format: {`[{"months": 3, "price": 15}, ...]`}
              </p>
              <textarea
                rows={3}
                value={settingsMap['addon_default_aged_tiers'] || '[{"months": 3, "price": 15.0}, {"months": 6, "price": 25.0}, {"months": 12, "price": 40.0}, {"months": 24, "price": 60.0}]'}
                onChange={(e) => setSettingsMap({ ...settingsMap, addon_default_aged_tiers: e.target.value })}
                className="w-full bg-dark-900 border border-slate-700/80 px-3.5 py-2.5 rounded-xl text-xs text-white font-mono placeholder-slate-500 focus:outline-none focus:border-amber-500"
              />
            </div>

            <div className="mt-3 space-y-3">
              <h5 className="text-xs font-bold text-cyan-400 flex items-center gap-1.5">
                <span>⚡</span> Standart Əlavə Axtarış Pilləli Qiymətləri (JSON)
              </h5>
              <p className="text-[10px] text-slate-500">
                Yeni satıcılar yaratdıqda paketin default əlavə axtarış tier qiymətləri. Format: {`[{"searches": 5, "price": 10}, ...]`}
              </p>
              <textarea
                rows={3}
                value={settingsMap['addon_default_search_tiers'] || '[{"searches": 5, "price": 10.0}, {"searches": 10, "price": 18.0}, {"searches": 20, "price": 30.0}, {"searches": 50, "price": 60.0}]'}
                onChange={(e) => setSettingsMap({ ...settingsMap, addon_default_search_tiers: e.target.value })}
                className="w-full bg-dark-900 border border-slate-700/80 px-3.5 py-2.5 rounded-xl text-xs text-white font-mono placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              />
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

      {/* SUB-TAB: Proksi & Anti-Bot İdarəetməsi */}
      {activeSubTab === 'proxy' && (
        <div className="space-y-6">
          {/* Header & Status Card */}
          <div className="bg-dark-800/90 p-6 rounded-2xl border border-slate-800 shadow-xl space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Globe className="w-5 h-5 text-indigo-400" />
                  Proksi & Anti-Bot Şəbəkə Mərkəzi
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Bina.az və digər daşınmaz əmlak portallarının IP bloklamalarından (Cloudflare Error 1006) yayınmaq üçün Webshare və ya istənilən fərdi proksi hovuzunu idarə edin.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-3 py-1 rounded-full text-xs font-semibold border flex items-center gap-1.5 ${
                  (settingsMap['proxy_enabled'] ?? 'true') === 'true'
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                    : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                }`}>
                  <span className={`w-2 h-2 rounded-full ${
                    (settingsMap['proxy_enabled'] ?? 'true') === 'true' ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'
                  }`} />
                  {(settingsMap['proxy_enabled'] ?? 'true') === 'true' ? 'Proksi Aktivdir' : 'Proksi Deaktivdir (Birbaşa IP)'}
                </span>
              </div>
            </div>

            {/* Quick Controls Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
              <label className="flex items-start gap-3 p-3.5 rounded-xl bg-dark-900/80 border border-slate-700/60 cursor-pointer hover:border-slate-600 transition-all">
                <input
                  type="checkbox"
                  checked={(settingsMap['proxy_enabled'] ?? 'true') === 'true'}
                  onChange={(e) => setSettingsMap({ ...settingsMap, proxy_enabled: e.target.checked ? 'true' : 'false' })}
                  className="mt-0.5 rounded text-purple-600 focus:ring-purple-500 bg-dark-800 border-slate-700"
                />
                <div>
                  <span className="text-xs font-semibold text-white block">Proksi Şəbəkəsinə İcazə Ver</span>
                  <span className="text-[11px] text-slate-400 block mt-0.5">
                    Deaktiv edildikdə sorğular serverin öz birbaşa IP-si ilə çıxacaq.
                  </span>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3.5 rounded-xl bg-dark-900/80 border border-slate-700/60 cursor-pointer hover:border-slate-600 transition-all">
                <input
                  type="checkbox"
                  checked={(settingsMap['proxy_rotation_enabled'] ?? 'true') === 'true'}
                  onChange={(e) => setSettingsMap({ ...settingsMap, proxy_rotation_enabled: e.target.checked ? 'true' : 'false' })}
                  className="mt-0.5 rounded text-purple-600 focus:ring-purple-500 bg-dark-800 border-slate-700"
                />
                <div>
                  <span className="text-xs font-semibold text-white block">Dinamik Hovuz Rotasiyası</span>
                  <span className="text-[11px] text-slate-400 block mt-0.5">
                    Hər yeni elan yoxlama sorğusunda aşağıdakı hovuzdan təsadüfi proksi seçilir.
                  </span>
                </div>
              </label>
            </div>
          </div>

          {/* Primary Proxy & Pool Configuration */}
          <form onSubmit={handleSaveBranding} className="bg-dark-800/90 p-6 rounded-2xl border border-slate-800 shadow-xl space-y-5">
            <div>
              <h4 className="text-sm font-bold text-white mb-1">Əsas Proksi (Primary / Fallback URL)</h4>
              <p className="text-xs text-slate-400 mb-2">
                Əgər tək bir statik proksi və ya şəxsi tunel (məs. BrightData, Oxylabs, Webshare Backbone) istifadə edirsinizsə, bura daxil edin. Boş saxlanarsa birbaşa aşağıdakı çoxlu hovuz işə düşür.
              </p>
              <input
                type="text"
                placeholder="http://username:password@ip:port və ya ip:port:username:password"
                value={settingsMap['bina_az_proxy_url'] || ''}
                onChange={(e) => setSettingsMap({ ...settingsMap, bina_az_proxy_url: e.target.value })}
                className="w-full bg-dark-900 border border-slate-700/80 px-3.5 py-2.5 rounded-xl text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
              />
            </div>

            <div>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                <div>
                  <h4 className="text-sm font-bold text-white">Çoxlu Proksi Hovuzu (Proxy Pool List)</h4>
                  <p className="text-xs text-slate-400">
                    Hər sətirdə bir proksi. Webshare standart formatı (<code className="text-purple-300">IP:PORT:USER:PASS</code>) və ya URL formatı (<code className="text-purple-300">http://user:pass@ip:port</code>) dəstəklənir.
                  </p>
                </div>
                <div className="flex items-center gap-2 self-start sm:self-auto flex-wrap">
                  <span className="text-xs px-2.5 py-1 rounded-lg bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-mono">
                    {(settingsMap['proxy_pool_urls'] || '').split('\n').filter(p => p.trim()).length} Proksi Qeydiyyatda
                  </span>
                  <button
                    type="button"
                    onClick={handleScanPool}
                    disabled={poolScanRunning}
                    className="flex items-center gap-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/40 text-xs font-semibold px-3 py-1 rounded-lg transition-all disabled:opacity-50"
                  >
                    {poolScanRunning ? <RefreshCw className="w-3 h-3 animate-spin" /> : <ShieldCheck className="w-3 h-3" />}
                    <span>{poolScanRunning ? 'Skan edilir...' : '🩺 Bütün Hovuzu Diaqnostika Et'}</span>
                  </button>
                </div>
              </div>

              {/* Pool Scan Summary Banner */}
              {poolScanResult && (
                <div className="mb-3 p-3 rounded-xl bg-dark-900/90 border border-slate-700 space-y-2">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                        poolScanResult.healthy_percent >= 80 ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'
                      }`}>
                        Sağlamlıq: {poolScanResult.healthy_percent}%
                      </span>
                      <span className="text-xs text-slate-300">
                        🟢 {poolScanResult.healthy_count} aktiv işlək / 🔴 {poolScanResult.blocked_count} bloklanmış
                      </span>
                    </div>

                    {poolScanResult.blocked_count > 0 && (
                      <button
                        type="button"
                        onClick={handleRemoveBlockedProxies}
                        className="flex items-center gap-1 text-xs font-semibold text-rose-400 hover:text-rose-300 bg-rose-500/10 border border-rose-500/20 px-2.5 py-1 rounded-lg transition-all"
                      >
                        <Trash2 className="w-3 h-3" />
                        <span>Bloklanmış {poolScanResult.blocked_count} Proksini Siyahıdan Təmizlə</span>
                      </button>
                    )}
                  </div>

                  {/* Micro list of scanned proxies */}
                  <div className="max-h-36 overflow-y-auto space-y-1 pt-1 pr-1">
                    {poolScanResult.results.map((r, idx) => (
                      <div key={idx} className="flex items-center justify-between text-[11px] font-mono p-1.5 rounded-lg bg-dark-800/80 border border-slate-800">
                        <div className="flex items-center gap-2 truncate">
                          <span>{r.success ? '🟢' : '🔴'}</span>
                          <span className="text-slate-300 truncate">{r.proxy}</span>
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0">
                          <span className={`px-1.5 py-0.5 rounded text-[10px] ${r.bina_status === 200 ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300 font-semibold'}`}>
                            Bina: {r.bina_status ? `${r.bina_status}` : 'Xəta'}
                          </span>
                          <span className={`px-1.5 py-0.5 rounded text-[10px] ${r.tap_status === 200 ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300 font-semibold'}`}>
                            Tap: {r.tap_status ? `${r.tap_status}` : 'Xəta'}
                          </span>
                          <span className="text-slate-500">{r.latency_ms}ms</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <textarea
                rows={8}
                value={settingsMap['proxy_pool_urls'] || ''}
                onChange={(e) => setSettingsMap({ ...settingsMap, proxy_pool_urls: e.target.value })}
                placeholder="31.59.20.176:6754:reipvtkd:kwop2c4stm5r&#10;45.38.107.97:6014:reipvtkd:kwop2c4stm5r"
                className="w-full bg-dark-900 border border-slate-700/80 p-3.5 rounded-xl text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-purple-500 leading-relaxed"
              />
            </div>

            <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
              {brandingSaved && (
                <span className="text-xs text-emerald-400 font-medium flex items-center gap-1">
                  <CheckCircle className="w-4 h-4" /> Proksi tənzimləmələri yadda saxlanıldı və scraper hovuzunda dərhal tətbiq edildi!
                </span>
              )}
              <button
                type="submit"
                disabled={savingBranding}
                className="ml-auto flex items-center gap-2 bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-400 hover:to-indigo-500 text-white text-sm font-semibold px-5 py-2.5 rounded-xl transition-all shadow-lg shadow-purple-500/20 disabled:opacity-50"
              >
                <Save className="w-4 h-4" />
                <span>{savingBranding ? 'Yadda Saxlanılır...' : 'Yadda Saxla və Tətbiq Et'}</span>
              </button>
            </div>
          </form>

          {/* 1-Click Live Proxy Diagnostics */}
          <div className="bg-dark-800/90 p-6 rounded-2xl border border-slate-800 shadow-xl space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
              <div>
                <h4 className="text-sm font-bold text-white flex items-center gap-2">
                  <Play className="w-4 h-4 text-purple-400" />
                  Canlı Proksi, Bina.az & Tap.az Sınağı
                </h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  Proksinin Cloudflare WAF blokunu keçib-keçmədiyini, həm Bina.az, həm də Tap.az saytlarına daxil ola bildiyini real vaxtda yoxlayın.
                </p>
              </div>

              <button
                type="button"
                onClick={() => handleRunProxyTest('')}
                disabled={proxyTestRunning}
                className="self-start sm:self-auto flex items-center gap-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-semibold px-4 py-2.5 rounded-xl transition-all disabled:opacity-50 shadow-lg shadow-emerald-500/20"
              >
                {proxyTestRunning ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
                <span>{proxyTestRunning ? 'Yoxlanılır...' : '⚡ Aktiv Hovuzu Yoxla'}</span>
              </button>
            </div>

            {/* Custom Single Proxy Test Input */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
                <span>Fərdi Proksini Sınaqdan Keçir (Opsional)</span>
                <span className="text-[11px] text-slate-500 font-mono">Format: 31.59.20.176:6754:reipvtkd:kwop2c4stm5r</span>
              </label>
              <div className="flex flex-col sm:flex-row gap-2">
                <input
                  type="text"
                  placeholder="Proksi server ünvanı: IP:PORT:USER:PASS və ya http://user:pass@IP:PORT"
                  value={customTestProxyInput}
                  onChange={(e) => setCustomTestProxyInput(e.target.value)}
                  className="flex-1 bg-dark-900 border border-slate-700/80 px-3.5 py-2.5 rounded-xl text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                />
                <button
                  type="button"
                  onClick={() => handleRunProxyTest()}
                  disabled={proxyTestRunning || !customTestProxyInput.trim()}
                  className="flex items-center justify-center gap-2 bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold px-5 py-2.5 rounded-xl transition-all disabled:opacity-50 shadow-lg shadow-purple-500/20"
                >
                  {proxyTestRunning ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                  <span>Fərdi Proksini Yoxla</span>
                </button>
              </div>

              {customTestProxyInput.toLowerCase().includes('bina.az') && (
                <div className="text-[11px] text-amber-300 flex items-start gap-1.5 mt-1.5 bg-amber-500/10 p-2.5 rounded-xl border border-amber-500/30">
                  <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <span>
                    <strong>Diqqət:</strong> Bu xanaya bina.az və ya tap.az saytının ünvanı yazılmamalıdır! Bura yalnız <strong>Webshare və ya proksi provayderinizin verdiyi IP və port</strong> yazılmalıdır (məs: <code className="text-purple-300">31.59.20.176:6754:reipvtkd:kwop2c4stm5r</code>). Hər iki sayta qoşulma arxa planda avtomatik sınaqdan keçirilir.
                  </span>
                </div>
              )}
            </div>

            {/* Test Results Display */}
            {proxyTestResult && (
              <div className={`p-4 rounded-xl border transition-all space-y-3 ${
                proxyTestResult.success
                  ? 'bg-emerald-500/10 border-emerald-500/30'
                  : 'bg-rose-500/10 border-rose-500/30'
              }`}>
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-700/40 pb-2.5">
                  <div className="flex items-center gap-2">
                    {proxyTestResult.success ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
                    )}
                    <div>
                      <span className={`text-sm font-bold block ${proxyTestResult.success ? 'text-emerald-300' : 'text-rose-300'}`}>
                        {proxyTestResult.bina_status === 200 && proxyTestResult.tap_status === 200
                          ? 'Proksi Tam İşləkdir (Bina.az & Tap.az 200 OK)'
                          : proxyTestResult.success
                            ? 'Proksi Qismən İşləkdir'
                            : 'Proksi Əlaqəsi Uğursuz Oldu'}
                      </span>
                      {proxyTestResult.proxy_used && (
                        <span className="text-[11px] font-mono text-slate-400 block mt-0.5">
                          Sınaq edilən proksi: <span className="text-slate-300">{proxyTestResult.proxy_used}</span>
                        </span>
                      )}
                    </div>
                  </div>
                  <span className="text-xs font-mono text-slate-300 bg-dark-900/80 px-2.5 py-1 rounded-lg border border-slate-700 self-start sm:self-auto">
                    ⚡ {proxyTestResult.latency_ms} ms
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
                  <div className="bg-dark-900/60 p-2.5 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block text-[11px] mb-0.5">🌐 Çıxış IP-si (Exit IP)</span>
                    <span className="font-mono text-white font-semibold truncate block">{proxyTestResult.detected_ip || 'Məlum deyil'}</span>
                  </div>
                  <div className="bg-dark-900/60 p-2.5 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block text-[11px] mb-0.5">🏠 Bina.az</span>
                    <span className={`font-mono font-semibold ${proxyTestResult.bina_status === 200 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      HTTP {proxyTestResult.bina_status || 'Xəta'}
                    </span>
                    <span className="text-[10px] text-slate-400 truncate block mt-0.5" title={proxyTestResult.bina_title}>
                      {proxyTestResult.bina_title || '-'}
                    </span>
                  </div>
                  <div className="bg-dark-900/60 p-2.5 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block text-[11px] mb-0.5">📱 Tap.az</span>
                    <span className={`font-mono font-semibold ${proxyTestResult.tap_status === 200 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      HTTP {proxyTestResult.tap_status || 'Xəta'}
                    </span>
                    <span className="text-[10px] text-slate-400 truncate block mt-0.5" title={proxyTestResult.tap_title}>
                      {proxyTestResult.tap_title || '-'}
                    </span>
                  </div>
                  <div className="bg-dark-900/60 p-2.5 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block text-[11px] mb-0.5">🛡️ IP Qorunması</span>
                    <span className="text-emerald-400 font-semibold block">Zero-Leak Aktiv</span>
                    <span className="text-[10px] text-slate-400 block mt-0.5">Statik IP gizlidir</span>
                  </div>
                </div>

                {proxyTestResult.message && (
                  <p className="text-xs text-slate-300 border-t border-slate-700/50 pt-2 leading-relaxed">
                    {proxyTestResult.message}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
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

      {/* SUB-TAB: System Maintenance Mode & Agent Notifications */}
      {activeSubTab === 'maintenance' && (
        <div className="space-y-6">
          {/* Status Overview Card */}
          <div className={`p-6 rounded-2xl border backdrop-blur-xl shadow-xl transition-all ${
            maintenanceStatus?.is_maintenance
              ? 'bg-rose-950/30 border-rose-500/40 shadow-rose-950/20'
              : 'bg-emerald-950/20 border-emerald-500/30 shadow-emerald-950/10'
          }`}>
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-start gap-4">
                <div className={`w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 border ${
                  maintenanceStatus?.is_maintenance
                    ? 'bg-rose-500/20 border-rose-500/40 text-rose-400'
                    : 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400'
                }`}>
                  {maintenanceStatus?.is_maintenance ? (
                    <AlertTriangle className="w-6 h-6 animate-pulse" />
                  ) : (
                    <ShieldCheck className="w-6 h-6" />
                  )}
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <h3 className="text-lg font-bold text-white tracking-tight">
                      {maintenanceStatus?.is_maintenance
                        ? 'Sistem Texniki Baxış Rejimindədir (Fasilə)'
                        : 'Sistem Normal Rejimdə Çalışır'}
                    </h3>
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider ${
                      maintenanceStatus?.is_maintenance
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                        : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                    }`}>
                      {maintenanceStatus?.is_maintenance ? 'Texniki Baxış Aktiv' : 'Normal Rejim'}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300">
                    {maintenanceStatus?.is_maintenance
                      ? `Səbəb: ${maintenanceStatus.reason || 'Planlı profilaktika'}`
                      : 'Bütün xidmətlər, bot əmrləri və elan axtarış skraperləri aktiv rejimdə işləyir.'}
                  </p>

                  {maintenanceStatus?.is_maintenance && maintenanceStatus.started_at && (
                    <div className="flex items-center gap-4 text-xs text-slate-400 pt-1">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-amber-400" />
                        Başlanma: {new Date(maintenanceStatus.started_at).toLocaleString('az-AZ')}
                      </span>
                      {maintenanceStatus.estimated_minutes > 0 && (
                        <span className="text-amber-300">
                          Təxmini müddət: ~{maintenanceStatus.estimated_minutes} dəqiqə
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Action Button: End or Refresh */}
              <div className="flex items-center gap-2 self-end md:self-center">
                <button
                  type="button"
                  onClick={loadMaintenanceStatus}
                  disabled={loadingMaintenance}
                  className="px-3 py-2 text-xs text-slate-400 hover:text-white bg-dark-900/60 border border-slate-700/60 rounded-xl hover:bg-dark-900 transition-all flex items-center gap-1.5"
                  title="Yenilə"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingMaintenance ? 'animate-spin' : ''}`} />
                  <span>Yenilə</span>
                </button>

                {maintenanceStatus?.is_maintenance && (
                  <button
                    type="button"
                    onClick={handleDisableMaintenance}
                    disabled={maintenanceActionLoading}
                    className="px-4 py-2 text-xs font-semibold text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 rounded-xl shadow-lg shadow-emerald-600/20 flex items-center gap-1.5 disabled:opacity-50 transition-all"
                  >
                    <Power className="w-4 h-4" />
                    <span>{maintenanceActionLoading ? 'Bərpa edilir...' : 'Texniki Baxışı Dayandır (Bərpa Et)'}</span>
                  </button>
                )}
              </div>
            </div>

            {/* Notification Bar */}
            {maintenanceAlert && (
              <div className={`mt-4 p-3 rounded-xl text-xs flex items-center gap-2 border ${
                maintenanceAlert.type === 'success'
                  ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                  : 'bg-rose-500/10 text-rose-300 border-rose-500/30'
              }`}>
                {maintenanceAlert.type === 'success' ? (
                  <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                ) : (
                  <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
                )}
                <span>{maintenanceAlert.message}</span>
              </div>
            )}
          </div>

          {/* Quick Stats Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-dark-800/80 p-4 rounded-xl border border-slate-800 flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                <Radio className="w-5 h-5" />
              </div>
              <div>
                <p className="text-[11px] text-slate-400">Qoşulmuş Agentlər</p>
                <p className="text-lg font-bold text-white">
                  {maintenanceStatus?.connected_agents_count || 0}
                  <span className="text-[11px] font-normal text-slate-400 ml-1">aktiv abunəçi</span>
                </p>
              </div>
            </div>

            <div className="bg-dark-800/80 p-4 rounded-xl border border-slate-800 flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                <Clock className="w-5 h-5" />
              </div>
              <div>
                <p className="text-[11px] text-slate-400">Gözlənilən Fasilə</p>
                <p className="text-lg font-bold text-white">
                  {maintenanceMinutes}
                  <span className="text-[11px] font-normal text-slate-400 ml-1">dəqiqə</span>
                </p>
              </div>
            </div>

            <div className="bg-dark-800/80 p-4 rounded-xl border border-slate-800 flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                <Send className="w-5 h-5" />
              </div>
              <div>
                <p className="text-[11px] text-slate-400">Xəbərdarlıq Kanalları</p>
                <p className="text-sm font-semibold text-slate-200">
                  Telegram & WhatsApp
                </p>
              </div>
            </div>
          </div>

          {/* Maintenance Control / Launch Form */}
          <div className="bg-dark-800/90 p-6 rounded-2xl border border-slate-800 space-y-6 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Power className="w-4 h-4 text-amber-400" />
                  <span>Texniki Baxış Rejimini İdarə Et və Agentləri Xəbərdar Et</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Texniki baxış aktiv olduqda bot sorğulara fasilə bildirişi verəcək, skraperlər dayanacaq və agentlərə dərhal mesaj çatdırılacaq.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Left Column: Form Controls */}
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Texniki Baxışın Səbəbi
                  </label>
                  <input
                    type="text"
                    value={maintenanceReason}
                    onChange={(e) => setMaintenanceReason(e.target.value)}
                    placeholder="Məs: Planlı server profilaktikası və yenilənmə"
                    className="w-full glass-input px-3.5 py-2.5 rounded-xl text-sm text-white bg-dark-900 border border-slate-700 focus:border-amber-500/50"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">Bu səbəb agentlərə göndərilən bildiriş mətnində əks olunacaq.</p>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Təxmini Fasilə Müddəti (Dəqiqə)
                  </label>
                  <div className="flex items-center gap-3">
                    <input
                      type="number"
                      min={5}
                      max={1440}
                      step={5}
                      value={maintenanceMinutes}
                      onChange={(e) => setMaintenanceMinutes(Math.max(5, parseInt(e.target.value) || 30))}
                      className="w-32 glass-input px-3.5 py-2 rounded-xl text-sm text-white bg-dark-900 border border-slate-700"
                    />
                    {/* Quick Presets */}
                    <div className="flex items-center gap-1.5">
                      {[15, 30, 60, 120].map((m) => (
                        <button
                          key={m}
                          type="button"
                          onClick={() => setMaintenanceMinutes(m)}
                          className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition-all ${
                            maintenanceMinutes === m
                              ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                              : 'bg-dark-900/60 text-slate-400 border-slate-800 hover:text-slate-200'
                          }`}
                        >
                          {m >= 60 ? `${m / 60} saat` : `${m} dəq`}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Broadcast Checkbox */}
                <div className="p-3 rounded-xl bg-dark-900/60 border border-slate-800 flex items-start gap-3">
                  <input
                    type="checkbox"
                    id="notify_agents_check"
                    checked={maintenanceNotify}
                    onChange={(e) => setMaintenanceNotify(e.target.checked)}
                    className="mt-0.5 rounded border-slate-700 text-amber-500 focus:ring-amber-500/20"
                  />
                  <label htmlFor="notify_agents_check" className="text-xs text-slate-300 cursor-pointer">
                    <span className="font-semibold text-white block">Qoşulmuş bütün agentlərə xəbərdarlıq göndər</span>
                    <span className="text-slate-400">
                      Sistem aktivləşdiriləndə və söndürüləndə bütün aktiv rieltor agentlərə Telegram və WhatsApp vasitəsilə bildiriş göndərilir.
                    </span>
                  </label>
                </div>

                {/* Custom Start Message (Optional override) */}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Fərdi Başlanğıc Mesajı (İstəyə görə)
                  </label>
                  <textarea
                    rows={3}
                    value={customStartMsg}
                    onChange={(e) => setCustomStartMsg(e.target.value)}
                    placeholder="Boş saxlasanız, sistemin standart peşəkar bildiriş şablonu göndəriləcək..."
                    className="w-full glass-input px-3.5 py-2 rounded-xl text-xs text-white bg-dark-900 border border-slate-700 focus:border-amber-500/50 resize-none font-mono"
                  />
                </div>

                {/* Custom End Message (Optional override) */}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Fərdi Bərpa Mesajı (İstəyə görə)
                  </label>
                  <textarea
                    rows={3}
                    value={customEndMsg}
                    onChange={(e) => setCustomEndMsg(e.target.value)}
                    placeholder="Boş saxlasanız, sistemin standart 'Texniki baxış başa çatdı' şablonu göndəriləcək..."
                    className="w-full glass-input px-3.5 py-2 rounded-xl text-xs text-white bg-dark-900 border border-slate-700 focus:border-emerald-500/50 resize-none font-mono"
                  />
                </div>

                {/* Action Buttons */}
                <div className="pt-2 flex items-center gap-3">
                  {!maintenanceStatus?.is_maintenance ? (
                    <button
                      type="button"
                      onClick={handleEnableMaintenance}
                      disabled={maintenanceActionLoading}
                      className="px-5 py-2.5 rounded-xl font-semibold text-xs text-white bg-gradient-to-r from-amber-600 to-rose-600 hover:from-amber-500 hover:to-rose-500 flex items-center gap-2 shadow-lg shadow-amber-600/20 disabled:opacity-50 transition-all"
                    >
                      <AlertTriangle className="w-4 h-4" />
                      <span>{maintenanceActionLoading ? 'Aktivləşdirilir...' : 'Texniki Baxışı Aktivləşdir və Agentlərə Bildir'}</span>
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={handleDisableMaintenance}
                      disabled={maintenanceActionLoading}
                      className="px-5 py-2.5 rounded-xl font-semibold text-xs text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 flex items-center gap-2 shadow-lg shadow-emerald-600/20 disabled:opacity-50 transition-all"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      <span>{maintenanceActionLoading ? 'Söndürülür...' : 'Texniki Baxışı Söndür və Sistemi Bərpa Et'}</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Right Column: Live Message Preview */}
              <div className="space-y-4">
                <div>
                  <h4 className="text-xs font-semibold text-slate-300 flex items-center gap-1.5 mb-2">
                    <Send className="w-3.5 h-3.5 text-blue-400" />
                    <span>Agentlərə Göndəriləcək Mesajın Canlı Önizləməsi</span>
                  </h4>
                  <p className="text-[11px] text-slate-400 mb-3">
                    Aktivləşdirmə düyməsinə basdıqda bütün qoşulmuş agentlər Telegram/WhatsApp-da bu mesajı alacaq:
                  </p>
                </div>

                {/* Start Message Preview Card */}
                <div className="p-4 rounded-xl bg-dark-900 border border-amber-500/20 space-y-2">
                  <div className="flex items-center justify-between text-[10px] text-amber-400 font-semibold uppercase tracking-wider">
                    <span>1. Texniki Baxış Başladıqda</span>
                    <span>Telegram / WhatsApp</span>
                  </div>
                  <pre className="text-[11px] text-slate-200 whitespace-pre-wrap font-sans bg-black/40 p-3 rounded-lg border border-slate-800 leading-relaxed">
                    {customStartMsg || maintenanceStatus?.preview_start_message || `⚠️ DİQQƏT: PLANLI TEXNİKİ BAXIŞ\n\nHörmətli tərəfdaşımız,\n\nSistemimizdə xidmət keyfiyyətinin və sürətinin artırılması məqsədilə texniki baxış işləri aparılır.\n\n📌 Səbəb: ${maintenanceReason}\n⏱ Təxmini fasilə müddəti: ~${maintenanceMinutes} dəqiqə\n\nBu müddət ərzində yeni elanların axtarışı və bot sorğuları müvəqqəti dayandırılacaq.\nİşlər yekunlaşan kimi sizə dərhal xəbər veriləcəkdir.\n\nAnlayışınız üçün təşəkkür edirik! 🙏`}
                  </pre>
                </div>

                {/* End Message Preview Card */}
                <div className="p-4 rounded-xl bg-dark-900 border border-emerald-500/20 space-y-2">
                  <div className="flex items-center justify-between text-[10px] text-emerald-400 font-semibold uppercase tracking-wider">
                    <span>2. Texniki Baxış Bitdikdə</span>
                    <span>Telegram / WhatsApp</span>
                  </div>
                  <pre className="text-[11px] text-slate-200 whitespace-pre-wrap font-sans bg-black/40 p-3 rounded-lg border border-slate-800 leading-relaxed">
                    {customEndMsg || maintenanceStatus?.preview_end_message || `✅ TEXNİKİ BAXIŞ BAŞA ÇATDI!\n\nHörmətli tərəfdaşımız,\n\nSistemimizdə aparılan texniki profilaktika və optimizasiya işləri uğurla tamamlanmışdır.\n\n🚀 Bütün xidmətlər, real vaxt rejimində elan axtarışı və bot funksionallığı tam bərpa edildi.\n\nXidmətimizdən istifadə etdiyiniz üçün təşəkkür edirik! 🤝`}
                  </pre>
                </div>

                {/* Maintenance Policy Note */}
                <div className="p-3.5 rounded-xl bg-blue-950/20 border border-blue-500/20 text-xs text-blue-300 space-y-1">
                  <div className="font-semibold flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
                    <span>Texniki Baxış Rejiminin Qoruyucu Təsirləri:</span>
                  </div>
                  <ul className="list-disc list-inside space-y-0.5 text-[11px] text-slate-400">
                    <li>Celery elan skraperləri fasiləyə keçir (verilənlər bazası və server yükü sıfırlanır).</li>
                    <li>Agentlər bota yazdığı zaman bot dərhal texniki baxış mesajı ilə cavab verir.</li>
                    <li>SaaS Admin Paneli fasiləsiz işləyir və istənilən an bir toxunuşla bərpa edilə bilər.</li>
                  </ul>
                </div>
              </div>
            </div>
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
