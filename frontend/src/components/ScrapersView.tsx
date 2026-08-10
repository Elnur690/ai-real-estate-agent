import React, { useEffect, useState } from 'react';
import { Database, RefreshCw, CheckCircle2, AlertCircle, ExternalLink } from 'lucide-react';
import api from '../api';
import { ScraperSource } from '../types';

export const ScrapersView: React.FC = () => {
  const [sources, setSources] = useState<ScraperSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [cycleResult, setCycleResult] = useState<any>(null);

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

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Database className="w-5 h-5 text-emerald-400" />
            Scraper Sources & Pipeline Health
          </h2>
          <p className="text-slate-400 text-xs mt-0.5">
            Public real estate websites (bina.az, tap.az) and public Telegram channel crawlers.
          </p>
        </div>
        <button
          onClick={handleTriggerCycle}
          disabled={triggering}
          className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-all shadow-lg shadow-emerald-500/20 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${triggering ? 'animate-spin' : ''}`} />
          {triggering ? 'Scraping & Matching...' : 'Run Pipeline Cycle Now'}
        </button>
      </div>

      {cycleResult && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center justify-between">
          <span className="font-semibold flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" /> Cycle Completed Successfully!
          </span>
          <span>Scraped: {cycleResult.scraped_count} listings | Matches Delivered: {cycleResult.matched_count}</span>
        </div>
      )}

      <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-dark-800/80 text-slate-400 font-medium text-xs uppercase tracking-wider border-b border-slate-800">
            <tr>
              <th className="p-4">Source Name</th>
              <th className="p-4">Type</th>
              <th className="p-4">URL / Handle</th>
              <th className="p-4">Status</th>
              <th className="p-4">Last Scraped At</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {sources.map((s) => (
              <tr key={s.id} className="hover:bg-dark-700/30 transition-colors">
                <td className="p-4 font-bold text-white">{s.name}</td>
                <td className="p-4 capitalize text-xs text-slate-400">{s.type.replace('_', ' ')}</td>
                <td className="p-4 font-mono text-xs text-emerald-400 flex items-center gap-1">
                  {s.url_or_handle}
                </td>
                <td className="p-4">
                  <span className={`inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-medium ${
                    s.status === 'active' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
                  }`}>
                    {s.status === 'active' ? <CheckCircle2 className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
                    {s.status}
                  </span>
                </td>
                <td className="p-4 text-xs text-slate-400">
                  {s.last_scraped_at ? new Date(s.last_scraped_at).toLocaleString() : 'Never'}
                </td>
              </tr>
            ))}
            {sources.length === 0 && (
              <tr>
                <td colSpan={5} className="p-8 text-center text-slate-500">
                  No sources registered. Click "Run Pipeline Cycle Now" to seed default bina.az and tap.az sources.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
