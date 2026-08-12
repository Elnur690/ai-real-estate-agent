import React, { useEffect, useState } from 'react';
import { Sliders, Save, CheckCircle, Cpu, Key, CheckCircle2, AlertTriangle, Play, History, Building2, SlidersHorizontal, Database } from 'lucide-react';
import api from '../api';
import { AIProviderConfigItem, AICallLogItem } from '../types';

export const AppSettingsView: React.FC = () => {
  const [activeSubTab, setActiveSubTab] = useState<'branding' | 'ai' | 'automation'>('branding');

  // App Branding State
  const [settingsMap, setSettingsMap] = useState<Record<string, string>>({
    app_name: 'RealEstate AI Agent',
    support_phone: '+994501234567',
    app_logo_url: '',
    makler_threshold: '0.7',
    cobrokering_default_split: '50'
  });
  const [brandingSaved, setBrandingSaved] = useState(false);
  const [savingBranding, setSavingBranding] = useState(false);

  // AI Provider State
  const [configs, setConfigs] = useState<AIProviderConfigItem[]>([]);
  const [callLogs, setCallLogs] = useState<AICallLogItem[]>([]);
  const [loadingAi, setLoadingAi] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);
  const [testing, setTesting] = useState(false);

  const taskTypes = [
    { key: 'criteria_parsing', label: 'Criteria Parsing (Conversational Agent)', defaultProvider: 'gemini', defaultModel: 'gemini-2.5-flash' },
    { key: 'listing_parsing', label: 'Telegram Unformatted Listing Parser', defaultProvider: 'gemini', defaultModel: 'gemini-2.5-flash' },
    { key: 'match_scoring', label: 'Match Scoring Engine', defaultProvider: 'gemini', defaultModel: 'gemini-2.5-flash' },
  ];

  const modelOptions: Record<string, string[]> = {
    gemini: ['gemini-2.5-flash', 'gemini-1.5-pro'],
    claude: ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022'],
    gpt: ['gpt-4o', 'gpt-4o-mini']
  };

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
  }, []);

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

  const getConfigForTask = (taskType: string) => {
    return configs.find(c => c.task_type === taskType) || {
      provider: 'gemini',
      model_name: 'gemini-2.5-flash',
      api_key_masked: ''
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
              <p className="text-xs text-slate-400">Manage runtime app parameters, AI Provider models, keys & automation thresholds</p>
            </div>
          </div>
        </div>

        {/* Sub-Navigation Tabs */}
        <div className="flex items-center gap-1 bg-dark-900/90 p-1.5 rounded-xl border border-slate-800 self-start sm:self-auto">
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
            {taskTypes.map((task) => {
              const cfg = getConfigForTask(task.key);
              const [selectedProvider, setSelectedProvider] = useState(cfg.provider);
              const [selectedModel, setSelectedModel] = useState(cfg.model_name);
              const [apiKeyInput, setApiKeyInput] = useState('');

              return (
                <div key={task.key} className="bg-dark-800/90 p-5 rounded-2xl border border-slate-800 space-y-4 flex flex-col justify-between shadow-xl">
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
                          setSelectedProvider(p as any);
                          setSelectedModel(modelOptions[p][0]);
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
                      onClick={() => handleTestConnection(selectedProvider, selectedModel, apiKeyInput)}
                      className="text-xs font-semibold text-purple-400 hover:text-purple-300 flex items-center gap-1"
                    >
                      <Play className="w-3 h-3" /> Test Connection
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSaveAiConfig(task.key, selectedProvider, selectedModel, apiKeyInput)}
                      className="px-3 py-1.5 bg-gradient-to-r from-purple-500 to-teal-500 hover:from-purple-400 hover:to-teal-400 text-white rounded-lg text-xs font-semibold shadow-md"
                    >
                      Save Config
                    </button>
                  </div>
                </div>
              );
            })}
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

            <div>
              <label className="text-xs text-slate-300 font-semibold block mb-1">Co-Brokering Default Commission Split % (`cobrokering_default_split`)</label>
              <input
                type="number"
                min="0"
                max="100"
                value={settingsMap['cobrokering_default_split'] || '50'}
                onChange={(e) => setSettingsMap({ ...settingsMap, cobrokering_default_split: e.target.value })}
                className="w-full bg-dark-900 border border-slate-700/80 px-3.5 py-2.5 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
              />
              <span className="text-[11px] text-slate-500 mt-1 block">
                Default percentage split for B2B co-brokering deals.
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
    </div>
  );
};
