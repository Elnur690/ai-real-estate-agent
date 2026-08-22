import React, { useEffect, useState } from 'react';
import { 
  Store, Users, Package, DollarSign, Award, Plus, Edit3, Trash2, CheckCircle, 
  AlertTriangle, RefreshCw, X, Shield, Phone, Send, Sparkles, Check, ChevronRight, TrendingUp
} from 'lucide-react';
import api from '../api';

export interface SellerDashboardData {
  seller_id: number;
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
  total_packages: number;
  min_package_price?: number;
  max_trial_days?: number;
}

export interface SellerAgent {
  id: number;
  name: string;
  phone: string;
  telegram_handle?: string;
  whatsapp_number?: string;
  preferred_channel: string;
  plan: string;
  status: string;
  plan_expires_at?: string;
  created_at: string;
}

export interface SellerPackageItem {
  id: number;
  name: string;
  description?: string;
  price: number;
  period: string;
  duration_days: number;
  max_searches: number;
  max_locations: number;
  feature_makler_detector: boolean;
  feature_avm_bargain_finder: boolean;
  feature_b2b_cobrokering: boolean;
  feature_backup_service: boolean;
  is_active: boolean;
}

export interface SellerTransactionItem {
  id: number;
  amount: number;
  commission_rate: number;
  seller_profit: number;
  platform_fee: number;
  type: string;
  description?: string;
  created_at: string;
}

export function SellerPortalView() {
  const [activeTab, setActiveTab] = useState<'agents' | 'packages' | 'earnings'>('agents');
  const [dashboard, setDashboard] = useState<SellerDashboardData | null>(null);
  const [agents, setAgents] = useState<SellerAgent[]>([]);
  const [packages, setPackages] = useState<SellerPackageItem[]>([]);
  const [earnings, setEarnings] = useState<{ balance: number; total_earnings: number; transactions: SellerTransactionItem[] } | null>(null);
  const [loading, setLoading] = useState(true);

  // Agent Modal State
  const [isAddAgentOpen, setIsAddAgentOpen] = useState(false);
  const [agentName, setAgentName] = useState('');
  const [agentPhone, setAgentPhone] = useState('');
  const [agentTg, setAgentTg] = useState('');
  const [agentWhatsapp, setAgentWhatsapp] = useState('');
  const [agentChannel, setAgentChannel] = useState('telegram');
  const [agentPkgId, setAgentPkgId] = useState<number | undefined>(undefined);
  const [agentError, setAgentError] = useState<string | null>(null);
  const [submittingAgent, setSubmittingAgent] = useState(false);

  // Package Modal State
  const [isAddPkgOpen, setIsAddPkgOpen] = useState(false);
  const [editingPkg, setEditingPkg] = useState<SellerPackageItem | null>(null);
  const [pkgName, setPkgName] = useState('');
  const [pkgPrice, setPkgPrice] = useState<number>(49);
  const [pkgDescription, setPkgDescription] = useState('');
  const [pkgPeriod, setPkgPeriod] = useState('monthly');
  const [pkgDuration, setPkgDuration] = useState<number>(30);
  const [pkgMaxSearches, setPkgMaxSearches] = useState<number>(5);
  const [pkgMakler, setPkgMakler] = useState(true);
  const [pkgAvm, setPkgAvm] = useState(true);
  const [pkgB2b, setPkgB2b] = useState(false);
  const [pkgBackup, setPkgBackup] = useState(false);
  const [submittingPkg, setSubmittingPkg] = useState(false);

  const fetchDashboard = async () => {
    try {
      const res = await api.get('/sellers/me/dashboard');
      setDashboard(res.data);
    } catch (err) {
      console.error('Error fetching seller dashboard:', err);
    }
  };

  const fetchAgents = async () => {
    try {
      const res = await api.get('/sellers/me/agents');
      setAgents(res.data);
    } catch (err) {
      console.error('Error fetching seller agents:', err);
    }
  };

  const fetchPackages = async () => {
    try {
      const res = await api.get('/sellers/me/packages');
      setPackages(res.data);
      if (res.data.length > 0 && !agentPkgId) {
        setAgentPkgId(res.data[0].id);
      }
    } catch (err) {
      console.error('Error fetching seller packages:', err);
    }
  };

  const fetchEarnings = async () => {
    try {
      const res = await api.get('/sellers/me/earnings');
      setEarnings(res.data);
    } catch (err) {
      console.error('Error fetching earnings:', err);
    }
  };

  const reloadAll = async () => {
    setLoading(true);
    await Promise.all([fetchDashboard(), fetchAgents(), fetchPackages(), fetchEarnings()]);
    setLoading(false);
  };

  useEffect(() => {
    reloadAll();
  }, []);

  const handleRegisterAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    setAgentError(null);
    setSubmittingAgent(true);
    try {
      await api.post('/sellers/me/agents', {
        name: agentName,
        phone: agentPhone,
        telegram_handle: agentTg || undefined,
        whatsapp_number: agentWhatsapp || undefined,
        preferred_channel: agentChannel,
        package_id: agentPkgId
      });
      setIsAddAgentOpen(false);
      setAgentName('');
      setAgentPhone('');
      setAgentTg('');
      setAgentWhatsapp('');
      reloadAll();
    } catch (err: any) {
      setAgentError(err.response?.data?.detail || 'Xəta baş verdi');
    } finally {
      setSubmittingAgent(false);
    }
  };

  const handleSavePackage = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingPkg(true);
    try {
      if (editingPkg) {
        await api.put(`/sellers/me/packages/${editingPkg.id}`, {
          name: pkgName,
          price: pkgPrice,
          description: pkgDescription || undefined,
          period: pkgPeriod,
          duration_days: pkgDuration,
          max_searches: pkgMaxSearches,
          feature_makler_detector: pkgMakler,
          feature_avm_bargain_finder: pkgAvm,
          feature_b2b_cobrokering: pkgB2b,
          feature_backup_service: pkgBackup
        });
      } else {
        await api.post('/sellers/me/packages', {
          name: pkgName,
          price: pkgPrice,
          description: pkgDescription || undefined,
          period: pkgPeriod,
          duration_days: pkgDuration,
          max_searches: pkgMaxSearches,
          feature_makler_detector: pkgMakler,
          feature_avm_bargain_finder: pkgAvm,
          feature_b2b_cobrokering: pkgB2b,
          feature_backup_service: pkgBackup
        });
      }
      setIsAddPkgOpen(false);
      setEditingPkg(null);
      fetchPackages();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Xəta baş verdi');
    } finally {
      setSubmittingPkg(false);
    }
  };

  const handleDeletePackage = async (pkg: SellerPackageItem) => {
    if (!window.confirm(`"${pkg.name}" paketini silmək istədiyinizə əminsiniz?`)) return;
    try {
      await api.delete(`/sellers/me/packages/${pkg.id}`);
      fetchPackages();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Paketi silmək mümkün olmadı');
    }
  };

  const openAddPkgModal = () => {
    setEditingPkg(null);
    setPkgName('');
    setPkgPrice(49);
    setPkgDescription('');
    setPkgPeriod('monthly');
    setPkgDuration(30);
    setPkgMaxSearches(5);
    setPkgMakler(true);
    setPkgAvm(true);
    setPkgB2b(false);
    setPkgBackup(false);
    setIsAddPkgOpen(true);
  };

  const openEditPkgModal = (pkg: SellerPackageItem) => {
    setEditingPkg(pkg);
    setPkgName(pkg.name);
    setPkgPrice(pkg.price);
    setPkgDescription(pkg.description || '');
    setPkgPeriod(pkg.period);
    setPkgDuration(pkg.duration_days);
    setPkgMaxSearches(pkg.max_searches);
    setPkgMakler(pkg.feature_makler_detector);
    setPkgAvm(pkg.feature_avm_bargain_finder);
    setPkgB2b(pkg.feature_b2b_cobrokering);
    setPkgBackup(pkg.feature_backup_service);
    setIsAddPkgOpen(true);
  };

  const getRankBadge = (rank: string) => {
    switch (rank) {
      case 'Diamond':
        return <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-lg shadow-cyan-500/10">💎 Diamond Seller</span>;
      case 'Platinum':
        return <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black bg-purple-500/10 text-purple-400 border border-purple-500/30 shadow-lg shadow-purple-500/10">💠 Platinum Seller</span>;
      case 'Gold':
        return <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black bg-amber-500/10 text-amber-400 border border-amber-500/30 shadow-lg shadow-amber-500/10">🥇 Gold Seller</span>;
      case 'Silver':
        return <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black bg-slate-400/10 text-slate-300 border border-slate-400/30">🥈 Silver Seller</span>;
      default:
        return <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black bg-orange-500/10 text-orange-400 border border-orange-500/30">🥉 Bronze Seller</span>;
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 p-6 rounded-3xl border border-slate-800 backdrop-blur-md shadow-2xl relative overflow-hidden">
        <div className="absolute right-0 top-0 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl pointer-events-none" />
        
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
                Xoş gəlmisiniz, {dashboard?.name || 'Satıcı'}!
              </h1>
              {dashboard && getRankBadge(dashboard.rank)}
            </div>
            <p className="text-slate-400 text-sm max-w-xl">
              Fərdi reseller portalınızda öz paketlərinizi yaradın, agentlərinizi idarə edin və qazanclarınızı izləyin.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={reloadAll}
              className="p-3 bg-slate-800/80 hover:bg-slate-700 text-slate-300 rounded-2xl border border-slate-700 transition"
              title="Yenilə"
            >
              <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={() => { setAgentError(null); setIsAddAgentOpen(true); }}
              className="flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-bold rounded-2xl shadow-xl shadow-indigo-500/25 transition transform active:scale-95"
            >
              <Plus className="w-5 h-5" />
              <span>Yeni Agent Qeydiyyatı</span>
            </button>
          </div>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800/80">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Mövcud Balans</span>
            <div className="p-2 bg-emerald-500/10 rounded-xl text-emerald-400 border border-emerald-500/20">
              <DollarSign className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-black text-emerald-400">
            {dashboard?.balance.toLocaleString() || 0} <span className="text-sm font-bold text-emerald-500/70">AZN</span>
          </p>
        </div>

        <div className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800/80">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Cəmi Xalis Qazanc</span>
            <div className="p-2 bg-blue-500/10 rounded-xl text-blue-400 border border-blue-500/20">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-black text-blue-400">
            {dashboard?.total_earnings.toLocaleString() || 0} <span className="text-sm font-bold text-blue-500/70">AZN</span>
          </p>
        </div>

        <div className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800/80">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Komissiya Faiziniz</span>
            <div className="p-2 bg-indigo-500/10 rounded-xl text-indigo-400 border border-indigo-500/20">
              <Award className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-black text-indigo-400">
            %{dashboard?.commission_rate || 70}
          </p>
        </div>

        <div className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800/80">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Aktiv Agentlər</span>
            <div className="p-2 bg-purple-500/10 rounded-xl text-purple-400 border border-purple-500/20">
              <Users className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-black text-white">
            {dashboard?.active_agents || 0} <span className="text-sm font-normal text-slate-500">/ {dashboard?.total_agents || 0}</span>
          </p>
        </div>

        <div className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800/80">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Fərdi Paketlər</span>
            <div className="p-2 bg-amber-500/10 rounded-xl text-amber-400 border border-amber-500/20">
              <Package className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-black text-amber-400">
            {packages.length}
          </p>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('agents')}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm transition ${
            activeTab === 'agents'
              ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>Agentlərim ({agents.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('packages')}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm transition ${
            activeTab === 'packages'
              ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
          }`}
        >
          <Package className="w-4 h-4" />
          <span>Paketlərim ({packages.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('earnings')}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm transition ${
            activeTab === 'earnings'
              ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
          }`}
        >
          <DollarSign className="w-4 h-4" />
          <span>Qazanc Tarixçəsi</span>
        </button>
      </div>

      {/* TAB 1: AGENTS */}
      {activeTab === 'agents' && (
        <div className="bg-slate-900/60 rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
          <div className="p-5 border-b border-slate-800 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Mənə Bağlı Agentlər</h2>
              <p className="text-xs text-slate-400">Yalnız sizin qeydiyyatdan keçirdiyiniz agentlər burada görünür.</p>
            </div>
            <button
              onClick={() => { setAgentError(null); setIsAddAgentOpen(true); }}
              className="flex items-center gap-1.5 px-3.5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold transition"
            >
              <Plus className="w-4 h-4" />
              <span>Agent Əlavə Et</span>
            </button>
          </div>

          {agents.length === 0 ? (
            <div className="p-12 text-center text-slate-400 space-y-3">
              <Users className="w-10 h-10 mx-auto text-slate-600" />
              <p>Hələ heç bir agent qeydiyyatdan keçirməmisiniz.</p>
              <button
                onClick={() => { setAgentError(null); setIsAddAgentOpen(true); }}
                className="px-4 py-2 bg-blue-600 text-white text-xs font-bold rounded-xl"
              >
                İlk Agenti Qeydiyyatdan Keçir
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-950/40 text-slate-400 text-xs uppercase font-semibold">
                    <th className="py-3.5 px-4">Agent Adı</th>
                    <th className="py-3.5 px-4">Əlaqə</th>
                    <th className="py-3.5 px-4">Kanal</th>
                    <th className="py-3.5 px-4">Paket</th>
                    <th className="py-3.5 px-4">Status</th>
                    <th className="py-3.5 px-4">Bitmə Vaxtı</th>
                    <th className="py-3.5 px-4">Qeydiyyat</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {agents.map((a) => (
                    <tr key={a.id} className="hover:bg-slate-800/30 transition">
                      <td className="py-4 px-4 font-bold text-white">{a.name}</td>
                      <td className="py-4 px-4 text-xs">
                        <div>{a.phone}</div>
                        {a.telegram_handle && <div className="text-blue-400">@{a.telegram_handle}</div>}
                      </td>
                      <td className="py-4 px-4">
                        <span className="capitalize text-xs font-medium px-2 py-0.5 rounded-md bg-slate-800 text-slate-300">
                          {a.preferred_channel}
                        </span>
                      </td>
                      <td className="py-4 px-4 font-semibold text-emerald-400">{a.plan}</td>
                      <td className="py-4 px-4">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                          a.status === 'active' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                        }`}>
                          {a.status === 'active' ? 'Aktiv' : a.status}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-xs text-slate-400">
                        {a.plan_expires_at ? new Date(a.plan_expires_at).toLocaleDateString('az-AZ') : 'Limitsiz'}
                      </td>
                      <td className="py-4 px-4 text-xs text-slate-500">
                        {new Date(a.created_at).toLocaleDateString('az-AZ')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: PACKAGES */}
      {activeTab === 'packages' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Fərdi Abunə Paketlərim</h2>
              <p className="text-xs text-slate-400">Öz agentləriniz üçün fərdi qiymət və imkanlara malik paketlər qurun.</p>
            </div>
            <button
              onClick={openAddPkgModal}
              className="flex items-center gap-1.5 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-bold shadow-lg shadow-blue-500/25 transition"
            >
              <Plus className="w-4 h-4" />
              <span>Yeni Paket Yarat</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {packages.map((pkg) => (
              <div key={pkg.id} className="bg-slate-900/70 border border-slate-800 rounded-3xl p-6 shadow-xl relative overflow-hidden flex flex-col justify-between hover:border-slate-700 transition">
                <div className="space-y-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-xl font-bold text-white">{pkg.name}</h3>
                      <p className="text-xs text-slate-400 mt-0.5">{pkg.description || 'Fərdi agent paketi'}</p>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => openEditPkgModal(pkg)}
                        className="p-1.5 text-slate-400 hover:text-white bg-slate-800 rounded-lg transition"
                      >
                        <Edit3 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDeletePackage(pkg)}
                        className="p-1.5 text-rose-400 hover:text-rose-300 bg-rose-500/10 rounded-lg transition"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  <div className="pt-2">
                    <span className="text-3xl font-black text-white">{pkg.price} AZN</span>
                    <span className="text-xs text-slate-400 ml-1.5">/ {pkg.period === 'monthly' ? 'aylıq' : pkg.period}</span>
                  </div>

                  <div className="space-y-2 text-xs text-slate-300 pt-2 border-t border-slate-800">
                    <div className="flex items-center gap-2">
                      <Check className="w-4 h-4 text-emerald-400" />
                      <span>{pkg.max_searches} Paralel Axtarış Limiti</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Check className="w-4 h-4 text-emerald-400" />
                      <span>{pkg.duration_days} Gün Aktivlik Müddəti</span>
                    </div>
                    {pkg.feature_makler_detector && (
                      <div className="flex items-center gap-2">
                        <Check className="w-4 h-4 text-emerald-400" />
                        <span>AI Makler & Vasitəçi Detektoru</span>
                      </div>
                    )}
                    {pkg.feature_avm_bargain_finder && (
                      <div className="flex items-center gap-2">
                        <Check className="w-4 h-4 text-emerald-400" />
                        <span>AVM Bazar Qiyməti & Fırsət Bildirişi</span>
                      </div>
                    )}
                    {pkg.feature_b2b_cobrokering && (
                      <div className="flex items-center gap-2">
                        <Check className="w-4 h-4 text-emerald-400" />
                        <span>B2B Partnyorluq və Qapalı Elanlar</span>
                      </div>
                    )}
                    {pkg.feature_backup_service && (
                      <div className="flex items-center gap-2">
                        <Check className="w-4 h-4 text-emerald-400" />
                        <span>Avtomatlaşdırılmış Backup Xidməti</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs">
                  <span className="text-slate-500">Qazancınız (70%):</span>
                  <span className="font-bold text-emerald-400">+{((pkg.price * (dashboard?.commission_rate || 70)) / 100).toFixed(1)} AZN</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: EARNINGS & TRANSACTIONS */}
      {activeTab === 'earnings' && (
        <div className="bg-slate-900/60 rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
          <div className="p-5 border-b border-slate-800 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Qazanc və Komissiya Tarixçəsi</h2>
              <p className="text-xs text-slate-400">Agentlərinizin abunələrindən qazandığınız komissiya daxilolmaları.</p>
            </div>
            <div className="text-right">
              <span className="text-xs text-slate-400 block">Çıxarıla bilən Balans</span>
              <span className="text-xl font-black text-emerald-400">{dashboard?.balance.toLocaleString()} AZN</span>
            </div>
          </div>

          {!earnings || earnings.transactions.length === 0 ? (
            <div className="p-12 text-center text-slate-400">Hələ heç bir əməliyyat qeydə alınmayıb.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-950/40 text-slate-400 text-xs uppercase font-semibold">
                    <th className="py-3.5 px-4">Təsvir</th>
                    <th className="py-3.5 px-4">Satış Məbləği</th>
                    <th className="py-3.5 px-4">Komissiya %</th>
                    <th className="py-3.5 px-4">Sizin Qazancınız</th>
                    <th className="py-3.5 px-4">Platforma Haqqı</th>
                    <th className="py-3.5 px-4">Tarix</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {earnings.transactions.map((t) => (
                    <tr key={t.id} className="hover:bg-slate-800/30 transition">
                      <td className="py-4 px-4 font-semibold text-white">{t.description || 'Abunə Satışı'}</td>
                      <td className="py-4 px-4 font-medium">{t.amount} AZN</td>
                      <td className="py-4 px-4 text-indigo-400 font-bold">%{t.commission_rate}</td>
                      <td className="py-4 px-4 font-black text-emerald-400">+{t.seller_profit} AZN</td>
                      <td className="py-4 px-4 text-slate-400">{t.platform_fee} AZN</td>
                      <td className="py-4 px-4 text-xs text-slate-500">
                        {new Date(t.created_at).toLocaleString('az-AZ')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* REGISTER AGENT MODAL */}
      {isAddAgentOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 w-full max-w-md rounded-2xl p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Users className="w-5 h-5 text-blue-400" />
                <span>Yeni Agent Qeydiyyatı</span>
              </h3>
              <button onClick={() => setIsAddAgentOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {agentError && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-400 flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{agentError}</span>
              </div>
            )}

            <form onSubmit={handleRegisterAgent} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Agentin Adı Soyadı *</label>
                <input
                  type="text"
                  required
                  value={agentName}
                  onChange={(e) => setAgentName(e.target.value)}
                  placeholder="Məs: Rəşad Əliyev"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Telefon Nömrəsi *</label>
                <input
                  type="text"
                  required
                  value={agentPhone}
                  onChange={(e) => setAgentPhone(e.target.value)}
                  placeholder="+994501234567"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                />
                <span className="text-[10px] text-slate-500 mt-0.5 block">Unikal nömrə (Sistemdə artıq varsa qeydə alınmayacaq)</span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Telegram İstifadəçi Adı</label>
                  <input
                    type="text"
                    value={agentTg}
                    onChange={(e) => setAgentTg(e.target.value)}
                    placeholder="@agent_username"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Bildiriş Kanalı</label>
                  <select
                    value={agentChannel}
                    onChange={(e) => setAgentChannel(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  >
                    <option value="telegram">Telegram</option>
                    <option value="whatsapp">WhatsApp</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Təyin Ediləcək Paket *</label>
                <select
                  required
                  value={agentPkgId}
                  onChange={(e) => setAgentPkgId(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                >
                  {packages.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.price} AZN / {p.period})
                    </option>
                  ))}
                </select>
              </div>

              <div className="pt-3 flex gap-3">
                <button
                  type="button"
                  onClick={() => setIsAddAgentOpen(false)}
                  className="w-1/2 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium rounded-xl transition"
                >
                  Ləğv et
                </button>
                <button
                  type="submit"
                  disabled={submittingAgent}
                  className="w-1/2 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold rounded-xl shadow-lg shadow-blue-500/25 transition disabled:opacity-50"
                >
                  {submittingAgent ? 'Qeydiyyat...' : 'Agenti Qeyd Et'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CREATE / EDIT PACKAGE MODAL */}
      {isAddPkgOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 w-full max-w-md rounded-2xl p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Package className="w-5 h-5 text-blue-400" />
                <span>{editingPkg ? 'Paketi Redaktə Et' : 'Yeni Fərdi Paket'}</span>
              </h3>
              <button onClick={() => setIsAddPkgOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSavePackage} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Paketin Adı *</label>
                <input
                  type="text"
                  required
                  value={pkgName}
                  onChange={(e) => setPkgName(e.target.value)}
                  placeholder="Məs: VIP Agent Paketi"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Qiymət (AZN) *</label>
                  <input
                    type="number"
                    min="0"
                    step="1"
                    required
                    value={pkgPrice}
                    onChange={(e) => setPkgPrice(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">
                    {pkgPrice === 0 ? 'Pulsuz Sınaq Paketi (0 AZN)' : `Min: ${dashboard?.min_package_price || 29} AZN`}
                  </span>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Müddət (Gün)</label>
                  <input
                    type="number"
                    min="1"
                    max={pkgPrice === 0 ? (dashboard?.max_trial_days || 14) : 365}
                    required
                    value={pkgDuration}
                    onChange={(e) => setPkgDuration(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">
                    {pkgPrice === 0 ? `Max sınaq: ${dashboard?.max_trial_days || 14} gün` : 'Standart: 30 gün'}
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Axtarış Slotu Limiti</label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  required
                  value={pkgMaxSearches}
                  onChange={(e) => setPkgMaxSearches(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="space-y-2 pt-2 border-t border-slate-800">
                <label className="text-xs font-semibold text-slate-400 block mb-1">İmkanlar və Funksiyalar</label>
                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={pkgMakler}
                    onChange={(e) => setPkgMakler(e.target.checked)}
                    className="rounded bg-slate-950 border-slate-800 text-blue-600 focus:ring-0"
                  />
                  <span>AI Makler & Vasitəçi Detektoru</span>
                </label>
                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={pkgAvm}
                    onChange={(e) => setPkgAvm(e.target.checked)}
                    className="rounded bg-slate-950 border-slate-800 text-blue-600 focus:ring-0"
                  />
                  <span>AVM Bazar Qiyməti & Fırsət Bildirişi</span>
                </label>
                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={pkgB2b}
                    onChange={(e) => setPkgB2b(e.target.checked)}
                    className="rounded bg-slate-950 border-slate-800 text-blue-600 focus:ring-0"
                  />
                  <span>B2B Şəbəkə & Co-Brokering</span>
                </label>
                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={pkgBackup}
                    onChange={(e) => setPkgBackup(e.target.checked)}
                    className="rounded bg-slate-950 border-slate-800 text-blue-600 focus:ring-0"
                  />
                  <span>Avtomatik Backup Xidməti</span>
                </label>
              </div>

              <div className="pt-3 flex gap-3">
                <button
                  type="button"
                  onClick={() => setIsAddPkgOpen(false)}
                  className="w-1/2 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium rounded-xl transition"
                >
                  Ləğv et
                </button>
                <button
                  type="submit"
                  disabled={submittingPkg}
                  className="w-1/2 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold rounded-xl shadow-lg shadow-blue-500/25 transition disabled:opacity-50"
                >
                  {submittingPkg ? 'Saxlanılır...' : 'Yadda Saxla'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
