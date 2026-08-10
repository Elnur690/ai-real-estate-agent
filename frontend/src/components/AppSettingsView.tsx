import React, { useEffect, useState } from 'react';
import { Sliders, Save, CheckCircle } from 'lucide-react';
import api from '../api';

export const AppSettingsView: React.FC = () => {
  const [settingsMap, setSettingsMap] = useState<Record<string, string>>({
    app_name: 'RealEstate AI Agent',
    support_phone: '+994501234567',
    app_logo_url: ''
  });
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState(false);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const res = await api.get('/settings');
      setSettingsMap(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(false);
    try {
      await api.post('/settings', { settings: settingsMap });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <Sliders className="w-5 h-5 text-emerald-400" />
          Runtime App Settings (`app_settings` table)
        </h2>
        <p className="text-slate-400 text-xs mt-0.5">
          App name and branding settings are stored in the database and read at runtime to populate bot messages, email templates, and dashboard headers without code redeploy.
        </p>
      </div>

      <form onSubmit={handleSave} className="glass-card p-6 rounded-2xl border border-slate-800 space-y-4">
        <div>
          <label className="text-xs text-slate-400 block mb-1">Application Name (`app_name`)</label>
          <input
            type="text"
            required
            value={settingsMap['app_name'] || ''}
            onChange={(e) => setSettingsMap({ ...settingsMap, app_name: e.target.value })}
            className="w-full glass-input px-3.5 py-2.5 rounded-xl text-sm text-white"
          />
          <span className="text-[11px] text-slate-500 mt-1 block">
            Used in WhatsApp / Telegram bot welcome messages & confirmations ("{settingsMap['app_name']} botuna xoş gəlmisiniz").
          </span>
        </div>

        <div>
          <label className="text-xs text-slate-400 block mb-1">Support Contact Phone (`support_phone`)</label>
          <input
            type="text"
            value={settingsMap['support_phone'] || ''}
            onChange={(e) => setSettingsMap({ ...settingsMap, support_phone: e.target.value })}
            className="w-full glass-input px-3.5 py-2.5 rounded-xl text-sm text-white"
          />
        </div>

        <div>
          <label className="text-xs text-slate-400 block mb-1">Custom Logo URL (`app_logo_url`)</label>
          <input
            type="text"
            placeholder="https://example.com/logo.png"
            value={settingsMap['app_logo_url'] || ''}
            onChange={(e) => setSettingsMap({ ...settingsMap, app_logo_url: e.target.value })}
            className="w-full glass-input px-3.5 py-2.5 rounded-xl text-sm text-white"
          />
        </div>

        <div className="pt-2 flex items-center justify-between">
          {saved && (
            <span className="text-xs text-emerald-400 font-medium flex items-center gap-1">
              <CheckCircle className="w-4 h-4" /> Settings updated cleanly in database!
            </span>
          )}
          <button
            type="submit"
            className="ml-auto flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-medium px-5 py-2.5 rounded-xl transition-all shadow-lg shadow-emerald-500/20"
          >
            <Save className="w-4 h-4" />
            Save Settings
          </button>
        </div>
      </form>
    </div>
  );
};
