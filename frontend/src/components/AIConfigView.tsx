import React, { useEffect, useState } from 'react';
import { Cpu, Key, CheckCircle2, AlertTriangle, Zap, History, Play } from 'lucide-react';
import api from '../api';
import { AIProviderConfigItem, AICallLogItem } from '../types';

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

interface AITaskCardProps {
  task: TaskType;
  cfg: AIProviderConfigItem;
  onSave: (taskType: string, provider: string, modelName: string, apiKey?: string) => void;
  onTest: (provider: string, modelName: string, apiKey?: string) => void;
}

const AITaskCard: React.FC<AITaskCardProps> = ({ task, cfg, onSave, onTest }) => {
  const [selectedProvider, setSelectedProvider] = useState<string>(cfg.provider || 'gemini');
  const [selectedModel, setSelectedModel] = useState<string>(cfg.model_name || 'gemini-3.5-flash');
  const [apiKeyInput, setApiKeyInput] = useState('');

  useEffect(() => {
    setSelectedProvider(cfg.provider || 'gemini');
    setSelectedModel(cfg.model_name || 'gemini-3.5-flash');
  }, [cfg]);

  return (
    <div className="glass-card p-5 rounded-2xl border border-slate-800 space-y-4 flex flex-col justify-between">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-white">{task.label}</h3>
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
              setSelectedModel(modelOptions[p] ? modelOptions[p][0] : 'gemini-1.5-flash');
            }}
            className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800"
          >
            <option value="gemini">Gemini (Default Free Tier)</option>
            <option value="claude">Claude (Anthropic)</option>
            <option value="gpt">GPT (OpenAI)</option>
          </select>
        </div>

        <div>
          <label className="text-xs text-slate-400 block mb-1">Model Name</label>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800"
          >
            {(modelOptions[selectedProvider] || []).map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-xs text-slate-400 block mb-1">
            API Key {cfg.api_key_masked && <span className="text-slate-500">({cfg.api_key_masked})</span>}
          </label>
          <div className="relative">
            <Key className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
            <input
              type="password"
              placeholder={cfg.api_key_masked ? "Leave blank to keep existing key" : "Enter API key"}
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
              className="w-full glass-input pl-9 pr-3 py-2 rounded-xl text-xs text-white"
            />
          </div>
        </div>
      </div>

      <div className="pt-2 flex items-center justify-between gap-2 border-t border-slate-800">
        <button
          type="button"
          onClick={() => onTest(selectedProvider, selectedModel, apiKeyInput)}
          className="text-xs font-medium text-purple-400 hover:text-purple-300 flex items-center gap-1"
        >
          <Play className="w-3 h-3" /> Test
        </button>
        <button
          type="button"
          onClick={() => onSave(task.key, selectedProvider, selectedModel, apiKeyInput)}
          className="px-3 py-1.5 bg-purple-500 hover:bg-purple-600 text-white rounded-lg text-xs font-medium"
        >
          Save Config
        </button>
      </div>
    </div>
  );
};

export const AIConfigView: React.FC = () => {
  const [configs, setConfigs] = useState<AIProviderConfigItem[]>([]);
  const [callLogs, setCallLogs] = useState<AICallLogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [testResult, setTestResult] = useState<any>(null);
  const [testing, setTesting] = useState(false);

  const taskTypes: TaskType[] = [
    { key: 'criteria_parsing', label: 'Criteria Parsing (Conversational Agent)', defaultProvider: 'gemini', defaultModel: 'gemini-3.5-flash' },
    { key: 'listing_parsing', label: 'Telegram Unformatted Listing Parser', defaultProvider: 'gemini', defaultModel: 'gemini-3.5-flash' },
    { key: 'match_scoring', label: 'Match Scoring Engine', defaultProvider: 'gemini', defaultModel: 'gemini-3.5-flash' },
  ];

  const loadConfigs = async () => {
    setLoading(true);
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
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConfigs();
  }, []);

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

  const handleSaveConfig = async (taskType: string, provider: string, modelName: string, apiKey?: string) => {
    try {
      await api.post('/ai-config', {
        task_type: taskType,
        provider,
        model_name: modelName,
        api_key: apiKey || undefined
      });
      loadConfigs();
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
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <Cpu className="w-5 h-5 text-purple-400" />
          AI Provider Abstraction Layer
        </h2>
        <p className="text-slate-400 text-xs mt-0.5">
          Switch active AI model per task (Gemini free tier, Claude, or GPT) without backend redeployment.
        </p>
      </div>

      {/* Task Config Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {taskTypes.map((task) => (
          <AITaskCard
            key={task.key}
            task={task}
            cfg={getConfigForTask(task.key)}
            onSave={handleSaveConfig}
            onTest={handleTestConnection}
          />
        ))}
      </div>

      {/* Connection Test Output Result */}
      {testResult && (
        <div className={`p-4 rounded-xl border text-xs ${testResult.success ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-red-500/10 border-red-500/30 text-red-300'}`}>
          <div className="font-bold flex items-center gap-2">
            {testResult.success ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
            Connection Test Result for {testResult.provider} ({testResult.model_name}) — Latency: {testResult.latency_ms}ms
          </div>
          {testResult.success ? (
            <div className="mt-1 text-slate-300">Parsed Test Summary: "{testResult.test_output}"</div>
          ) : (
            <div className="mt-1 font-mono text-red-400">{testResult.error}</div>
          )}
        </div>
      )}

      {/* AI Call Logs Table */}
      <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
        <div className="p-4 bg-dark-800/80 border-b border-slate-800 flex items-center gap-2 text-sm font-semibold text-white">
          <History className="w-4 h-4 text-purple-400" />
          Recent AI Provider Call Logs
        </div>
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-dark-800/40 text-slate-400 font-medium uppercase tracking-wider border-b border-slate-800">
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
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-sans font-medium ${
                    log.status === 'success' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
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
  );
};
