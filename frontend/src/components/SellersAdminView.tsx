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
  bonus_commission?: number;
  effective_commission_rate?: number;
  rank: string;
  rank_label?: string;
  rank_emoji?: string;
  status: string;
  balance: number;
  total_earnings: number;
  total_sales_volume: number;
  total_platform_fee?: number;
  platform_fee_settled?: number;
  pending_platform_debt?: number;
  total_agents: number;
  active_agents: number;
  custom_domain?: string;
  custom_domain_enabled?: boolean;
  rank_allows_domain?: boolean;
  domain_status?: string;
  custom_brand_title?: string;
  custom_brand_logo?: string;
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

export interface AdminPayoutItem {
  id: number;
  seller_id: number;
  seller_name: string;
  seller_company?: string;
  seller_phone?: string;
  seller_balance: number;
  amount: number;
  card_number: string;
  card_holder_name: string;
  iban?: string;
  status: string;
  notes?: string;
  admin_notes?: string;
  created_at: string;
  processed_at?: string;
}

export function SellersAdminView() {
  const [activeTab, setActiveTab] = useState<'sellers' | 'payouts'>('sellers');
  const [sellers, setSellers] = useState<SellerItem[]>([]);
  const [payouts, setPayouts] = useState<AdminPayoutItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [editingSeller, setEditingSeller] = useState<SellerItem | null>(null);
  const [agentsModalSeller, setAgentsModalSeller] = useState<SellerItem | null>(null);
  const [sellerAgents, setSellerAgents] = useState<SellerAgentItem[]>([]);
  const [loadingAgents, setLoadingAgents] = useState(false);

  // Cash Settlement Modal State
  const [settleModalSeller, setSettleModalSeller] = useState<SellerItem | null>(null);
  const [settleAmount, setSettleAmount] = useState<number>(0);
  const [settleNotes, setSettleNotes] = useState<string>('');
  const [settling, setSettling] = useState(false);

  // Form State
  const [formName, setFormName] = useState('');
  const [formEmail, setFormEmail] = useState('');
  const [formPhone, setFormPhone] = useState('');
  const [formPassword, setFormPassword] = useState('');
  const [formCompany, setFormCompany] = useState('');
  const [formCommission, setFormCommission] = useState<number>(70);
  const [formRank, setFormRank] = useState('Bronze');
  const [formStatus, setFormStatus] = useState('active');
  const [formCustomDomain, setFormCustomDomain] = useState('');
  const [formCustomDomainEnabled, setFormCustomDomainEnabled] = useState(false);
  const [formDomainStatus, setFormDomainStatus] = useState('disabled');
  const [formBrandTitle, setFormBrandTitle] = useState('');
  const [formBrandLogo, setFormBrandLogo] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const fetchSellers = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sRes, pRes] = await Promise.all([
        api.get('/sellers'),
        api.get('/sellers/admin/payouts').catch(() => ({ data: [] }))
      ]);
      setSellers(sRes.data);
      setPayouts(pRes.data || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Satıcıları yükləmək mümkün olmadı.');
    } finally {
      setLoading(false);
    }
  };

  const handlePayoutAction = async (payoutId: number, action: 'approve' | 'reject') => {
    let adminNotes = '';
    if (action === 'reject') {
      const reason = prompt('İmtina səbəbini daxil edin:');
      if (reason === null) return;
      adminNotes = reason;
    }
    try {
      await api.post(`/sellers/admin/payouts/${payoutId}/action`, {
        action: action === 'approve' ? 'pay' : 'reject',
        admin_notes: adminNotes || undefined
      });
      alert(action === 'approve' ? 'Çıxarış təsdiqləndi və satıcı balansından çıxıldı!' : 'Çıxarış tələbi imtina edildi.');
      fetchSellers();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Xəta baş verdi.');
    }
  };

  const handleSettleCash = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!settleModalSeller || settleAmount <= 0) return;
    setSettling(true);
    try {
      await api.post(`/sellers/${settleModalSeller.id}/settle-cash`, {
        amount: settleAmount,
        notes: settleNotes || undefined
      });
      alert('Nağd hesablaşma uğurla qeydə alındı!');
      setSettleModalSeller(null);
      fetchSellers();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Hesablaşma zamanı xəta baş verdi.');
    } finally {
      setSettling(false);
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
    setFormCustomDomain('');
    setFormCustomDomainEnabled(false);
    setFormDomainStatus('disabled');
    setFormBrandTitle('');
    setFormBrandLogo('');
    setIsAddOpen(true);
  };

  const openEditModal = (seller: SellerItem) => {
    setEditingSeller(seller);
    setFormName(seller.name);
    setFormEmail(seller.email);
    setFormPhone(seller.phone);
    setFormCompany(seller.company_name || '');
    setFormCommission(seller.commission_rate);
    setFormRank(seller.rank);
    setFormStatus(seller.status);
    setFormCustomDomain(seller.custom_domain || '');
    const isHighRank = ['Gold', 'Platinum', 'Diamond'].includes(seller.rank);
    setFormCustomDomainEnabled(seller.custom_domain_enabled || isHighRank);
    setFormDomainStatus(seller.domain_status && seller.domain_status !== 'disabled' ? seller.domain_status : (seller.custom_domain ? 'active' : (isHighRank ? 'active' : 'disabled')));
    setFormBrandTitle(seller.custom_brand_title || '');
    setFormBrandLogo(seller.custom_brand_logo || '');
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
        rank: formRank,
        custom_domain: formCustomDomain || undefined,
        custom_domain_enabled: formCustomDomainEnabled,
        custom_brand_title: formBrandTitle || undefined,
        custom_brand_logo: formBrandLogo || undefined
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
        email: formEmail,
        phone: formPhone,
        company_name: formCompany || undefined,
        commission_rate: formCommission,
        rank: formRank,
        status: formStatus,
        password: formPassword || undefined,
        custom_domain: formCustomDomain || undefined,
        custom_domain_enabled: formCustomDomainEnabled,
        domain_status: formDomainStatus,
        custom_brand_title: formBrandTitle || undefined,
        custom_brand_logo: formBrandLogo || undefined
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
  const totalPlatformFee = sellers.reduce((acc, s) => acc + (s.total_platform_fee ?? ((s.total_sales_volume || 0) - (s.total_earnings || 0))), 0);
  const totalPendingDebt = sellers.reduce((acc, s) => acc + (s.pending_platform_debt || 0), 0);
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
            Platforma satıcılarını idarə edin, fərdi komissiya faizləri təyin edin və nağd hesablaşmaları izləyin.
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
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
        <div className="bg-slate-900/40 p-4 rounded-2xl border border-slate-800 flex items-center gap-3">
          <div className="p-2.5 bg-blue-500/10 rounded-xl text-blue-400 border border-blue-500/20">
            <Store className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Ümumi Satıcılar</p>
            <p className="text-xl font-black text-white">{sellers.length}</p>
          </div>
        </div>

        <div className="bg-slate-900/40 p-4 rounded-2xl border border-slate-800 flex items-center gap-3">
          <div className="p-2.5 bg-indigo-500/10 rounded-xl text-indigo-400 border border-indigo-500/20">
            <Users className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Satıcı Agentləri</p>
            <p className="text-xl font-black text-indigo-400">{totalAgents}</p>
          </div>
        </div>

        <div className="bg-slate-900/40 p-4 rounded-2xl border border-slate-800 flex items-center gap-3">
          <div className="p-2.5 bg-emerald-500/10 rounded-xl text-emerald-400 border border-emerald-500/20">
            <DollarSign className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Nağd Satış Yığımı</p>
            <p className="text-xl font-black text-emerald-400">{totalSales.toLocaleString()} AZN</p>
          </div>
        </div>

        <div className="bg-slate-900/40 p-4 rounded-2xl border border-slate-800 flex items-center gap-3">
          <div className="p-2.5 bg-amber-500/10 rounded-xl text-amber-400 border border-amber-500/20">
            <Award className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Satıcıların Qazancı</p>
            <p className="text-xl font-black text-amber-400">{totalSellerEarnings.toLocaleString()} AZN</p>
          </div>
        </div>

        <div className="bg-slate-900/40 p-4 rounded-2xl border border-cyan-500/30 flex items-center gap-3 shadow-lg shadow-cyan-500/5">
          <div className="p-2.5 bg-cyan-500/10 rounded-xl text-cyan-400 border border-cyan-500/20">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Adminə Çatacaq Pay</p>
            <p className="text-xl font-black text-cyan-400">
              {totalPendingDebt > 0 ? `${totalPendingDebt.toLocaleString()} AZN` : '0 AZN (Tam Təhvil)'}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex gap-2 p-1.5 bg-slate-900/80 rounded-2xl border border-slate-800 w-fit">
        <button
          onClick={() => setActiveTab('sellers')}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs transition ${
            activeTab === 'sellers'
              ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-500/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
          }`}
        >
          <Store className="w-4 h-4" />
          <span>Satıcılar ({sellers.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('payouts')}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs transition ${
            activeTab === 'payouts'
              ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-lg shadow-emerald-500/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
          }`}
        >
          <span>🏧</span>
          <span>Bank Çıxarış Tələbləri ({payouts.filter(p => p.status === 'pending').length} gözləyir)</span>
        </button>
      </div>

      {/* TAB 1: SELLERS LIST */}
      {activeTab === 'sellers' && (
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
                    <th className="py-3.5 px-4">Fərdi Domen</th>
                    <th className="py-3.5 px-4">Əlaqə</th>
                    <th className="py-3.5 px-4">Komissiya %</th>
                    <th className="py-3.5 px-4">Dərəcə</th>
                    <th className="py-3.5 px-4">Agentlər</th>
                    <th className="py-3.5 px-4">Nağd Satış / Qazanc</th>
                    <th className="py-3.5 px-4">Admin Payı (Borc)</th>
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
                        {s.custom_domain ? (
                          <div>
                            <div className="text-xs font-mono text-cyan-400 font-semibold flex items-center gap-1">
                              <span>🌐 {s.custom_domain}</span>
                            </div>
                            <span className={`inline-flex items-center text-[10px] mt-0.5 font-medium px-1.5 py-0.5 rounded ${
                              s.domain_status === 'active' 
                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                                : s.domain_status === 'pending_dns'
                                ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                : 'bg-slate-800 text-slate-400 border border-slate-700'
                            }`}>
                              {s.domain_status === 'active' ? '🟢 Aktiv' : s.domain_status === 'pending_dns' ? '🟡 DNS Gözlənilir' : '🔴 Deaktiv'}
                            </span>
                          </div>
                        ) : (
                          <div>
                            {s.rank_allows_domain || s.custom_domain_enabled || ['Gold', 'Platinum', 'Diamond'].includes(s.rank) ? (
                              <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-lg border border-emerald-500/20">
                                <span>✨ İcazə Verilib</span>
                                <span className="text-[9px] text-emerald-300 font-normal">({s.rank})</span>
                              </span>
                            ) : (
                              <span className="inline-flex items-center text-[10px] text-slate-500 bg-slate-800/50 px-2 py-0.5 rounded">
                                ⚪ İcazə Yoxdur
                              </span>
                            )}
                          </div>
                        )}
                      </td>
                      <td className="py-4 px-4">
                        <div>{s.email}</div>
                        <div className="text-xs text-slate-400">{s.phone}</div>
                      </td>
                      <td className="py-4 px-4">
                        <div className="font-bold text-emerald-400">%{s.commission_rate}</div>
                        {s.bonus_commission && s.bonus_commission > 0 ? (
                          <div className="text-[10px] text-amber-400 font-bold">
                            +{s.bonus_commission}% Rank Bonusu (%{s.effective_commission_rate})
                          </div>
                        ) : null}
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
                        <div className="font-bold text-emerald-400">Qazanc: {s.total_earnings?.toLocaleString() || 0} AZN</div>
                        <div className="text-xs text-slate-400">Nağd Satış: {s.total_sales_volume?.toLocaleString() || 0} AZN</div>
                      </td>
                      <td className="py-4 px-4">
                        {(s.pending_platform_debt || 0) > 0 ? (
                          <div>
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                              🔴 {s.pending_platform_debt?.toLocaleString()} AZN gözləyir
                            </span>
                            <div className="text-[10px] text-slate-500 mt-0.5">
                              Təhvil verilən: {s.platform_fee_settled || 0} AZN
                            </div>
                          </div>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            🟢 Borc yoxdur
                          </span>
                        )}
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
                            onClick={() => {
                              setSettleModalSeller(s);
                              setSettleAmount(s.pending_platform_debt || 0);
                              setSettleNotes('');
                            }}
                            className="px-2.5 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 rounded-lg text-xs font-bold transition flex items-center gap-1"
                            title="Nağd Platforma Haqqını Təhvil Al"
                          >
                            <span>💵</span>
                            <span>Təhvil Al</span>
                          </button>
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
      )}

      {/* TAB 2: PAYOUT REQUESTS LIST */}
      {activeTab === 'payouts' && (
        <div className="bg-slate-900/60 rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
          <div className="p-5 border-b border-slate-800 flex items-center justify-between">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <span>🏧</span>
              <span>Satıcıların Pul Çıxarış Tələbləri</span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-300">
                {payouts.length}
              </span>
            </h2>
          </div>

          {loading ? (
            <div className="p-12 text-center text-slate-400">Yüklənir...</div>
          ) : payouts.length === 0 ? (
            <div className="p-12 text-center text-slate-400">Hələ heç bir çıxarış tələbi yoxdur.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-950/40 text-slate-400 text-xs uppercase font-semibold">
                    <th className="py-3.5 px-4">Satıcı / Şirkət</th>
                    <th className="py-3.5 px-4">Çıxarış Məbləği</th>
                    <th className="py-3.5 px-4">Bank Kartı</th>
                    <th className="py-3.5 px-4">Kart Sahibi</th>
                    <th className="py-3.5 px-4">Mövcud Balans</th>
                    <th className="py-3.5 px-4">Status</th>
                    <th className="py-3.5 px-4">Tarix</th>
                    <th className="py-3.5 px-4 text-right">Əməliyyatlar</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {payouts.map((p) => (
                    <tr key={p.id} className="hover:bg-slate-800/30 transition">
                      <td className="py-4 px-4">
                        <div className="font-semibold text-white">{p.seller_name}</div>
                        {p.seller_company && <div className="text-xs text-slate-400">{p.seller_company}</div>}
                        {p.seller_phone && <div className="text-[11px] text-slate-500 font-mono">{p.seller_phone}</div>}
                      </td>
                      <td className="py-4 px-4 font-black text-emerald-400 text-base">
                        {p.amount.toLocaleString()} AZN
                      </td>
                      <td className="py-4 px-4 font-mono font-bold text-cyan-300">
                        {p.card_number}
                        {p.iban && <div className="text-[10px] text-slate-400 font-normal">{p.iban}</div>}
                      </td>
                      <td className="py-4 px-4 font-medium text-white">{p.card_holder_name}</td>
                      <td className="py-4 px-4 text-xs font-semibold text-slate-300">
                        {p.seller_balance?.toLocaleString()} AZN
                      </td>
                      <td className="py-4 px-4">
                        {p.status === 'paid' && (
                          <span className="px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold text-xs">
                            🟢 Ödənildi
                          </span>
                        )}
                        {p.status === 'pending' && (
                          <span className="px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 font-semibold text-xs">
                            🟡 Gözləmədə
                          </span>
                        )}
                        {p.status === 'rejected' && (
                          <span className="px-2.5 py-1 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 font-semibold text-xs">
                            🔴 İmtina edildi
                          </span>
                        )}
                      </td>
                      <td className="py-4 px-4 text-xs text-slate-500">
                        {new Date(p.created_at).toLocaleString('az-AZ')}
                      </td>
                      <td className="py-4 px-4 text-right">
                        {p.status === 'pending' ? (
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => handlePayoutAction(p.id, 'approve')}
                              className="px-3 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 rounded-xl text-xs font-bold transition"
                            >
                              Təsdiqlə və Ödə
                            </button>
                            <button
                              onClick={() => handlePayoutAction(p.id, 'reject')}
                              className="px-3 py-1.5 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 rounded-xl text-xs font-bold transition"
                            >
                              İmtina
                            </button>
                          </div>
                        ) : (
                          <span className="text-xs text-slate-500 italic">{p.admin_notes || 'Tamamlandı'}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

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
                    onChange={(e) => {
                      const newRank = e.target.value;
                      setFormRank(newRank);
                      if (['Gold', 'Platinum', 'Diamond'].includes(newRank)) {
                        setFormCustomDomainEnabled(true);
                      }
                    }}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  >
                    <option value="Bronze">🥉 Bronze</option>
                    <option value="Silver">🥈 Silver (+3% Bonus)</option>
                    <option value="Gold">🥇 Gold (+5% Bonus & Domen)</option>
                    <option value="Platinum">💠 Platinum (+8% Bonus & Domen)</option>
                    <option value="Diamond">💎 Diamond (+10% Bonus & Domen)</option>
                  </select>
                </div>
              </div>

              {['Gold', 'Platinum', 'Diamond'].includes(formRank) && (
                <div className="text-[11px] text-emerald-400 bg-emerald-500/10 p-2.5 rounded-xl border border-emerald-500/20 flex items-center gap-2">
                  <span>💎</span>
                  <span><strong>{formRank} Səviyyəsi:</strong> Fərdi Domen (White-label) səlahiyyəti avtomatik olaraq bu satıcı üçün aktivdir.</span>
                </div>
              )}

              <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-3">
                <div className="text-xs font-bold text-cyan-400 flex items-center gap-1.5">
                  <span>🌐</span>
                  <span>Fərdi Domen və White-label Brend (Könüllü)</span>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Fərdi Domen</label>
                  <input
                    type="text"
                    value={formCustomDomain}
                    onChange={(e) => setFormCustomDomain(e.target.value)}
                    placeholder="agent.bakuemlak.az"
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 text-white text-xs font-mono focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 mb-1">Fərdi Brend Başlığı</label>
                    <input
                      type="text"
                      value={formBrandTitle}
                      onChange={(e) => setFormBrandTitle(e.target.value)}
                      placeholder="Baku Emlak Portalı"
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 text-white text-xs focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 mb-1">Fərdi Loqo URL</label>
                    <input
                      type="text"
                      value={formBrandLogo}
                      onChange={(e) => setFormBrandLogo(e.target.value)}
                      placeholder="https://..."
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 text-white text-xs focus:outline-none focus:border-cyan-500"
                    />
                  </div>
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
          <div className="bg-slate-900 border border-slate-800 w-full max-w-md rounded-2xl p-6 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto">
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
              <div className="grid grid-cols-2 gap-3">
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
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Giriş Emaili (Login) *</label>
                  <input
                    type="email"
                    required
                    value={formEmail}
                    onChange={(e) => setFormEmail(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
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
                    onChange={(e) => {
                      const newRank = e.target.value;
                      setFormRank(newRank);
                      if (['Gold', 'Platinum', 'Diamond'].includes(newRank)) {
                        setFormCustomDomainEnabled(true);
                        if (formDomainStatus === 'disabled') {
                          setFormDomainStatus('active');
                        }
                      }
                    }}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  >
                    <option value="Bronze">🥉 Bronze</option>
                    <option value="Silver">🥈 Silver (+3% Bonus)</option>
                    <option value="Gold">🥇 Gold (+5% Bonus & Domen)</option>
                    <option value="Platinum">💠 Platinum (+8% Bonus & Domen)</option>
                    <option value="Diamond">💎 Diamond (+10% Bonus & Domen)</option>
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

              {['Gold', 'Platinum', 'Diamond'].includes(formRank) && (
                <div className="text-[11px] text-emerald-400 bg-emerald-500/10 p-2.5 rounded-xl border border-emerald-500/20 flex items-center gap-2">
                  <span>💎</span>
                  <span><strong>{formRank} Səviyyəsi:</strong> Fərdi Domen (White-label) səlahiyyəti avtomatik olaraq bu satıcı üçün aktivdir.</span>
                </div>
              )}

              <div className="p-3.5 bg-slate-950/60 border border-slate-800 rounded-xl space-y-3">
                <div className="text-xs font-bold text-cyan-400 flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <span>🌐</span>
                    <span>Fərdi Domen (White-label) İdarəsi</span>
                  </span>
                  <label className="flex items-center gap-1.5 text-xs text-slate-300 font-normal cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formCustomDomainEnabled || ['Gold', 'Platinum', 'Diamond'].includes(formRank)}
                      onChange={(e) => setFormCustomDomainEnabled(e.target.checked)}
                      className="rounded bg-slate-900 border-slate-700 text-cyan-500"
                    />
                    <span>İcazə Verilib</span>
                  </label>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 mb-1">Fərdi Domen</label>
                    <input
                      type="text"
                      value={formCustomDomain}
                      onChange={(e) => setFormCustomDomain(e.target.value)}
                      placeholder="agent.bakuemlak.az"
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 text-white text-xs font-mono focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 mb-1">Domen Statusu</label>
                    <select
                      value={formDomainStatus}
                      onChange={(e) => setFormDomainStatus(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-2 py-1.5 text-white text-xs focus:outline-none focus:border-cyan-500"
                    >
                      <option value="disabled">Deaktiv</option>
                      <option value="pending_dns">DNS Gözlənilir</option>
                      <option value="active">Aktiv (DNS Təsdiqlənib)</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 mb-1">Fərdi Brend Başlığı</label>
                    <input
                      type="text"
                      value={formBrandTitle}
                      onChange={(e) => setFormBrandTitle(e.target.value)}
                      placeholder="Baku Emlak Portalı"
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 text-white text-xs focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 mb-1">Fərdi Loqo URL</label>
                    <input
                      type="text"
                      value={formBrandLogo}
                      onChange={(e) => setFormBrandLogo(e.target.value)}
                      placeholder="https://..."
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 text-white text-xs focus:outline-none focus:border-cyan-500"
                    />
                  </div>
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

      {/* CASH SETTLEMENT MODAL (Admin collects cash platform share from seller) */}
      {settleModalSeller && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 w-full max-w-md rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <span>💵</span>
                <span>Nağd Platforma Haqqını Təhvil Al</span>
              </h3>
              <button onClick={() => setSettleModalSeller(null)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-3.5 bg-slate-950/70 border border-slate-800 rounded-xl space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">Satıcı:</span>
                <span className="font-bold text-white">{settleModalSeller.name} ({settleModalSeller.company_name || 'Fərdi'})</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Telefon:</span>
                <span className="text-slate-300 font-mono">{settleModalSeller.phone}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Məcmu Nağd Satış:</span>
                <span className="text-slate-300">{settleModalSeller.total_sales_volume?.toLocaleString() || 0} AZN</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Satıcının Qazancı:</span>
                <span className="text-emerald-400 font-bold">{settleModalSeller.total_earnings?.toLocaleString() || 0} AZN</span>
              </div>
              <div className="flex justify-between pt-1 border-t border-slate-800 text-sm">
                <span className="text-cyan-300 font-bold">Adminə Qalan Borc Pay:</span>
                <span className="text-rose-400 font-black">
                  {settleModalSeller.pending_platform_debt?.toLocaleString() || 0} AZN
                </span>
              </div>
            </div>

            <form onSubmit={handleSettleCash} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Təhvil Alınan Məbləğ (AZN) *
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  required
                  value={settleAmount || ''}
                  onChange={(e) => setSettleAmount(parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white font-black text-base focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Qeyd / Təhvil Təsviri (İstəyə bağlı)
                </label>
                <textarea
                  rows={2}
                  placeholder="Məs: Ofisdə nağd qəbul edildi və ya BirBank köçürməsi"
                  value={settleNotes}
                  onChange={(e) => setSettleNotes(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-xs focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setSettleModalSeller(null)}
                  className="w-1/2 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium rounded-xl text-xs transition"
                >
                  Ləğv et
                </button>
                <button
                  type="submit"
                  disabled={settling || settleAmount <= 0}
                  className="w-1/2 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold rounded-xl text-xs shadow-lg shadow-emerald-600/25 transition disabled:opacity-50"
                >
                  {settling ? 'Qeydə alınır...' : 'Təsdiqlə və Qeydə Al'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
