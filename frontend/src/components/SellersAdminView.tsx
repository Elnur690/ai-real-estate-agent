import React, { useEffect, useState } from 'react';
import { Store, Plus, Edit3, Trash2, Users, DollarSign, Award, CheckCircle, AlertTriangle, Shield, RefreshCw, X, ChevronRight } from 'lucide-react';
import api from '../api';

export interface SellerItem {
  id: number;
  user_id: number;
  name: string;
  email: string;
  phone: string;
  company_name?: string;
  commission_rate: number;
  rank: string;
  status: string;
  balance: number;
  total_earnings: number;
  total_sales_volume: number;
  total_agents: number;
  active_agents: number;
  created_at: string;
}

export interface SellerAgentItem {
  id: number;
  name: string;
  phone: string;
  telegram_handle?: string;
  plan: string;
  status: string;
  plan_expires_at?: string;
  created_at: string;
}

export function SellersAdminView() {
  const [sellers, setSellers] = useState<SellerItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [editingSeller, setEditingSeller] = useState<SellerItem | null>(null);
  const [agentsModalSeller, setAgentsModalSeller] = useState<SellerItem | null>(null);
  const [sellerAgents, setSellerAgents] = useState<SellerAgentItem[]>([]);
  const [loadingAgents, setLoadingAgents] = useState(false);

  // Form State
  const [formName, setFormName] = useState('');
  const [formEmail, setFormEmail] = useState('');
  const [formPhone, setFormPhone] = useState('');
  const [formPassword, setFormPassword] = useState('');
  const [formCompany, setFormCompany] = useState('');
  const [formCommission, setFormCommission] = useState<number>(70);
  const [formRank, setFormRank] = useState('Bronze');
  const [formStatus, setFormStatus] = useState('active');
  const [submitting, setSubmitting] = useState(false);

  const fetchSellers = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get('/sellers');
      setSellers(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Satıcıları yükləmək mümkün olmadı.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSellers();
  }, []);

  const openAddModal = () => {
    setFormName('');
    setFormEmail('');
    setFormPhone('');
    setFormPassword('');
    setFormCompany('');
    setFormCommission(70);
    setFormRank('Bronze');
    setFormStatus('active');
    setIsAddOpen(true);
  };

  const openEditModal = (seller: SellerItem) => {
    setEditingSeller(seller);
    setFormName(seller.name);
    setFormPhone(seller.phone);
    setFormCompany(seller.company_name || '');
    setFormCommission(seller.commission_rate);
    setFormRank(seller.rank);
    setFormStatus(seller.status);
    setFormPassword('');
  };

  const handleCreateSeller = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post('/sellers', {
        name: formName,
        email: formEmail,
        phone: formPhone,
        password: formPassword,
        company_name: formCompany || undefined,
        commission_rate: formCommission,
        rank: formRank
      });
      setIsAddOpen(false);
      fetchSellers();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Xəta baş verdi');
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateSeller = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingSeller) return;
    setSubmitting(true);
    try {
      await api.put(`/sellers/${editingSeller.id}`, {
        name: formName,
        phone: formPhone,
        company_name: formCompany || undefined,
        commission_rate: formCommission,
        rank: formRank,
        status: formStatus,
        password: formPassword || undefined
      });
      setEditingSeller(null);
      fetchSellers();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Xəta baş verdi');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteSeller = async (seller: SellerItem) => {
    if (!window.confirm(`"${seller.name}" satıcısını və hesabını silmək istədiyinizə əminsiniz?`)) return;
    try {
      await api.delete(`/sellers/${seller.id}`);
      fetchSellers();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Silmək mümkün olmadı');
    }
  };

  const openAgentsModal = async (seller: SellerItem) => {
    setAgentsModalSeller(seller);
    setLoadingAgents(true);
    try {
      const res = await api.get(`/sellers/${seller.id}/agents`);
      setSellerAgents(res.data);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Agentləri yükləmək mümkün olmadı');
    } finally {
      setLoadingAgents(false);
    }
  };

  const getRankBadge = (rank: string) => {
    switch (rank) {
      case 'Diamond':
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">💎 Diamond</span>;
      case 'Platinum':
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-purple-500/10 text-purple-400 border border-purple-500/20">💠 Platinum</span>;
      case 'Gold':
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">🥇 Gold</span>;
      case 'Silver':
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-slate-400/10 text-slate-300 border border-slate-400/20">🥈 Silver</span>;
      default:
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-orange-500/10 text-orange-400 border border-orange-500/20">🥉 Bronze</span>;
    }
  };

  const totalSales = sellers.reduce((acc, s) => acc + (s.total_sales_volume || 0), 0);
  const totalSellerEarnings = sellers.reduce((acc, s) => acc + (s.total_earnings || 0), 0);
  const totalAgents = sellers.reduce((acc, s) => acc + (s.total_agents || 0), 0);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900/60 p-6 rounded-2xl border border-slate-800 backdrop-blur-md">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="p-2.5 bg-blue-500/10 border border-blue-500/20 rounded-xl text-blue-400">
              <Store className="w-6 h-6" />
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight">SaaS Satıcılar (Resellers & Franchise)</h1>
          </div>
          <p className="text-slate-400 text-sm">
            Platforma satıcılarını idarə edin, fərdi komissiya faizləri təyin edin və dərəcələri izləyin.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchSellers}
            className="p-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl border border-slate-700 transition"
            title="Yenilə"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={openAddModal}
            className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-medium rounded-xl shadow-lg shadow-blue-500/25 transition"
          >
            <Plus className="w-5 h-5" />
            <span>Yeni Satıcı Əlavə Et</span>
          </button>
        </div>
      </div>

      {/* Overview Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-900/40 p-5 rounded-2xl border border-slate-800 flex items-center gap-4">
          <div className="p-3 bg-blue-500/10 rounded-xl text-blue-400 border border-blue-500/20">
            <Store className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Ümumi Satıcılar</p>
            <p className="text-2xl font-black text-white">{sellers.length}</p>
          </div>
        </div>

        <div className="bg-slate-900/40 p-5 rounded-2xl border border-slate-800 flex items-center gap-4">
          <div className="p-3 bg-indigo-500/10 rounded-xl text-indigo-400 border border-indigo-500/20">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Satıcı Agentləri</p>
            <p className="text-2xl font-black text-indigo-400">{totalAgents}</p>
          </div>
        </div>

        <div className="bg-slate-900/40 p-5 rounded-2xl border border-slate-800 flex items-center gap-4">
          <div className="p-3 bg-emerald-500/10 rounded-xl text-emerald-400 border border-emerald-500/20">
            <DollarSign className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Ümumi Dövriyyə</p>
            <p className="text-2xl font-black text-emerald-400">{totalSales.toLocaleString()} AZN</p>
          </div>
        </div>

        <div className="bg-slate-900/40 p-5 rounded-2xl border border-slate-800 flex items-center gap-4">
          <div className="p-3 bg-amber-500/10 rounded-xl text-amber-400 border border-amber-500/20">
            <Award className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Satıcı Qazancları</p>
            <p className="text-2xl font-black text-amber-400">{totalSellerEarnings.toLocaleString()} AZN</p>
          </div>
        </div>
      </div>

      {/* Sellers List Table */}
      <div className="bg-slate-900/60 rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <span>Satıcılar Siyahısı</span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-300">
              {sellers.length}
            </span>
          </h2>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-400">Yüklənir...</div>
        ) : sellers.length === 0 ? (
          <div className="p-12 text-center text-slate-400">Hələ heç bir satıcı qeydiyyatdan keçməyib.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/40 text-slate-400 text-xs uppercase font-semibold">
                  <th className="py-3.5 px-4">Satıcı / Şirkət</th>
                  <th className="py-3.5 px-4">Əlaqə</th>
                  <th className="py-3.5 px-4">Komissiya %</th>
                  <th className="py-3.5 px-4">Dərəcə</th>
                  <th className="py-3.5 px-4">Agentlər</th>
                  <th className="py-3.5 px-4">Balans / Qazanc</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4 text-right">Əməliyyatlar</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {sellers.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-800/30 transition">
                    <td className="py-4 px-4">
                      <div className="font-semibold text-white">{s.name}</div>
                      {s.company_name && (
                        <div className="text-xs text-slate-400">{s.company_name}</div>
                      )}
                    </td>
                    <td className="py-4 px-4">
                      <div>{s.email}</div>
                      <div className="text-xs text-slate-400">{s.phone}</div>
                    </td>
                    <td className="py-4 px-4">
                      <span className="font-bold text-emerald-400">%{s.commission_rate}</span>
                    </td>
                    <td className="py-4 px-4">
                      {getRankBadge(s.rank)}
                    </td>
                    <td className="py-4 px-4">
                      <button
                        onClick={() => openAgentsModal(s)}
                        className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-blue-400 hover:text-blue-300 rounded-lg text-xs font-semibold transition"
                      >
                        <Users className="w-3.5 h-3.5" />
                        <span>{s.active_agents} / {s.total_agents} Agent</span>
                        <ChevronRight className="w-3 h-3" />
                      </button>
                    </td>
                    <td className="py-4 px-4">
                      <div className="font-bold text-white">{s.balance.toLocaleString()} AZN</div>
                      <div className="text-xs text-slate-400">Cəmi: {s.total_earnings.toLocaleString()} AZN</div>
                    </td>
                    <td className="py-4 px-4">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        s.status === 'active' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}>
                        {s.status === 'active' ? 'Aktiv' : 'Dayandırılıb'}
                      </span>
                    </td>
                    <td className="py-4 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => openEditModal(s)}
                          className="p-1.5 text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition"
                          title="Redaktə et"
                        >
                          <Edit3 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteSeller(s)}
                          className="p-1.5 text-rose-400 hover:text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 rounded-lg transition"
                          title="Sil"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ADD SELLER MODAL */}
      {isAddOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 w-full max-w-md rounded-2xl p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Store className="w-5 h-5 text-blue-400" />
                <span>Yeni Satıcı Qeydiyyatı</span>
              </h3>
              <button onClick={() => setIsAddOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateSeller} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Satıcı / Şəxs Adı *</label>
                <input
                  type="text"
                  required
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="Məs: Elmir Məmmədov"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Şirkət / Agentlik Adı</label>
                <input
                  type="text"
                  value={formCompany}
                  onChange={(e) => setFormCompany(e.target.value)}
                  placeholder="Məs: Baku Real Estate Franchise"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Email (Giriş üçün) *</label>
                  <input
                    type="email"
                    required
                    value={formEmail}
                    onChange={(e) => setFormEmail(e.target.value)}
                    placeholder="seller@domain.az"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Telefon *</label>
                  <input
                    type="text"
                    required
                    value={formPhone}
                    onChange={(e) => setFormPhone(e.target.value)}
                    placeholder="+994501234567"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Şifrə *</label>
                <input
                  type="password"
                  required
                  value={formPassword}
                  onChange={(e) => setFormPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Komissiya Faizi (%) *</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.5"
                    required
                    value={formCommission}
                    onChange={(e) => setFormCommission(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                  <span className="text-[10px] text-slate-500 mt-0.5 block">Satışdan satıcıya qalacaq pay %</span>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Dərəcə (Rank)</label>
                  <select
                    value={formRank}
                    onChange={(e) => setFormRank(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  >
                    <option value="Bronze">🥉 Bronze</option>
                    <option value="Silver">🥈 Silver</option>
                    <option value="Gold">🥇 Gold</option>
                    <option value="Platinum">💠 Platinum</option>
                    <option value="Diamond">💎 Diamond</option>
                  </select>
                </div>
              </div>

              <div className="pt-3 flex gap-3">
                <button
                  type="button"
                  onClick={() => setIsAddOpen(false)}
                  className="w-1/2 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium rounded-xl transition"
                >
                  Ləğv et
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="w-1/2 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold rounded-xl shadow-lg shadow-blue-500/25 transition disabled:opacity-50"
                >
                  {submitting ? 'Yaradılır...' : 'Satıcı Yarat'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* EDIT SELLER MODAL */}
      {editingSeller && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 w-full max-w-md rounded-2xl p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Edit3 className="w-5 h-5 text-blue-400" />
                <span>Satıcını Redaktə Et</span>
              </h3>
              <button onClick={() => setEditingSeller(null)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUpdateSeller} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Satıcı Adı *</label>
                <input
                  type="text"
                  required
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Şirkət / Agentlik</label>
                <input
                  type="text"
                  value={formCompany}
                  onChange={(e) => setFormCompany(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Telefon *</label>
                  <input
                    type="text"
                    required
                    value={formPhone}
                    onChange={(e) => setFormPhone(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Yeni Şifrə (Dəyişmək üçün)</label>
                  <input
                    type="password"
                    value={formPassword}
                    onChange={(e) => setFormPassword(e.target.value)}
                    placeholder="Boş buraxın"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Komissiya %</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.5"
                    required
                    value={formCommission}
                    onChange={(e) => setFormCommission(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Dərəcə</label>
                  <select
                    value={formRank}
                    onChange={(e) => setFormRank(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  >
                    <option value="Bronze">Bronze</option>
                    <option value="Silver">Silver</option>
                    <option value="Gold">Gold</option>
                    <option value="Platinum">Platinum</option>
                    <option value="Diamond">Diamond</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Status</label>
                  <select
                    value={formStatus}
                    onChange={(e) => setFormStatus(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  >
                    <option value="active">Aktiv</option>
                    <option value="suspended">Dayandırılıb</option>
                  </select>
                </div>
              </div>

              <div className="pt-3 flex gap-3">
                <button
                  type="button"
                  onClick={() => setEditingSeller(null)}
                  className="w-1/2 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium rounded-xl transition"
                >
                  Ləğv et
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="w-1/2 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold rounded-xl shadow-lg shadow-blue-500/25 transition disabled:opacity-50"
                >
                  {submitting ? 'Saxlanılır...' : 'Yadda Saxla'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* SELLER AGENTS MODAL */}
      {agentsModalSeller && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 w-full max-w-2xl rounded-2xl p-6 shadow-2xl space-y-5 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Users className="w-5 h-5 text-blue-400" />
                  <span>{agentsModalSeller.name} — Agentləri</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Bu satıcıya bağlı qeydiyyatdan keçmiş agentlərin siyahısı
                </p>
              </div>
              <button onClick={() => setAgentsModalSeller(null)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="overflow-y-auto flex-1">
              {loadingAgents ? (
                <div className="p-8 text-center text-slate-400">Yüklənir...</div>
              ) : sellerAgents.length === 0 ? (
                <div className="p-8 text-center text-slate-400">Bu satıcıya bağlı hələ heç bir agent yoxdur.</div>
              ) : (
                <table className="w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 text-xs uppercase font-semibold">
                      <th className="py-2.5 px-3">Agent</th>
                      <th className="py-2.5 px-3">Əlaqə</th>
                      <th className="py-2.5 px-3">Paket</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3">Bitmə Vaxtı</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/40 text-slate-300">
                    {sellerAgents.map((a) => (
                      <tr key={a.id} className="hover:bg-slate-800/20">
                        <td className="py-3 px-3 font-medium text-white">{a.name}</td>
                        <td className="py-3 px-3 text-xs">
                          <div>{a.phone}</div>
                          {a.telegram_handle && <div className="text-blue-400">@{a.telegram_handle}</div>}
                        </td>
                        <td className="py-3 px-3 text-xs font-semibold text-emerald-400">{a.plan}</td>
                        <td className="py-3 px-3">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                            a.status === 'active' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-500/10 text-slate-400'
                          }`}>
                            {a.status === 'active' ? 'Aktiv' : a.status}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-xs text-slate-400">
                          {a.plan_expires_at ? new Date(a.plan_expires_at).toLocaleDateString('az-AZ') : 'Limitsiz'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div className="pt-3 border-t border-slate-800 text-right">
              <button
                onClick={() => setAgentsModalSeller(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm font-medium transition"
              >
                Bağla
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
