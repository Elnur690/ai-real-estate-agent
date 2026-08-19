import React, { useEffect, useState } from 'react';
import { Database, RefreshCw, CheckCircle2, AlertCircle, Plus, Trash2, Power, Globe, MessageSquare, Facebook, ExternalLink, Copy, Check } from 'lucide-react';
import api from '../api';
import { ScraperSource } from '../types';
import { useTranslation } from '../i18n';

export const ScrapersView: React.FC = () => {
  const [sources, setSources] = useState<ScraperSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [cycleResult, setCycleResult] = useState<any>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [copiedWebhook, setCopiedWebhook] = useState(false);
  const { t } = useTranslation();

  // New Source Form State
  const [newType, setNewType] = useState<'facebook_group' | 'facebook_page' | 'telegram_channel' | 'website'>('facebook_group');
  const [newName, setNewName] = useState('');
  const [newUrl, setNewUrl] = useState('');
  const [savingSource, setSavingSource] = useState(false);

  const loadSources = async () => {
    setLoading(true);
    try {
      const res = await api.get('/scrapers/sources');
      setSources(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSources();
  }, []);

  const handleTriggerCycle = async () => {
    setTriggering(true);
    setCycleResult(null);
    try {
      const res = await api.post('/scrapers/trigger');
      setCycleResult(res.data.result);
      await loadSources();
    } catch (e: any) {
      console.error(e);
    } finally {
      setTriggering(false);
    }
  };

  const handleAddSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim() || !newUrl.trim()) return;
    setSavingSource(true);
    try {
      await api.post('/scrapers/sources', {
        name: newName.trim(),
        type: newType,
        url_or_handle: newUrl.trim()
      });
      setShowAddModal(false);
      setNewName('');
      setNewUrl('');
      await loadSources();
    } catch (e) {
      console.error(e);
      alert('Mənbə əlavə edilərkən xəta baş verdi');
    } finally {
      setSavingSource(false);
    }
  };

  const handleToggleStatus = async (id: number) => {
    try {
      await api.patch(`/scrapers/sources/${id}/toggle`);
      await loadSources();
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteSource = async (id: number, name: string) => {
    if (!confirm(`"${name}" mənbəyini silmək istədiyinizə əminsiniz?`)) return;
    try {
      await api.delete(`/scrapers/sources/${id}`);
      await loadSources();
    } catch (e) {
      console.error(e);
    }
  };

  const copyWebhookUrl = () => {
    const webhookUrl = `${window.location.origin.replace('3000', '8000')}/api/v1/webhooks/facebook`;
    navigator.clipboard.writeText(webhookUrl);
    setCopiedWebhook(true);
    setTimeout(() => setCopiedWebhook(false), 2500);
  };

  const getTypeBadge = (type: string) => {
    if (type === 'facebook_group') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
          <Facebook className="w-3.5 h-3.5" /> Facebook Qrupu
        </span>
      );
    }
    if (type === 'facebook_page') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
          <Facebook className="w-3.5 h-3.5" /> Facebook Səhifəsi
        </span>
      );
    }
    if (type === 'telegram_channel') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/20">
          <MessageSquare className="w-3.5 h-3.5" /> Telegram Kanalı
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-700/50 text-slate-300 border border-slate-600/30">
        <Globe className="w-3.5 h-3.5" /> Veb Portal
      </span>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Database className="w-5 h-5 text-emerald-400" />
            {t.scrapersTitle}
          </h2>
          <p className="text-slate-400 text-xs mt-0.5">
            {t.scrapersSubtitle}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-all shadow-lg shadow-blue-600/20"
          >
            <Plus className="w-4 h-4" />
            Yeni Mənbə (Facebook / Telegram)
          </button>
          <button
            onClick={handleTriggerCycle}
            disabled={triggering}
            className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-all shadow-lg shadow-emerald-500/20 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${triggering ? 'animate-spin' : ''}`} />
            {triggering ? t.loading : t.triggerManualScrape}
          </button>
        </div>
      </div>

      {/* Webhook & Realtime Ingestion Info Card */}
      <div className="p-4 rounded-2xl bg-gradient-to-r from-blue-950/40 via-dark-800 to-indigo-950/40 border border-blue-500/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-white font-semibold text-sm">
            <Facebook className="w-4 h-4 text-blue-400" />
            Facebook & Xarici Botlar üçün Real-Time Webhook Endpoint
          </div>
          <p className="text-slate-400 text-xs">
            Zapier, Make.com və ya xüsusi skriptlər vasitəsilə Facebook qruplarındakı yeni elanları anında bu ünvana göndərə bilərsiniz:
          </p>
        </div>
        <button
          onClick={copyWebhookUrl}
          className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs px-3.5 py-2 rounded-xl transition-all font-mono whitespace-nowrap self-start md:self-auto"
        >
          {copiedWebhook ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 text-slate-400" />}
          {copiedWebhook ? 'Kopyalandı!' : 'POST /api/v1/webhooks/facebook'}
        </button>
      </div>

      {cycleResult && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center justify-between">
          <span className="font-semibold flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" /> {t.success}!
          </span>
          <span>{t.totalListings}: {cycleResult.scraped_count} | {t.dailyMatches}: {cycleResult.matched_count}</span>
        </div>
      )}

      {/* Sources Table */}
      <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-dark-800/80 text-slate-400 font-medium text-xs uppercase tracking-wider border-b border-slate-800">
            <tr>
              <th className="p-4">Portal / Mənbə Adı</th>
              <th className="p-4">Növ</th>
              <th className="p-4">URL / Qrup Linki</th>
              <th className="p-4">{t.status}</th>
              <th className="p-4">{t.lastScrape}</th>
              <th className="p-4 text-right">Əməliyyatlar</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {sources.map((s) => (
              <tr key={s.id} className="hover:bg-dark-700/30 transition-colors">
                <td className="p-4 font-bold text-white flex items-center gap-2">
                  {s.name}
                </td>
                <td className="p-4">{getTypeBadge(s.type)}</td>
                <td className="p-4 font-mono text-xs text-slate-300 max-w-xs truncate">
                  <a href={s.url_or_handle.startsWith('http') ? s.url_or_handle : `https://t.me/${s.url_or_handle.replace('@', '')}`} target="_blank" rel="noreferrer" className="text-emerald-400 hover:underline flex items-center gap-1 truncate">
                    {s.url_or_handle}
                    <ExternalLink className="w-3 h-3 flex-shrink-0" />
                  </a>
                </td>
                <td className="p-4">
                  <span className={`inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-medium ${
                    s.status === 'active' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'
                  }`}>
                    {s.status === 'active' ? <CheckCircle2 className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
                    {s.status === 'active' ? 'Aktiv' : 'Dayandırılıb'}
                  </span>
                </td>
                <td className="p-4 text-xs text-slate-400">
                  {s.last_scraped_at ? new Date(s.last_scraped_at).toLocaleString() : 'Hələ skreyp edilməyib'}
                </td>
                <td className="p-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => handleToggleStatus(s.id)}
                      title={s.status === 'active' ? 'Mənbəni dayandır' : 'Mənbəni aktivləşdir'}
                      className={`p-1.5 rounded-lg transition-colors ${s.status === 'active' ? 'text-amber-400 hover:bg-amber-500/10' : 'text-emerald-400 hover:bg-emerald-500/10'}`}
                    >
                      <Power className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDeleteSource(s.id, s.name)}
                      title="Mənbəni sil"
                      className="p-1.5 rounded-lg text-red-400 hover:bg-red-500/10 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {sources.length === 0 && (
              <tr>
                <td colSpan={6} className="p-8 text-center text-slate-500">
                  Heç bir mənbə tapılmadı.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Add Source Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="glass-card bg-dark-900 border border-slate-700 rounded-2xl w-full max-w-md p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Plus className="w-5 h-5 text-blue-400" />
                Yeni Mənbə Əlavə Et
              </h3>
              <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-white text-sm">✕</button>
            </div>

            <form onSubmit={handleAddSource} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Mənbə Növü</label>
                <select
                  value={newType}
                  onChange={(e: any) => setNewType(e.target.value)}
                  className="w-full bg-dark-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="facebook_group">Facebook Qrupu</option>
                  <option value="facebook_page">Facebook Səhifəsi</option>
                  <option value="telegram_channel">Telegram Kanalı</option>
                  <option value="website">Veb Portal / Sayt</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Mənbə Adı</label>
                <input
                  type="text"
                  placeholder="məs. Bakıda Ev Alqı-Satqısı Qrupu"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  required
                  className="w-full bg-dark-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  {newType.startsWith('facebook') ? 'Facebook Qrup / Səhifə Linki' : (newType === 'telegram_channel' ? 'Telegram Kanalı (@kanal və ya link)' : 'Portal URL-i')}
                </label>
                <input
                  type="text"
                  placeholder={newType.startsWith('facebook') ? 'https://facebook.com/groups/baki.emlak' : (newType === 'telegram_channel' ? '@emlaktap' : 'https://example.az/elanlar')}
                  value={newUrl}
                  onChange={(e) => setNewUrl(e.target.value)}
                  required
                  className="w-full bg-dark-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 font-mono text-xs"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2.5 rounded-xl border border-slate-700 text-slate-300 text-sm font-medium hover:bg-slate-800 transition-colors"
                >
                  Ləğv et
                </button>
                <button
                  type="submit"
                  disabled={savingSource}
                  className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition-colors disabled:opacity-50"
                >
                  {savingSource ? 'Yadda saxlanılır...' : 'Əlavə Et'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
