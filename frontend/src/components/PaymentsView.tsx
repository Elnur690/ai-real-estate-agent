import React, { useEffect, useState, useMemo } from 'react';
import {
  DollarSign, Plus, Calendar, FileText, CheckCircle, Search, Filter,
  Users, Award, TrendingUp, AlertTriangle, ArrowUpRight, Clock,
  ShieldCheck, Tag, RefreshCw, X, ChevronDown, ChevronUp, Eye, Phone,
  Send, ExternalLink, Percent, Building2, UserCheck
} from 'lucide-react';
import api from '../api';
import { Payment, PaymentAnalytics, Tenant } from '../types';

export const PaymentsView: React.FC = () => {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [analytics, setAnalytics] = useState<PaymentAnalytics | null>(null);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [selectedReceipt, setSelectedReceipt] = useState<Payment | null>(null);
  const [showSellersCard, setShowSellersCard] = useState(true);

  // Filters State
  const [searchQuery, setSearchQuery] = useState('');
  const [sourceFilter, setSourceFilter] = useState<'all' | 'reseller' | 'direct'>('all');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'expiring_soon' | 'expired'>('all');
  const [sellerFilter, setSellerFilter] = useState<number | 'all'>('all');

  // New Payment Form State
  const [paymentCategory, setPaymentCategory] = useState<'full' | 'addon_only' | 'plan_only'>('full');
  const [newPayment, setNewPayment] = useState({
    tenant_id: 0,
    amount: 0,
    currency: 'AZN',
    days_covered: 30,
    payment_category: 'full',
    include_aged_listings: false,
    addon_aged_max_months: 12,
    include_portfolio_addon: false,
    addon_portfolio_limit: 25,
    addon_portfolio_price: 15,
    notes: ''
  });

  const calculatePaymentAmount = (tenantId: number, days: number, includeAged: boolean, includePortfolio: boolean = false, category: string = paymentCategory) => {
    const selected = tenants.find(t => t.id === tenantId);
    const planCode = selected ? selected.plan : 'starter';
    const planObj = plans.find(p => p.code.toLowerCase() === planCode.toLowerCase());
    const basePrice = planObj ? planObj.price : 29.0;
    const addonPrice = planObj?.addon_aged_listings_price !== undefined ? planObj.addon_aged_listings_price : 15.0;
    const portPrice = planObj?.addon_portfolio_price !== undefined ? planObj.addon_portfolio_price : 15.0;
    const multiplier = days === 365 ? 10 : (days === 180 ? 5 : (days === 90 ? 2.7 : (days === 60 ? 2.0 : 1)));

    const agedFee = includeAged ? (addonPrice * multiplier) : 0;
    const portFee = includePortfolio ? (portPrice * multiplier) : 0;

    if (category === 'addon_only') {
      return Math.round(agedFee + portFee);
    } else if (category === 'plan_only') {
      return Math.round(basePrice * multiplier);
    } else {
      return Math.round((basePrice * multiplier) + agedFee + portFee);
    }
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const [pRes, aRes, tRes, planRes] = await Promise.all([
        api.get('/payments'),
        api.get('/payments/analytics').catch(() => ({ data: null })),
        api.get('/tenants'),
        api.get('/plans').catch(() => ({ data: [] }))
      ]);
      setPayments(pRes.data || []);
      setAnalytics(aRes.data || null);
      const fetchedTenants = tRes.data || [];
      setTenants(fetchedTenants);
      const fetchedPlans = planRes.data || [];
      setPlans(fetchedPlans);

      if (fetchedTenants.length > 0 && newPayment.tenant_id === 0) {
        const firstTenant = fetchedTenants[0];
        const isAged = !!firstTenant.feature_aged_listings;
        const maxMonths = firstTenant.addon_aged_max_months || 12;
        const isPort = !!firstTenant.feature_portfolio;
        const portLimit = firstTenant.portfolio_limit || 25;
        const matchPlan = fetchedPlans.find((p: any) => p.code.toLowerCase() === (firstTenant.plan || '').toLowerCase());
        const basePrice = matchPlan ? matchPlan.price : 29.0;
        const addonPrice = matchPlan?.addon_aged_listings_price !== undefined ? matchPlan.addon_aged_listings_price : 15.0;
        const portPrice = firstTenant.addon_portfolio_price || matchPlan?.addon_portfolio_price || 15.0;
        const total = Math.round(basePrice + (isAged ? addonPrice : 0) + (isPort ? portPrice : 0));

        setNewPayment({
          tenant_id: firstTenant.id,
          amount: total,
          currency: matchPlan ? matchPlan.currency : 'AZN',
          days_covered: 30,
          payment_category: 'full',
          include_aged_listings: isAged,
          addon_aged_max_months: maxMonths,
          include_portfolio_addon: isPort,
          addon_portfolio_limit: portLimit,
          addon_portfolio_price: portPrice,
          notes: `Cash collected for ${firstTenant.name} (${(firstTenant.plan || 'STARTER').toUpperCase()} Plan)`
        });
      }
    } catch (e) {
      console.error('Failed to load payments data:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleTenantSelect = (tenantId: number) => {
    const selected = tenants.find(t => t.id === tenantId);
    if (selected) {
      const matchPlan = plans.find(p => p.code.toLowerCase() === (selected.plan || '').toLowerCase());
      const isAged = !!selected.feature_aged_listings;
      const maxMonths = selected.addon_aged_max_months || 12;
      const isPort = !!selected.feature_portfolio;
      const portLimit = selected.portfolio_limit || 25;
      const portPrice = selected.addon_portfolio_price || matchPlan?.addon_portfolio_price || 15.0;
      const total = calculatePaymentAmount(tenantId, newPayment.days_covered, isAged, isPort, paymentCategory);

      setNewPayment(prev => ({
        ...prev,
        tenant_id: tenantId,
        amount: total,
        currency: matchPlan ? matchPlan.currency : 'AZN',
        include_aged_listings: isAged,
        addon_aged_max_months: maxMonths,
        include_portfolio_addon: isPort,
        addon_portfolio_limit: portLimit,
        addon_portfolio_price: portPrice,
        notes: `Cash collected for ${selected.name} (${(selected.plan || 'STARTER').toUpperCase()} Plan)`
      }));
    }
  };

  const handlePeriodOrAddonChange = (days: number, includeAged: boolean, includePortfolio: boolean = newPayment.include_portfolio_addon, category: 'full' | 'addon_only' | 'plan_only' = paymentCategory) => {
    setPaymentCategory(category);
    const effectiveAged = category === 'addon_only' ? includeAged : (category === 'plan_only' ? false : includeAged);
    const effectivePort = category === 'addon_only' ? includePortfolio : (category === 'plan_only' ? false : includePortfolio);
    const total = calculatePaymentAmount(newPayment.tenant_id, days, effectiveAged, effectivePort, category);
    setNewPayment(prev => ({
      ...prev,
      days_covered: days,
      payment_category: category,
      include_aged_listings: effectiveAged,
      include_portfolio_addon: effectivePort,
      amount: total
    }));
  };

  const handleRecordPayment = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/payments', {
        ...newPayment,
        payment_category: paymentCategory
      });
      setShowModal(false);
      await loadData();
    } catch (e) {
      console.error(e);
    }
  };

  // Filtered Payments computation
  const filteredPayments = useMemo(() => {
    return payments.filter(p => {
      // Source filter
      if (sourceFilter === 'reseller' && !p.is_reseller_sale) return false;
      if (sourceFilter === 'direct' && p.is_reseller_sale) return false;

      // Reseller filter
      if (sellerFilter !== 'all' && p.seller_id !== sellerFilter) return false;

      // Status filter
      if (statusFilter !== 'all') {
        const subStatus = p.subscription_status || (p.is_expired ? 'expired' : (p.days_remaining !== undefined && p.days_remaining <= 5 ? 'expiring_soon' : 'active'));
        if (statusFilter !== subStatus) return false;
      }

      // Search Query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const tenantName = (p.tenant_name || '').toLowerCase();
        const tenantPhone = (p.tenant_phone || '').toLowerCase();
        const sellerName = (p.seller_name || '').toLowerCase();
        const sellerCompany = (p.seller_company || '').toLowerCase();
        const pkgName = (p.package_name || '').toLowerCase();
        const notes = (p.notes || '').toLowerCase();
        const idStr = String(p.id);

        if (!tenantName.includes(q) &&
            !tenantPhone.includes(q) &&
            !sellerName.includes(q) &&
            !sellerCompany.includes(q) &&
            !pkgName.includes(q) &&
            !notes.includes(q) &&
            idStr !== q) {
          return false;
        }
      }

      return true;
    });
  }, [payments, sourceFilter, statusFilter, sellerFilter, searchQuery]);

  return (
    <div className="space-y-6">
      {/* Header & Primary CTA */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-xl font-bold text-white">Nağd Ödənişlər & Abunə İzləmə Mərkəzi</h2>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Canlı Maliyyə Ledger
            </span>
          </div>
          <p className="text-slate-400 text-xs mt-1">
            Reseller satışları, nağd ödəniş yığımları, komissiya bölüşdürmələri və canlı abunə sonlanma tarixlərini izləyin.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadData}
            title="Yenilə"
            className="p-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-xl transition border border-slate-700"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-emerald-400' : ''}`} />
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white text-sm font-semibold px-4 py-2.5 rounded-xl transition-all shadow-lg shadow-emerald-500/20 active:scale-95"
          >
            <Plus className="w-4 h-4" />
            Nağd Ödəniş Qeyd Et & Aktivləşdir
          </button>
        </div>
      </div>

      {/* KPI Analytics Cards */}
      {analytics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Gross Revenue */}
          <div className="glass-card p-4 rounded-2xl border border-slate-800 relative overflow-hidden bg-slate-900/40">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400">Ümumi Dövriyyə (Gross)</span>
              <div className="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                <DollarSign className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-black text-white">{analytics.total_gross_revenue.toLocaleString()} AZN</span>
              <span className="text-[11px] text-slate-400 font-medium">({analytics.total_payments_count} ödəniş)</span>
            </div>
            <div className="mt-3 pt-2 border-t border-slate-800/80 text-[11px] text-slate-400 flex items-center justify-between">
              <span>Birbaşa Nağd:</span>
              <span className="font-bold text-slate-200">{analytics.direct_admin_revenue.toLocaleString()} AZN</span>
            </div>
          </div>

          {/* Card 2: Platform Net Revenue */}
          <div className="glass-card p-4 rounded-2xl border border-blue-500/20 relative overflow-hidden bg-gradient-to-br from-blue-950/20 to-slate-900/40">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-blue-300">Platforma Xalis Gəliri</span>
              <div className="w-8 h-8 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                <TrendingUp className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-black text-blue-400">{analytics.platform_net_revenue.toLocaleString()} AZN</span>
            </div>
            <div className="mt-3 pt-2 border-t border-blue-500/20 text-[11px] text-slate-400 flex items-center justify-between">
              <span>Platforma Payı:</span>
              <span className="font-bold text-blue-300">
                {analytics.total_gross_revenue > 0 ? Math.round((analytics.platform_net_revenue / analytics.total_gross_revenue) * 100) : 0}%
              </span>
            </div>
          </div>

          {/* Card 3: Reseller Sales & Profit */}
          <div className="glass-card p-4 rounded-2xl border border-purple-500/20 relative overflow-hidden bg-gradient-to-br from-purple-950/20 to-slate-900/40">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-purple-300">Reseller Satışları & Qazancı</span>
              <div className="w-8 h-8 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                <Users className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-black text-white">{analytics.reseller_sales_volume.toLocaleString()} AZN</span>
            </div>
            <div className="mt-3 pt-2 border-t border-purple-500/20 text-[11px] text-slate-400 flex items-center justify-between">
              <span>Ödənilən Komissiya:</span>
              <span className="font-bold text-purple-300">+{analytics.reseller_commissions_paid.toLocaleString()} AZN</span>
            </div>
          </div>

          {/* Card 4: Subscription Health */}
          <div className="glass-card p-4 rounded-2xl border border-slate-800 relative overflow-hidden bg-slate-900/40">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400">Abunə Müddəti Sağlamlığı</span>
              <div className="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                <Clock className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-2 flex items-center gap-2">
              <div className="flex items-center gap-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-1 rounded-lg text-xs font-bold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>{analytics.subscription_health.active_count} Aktiv</span>
              </div>
              <div className="flex items-center gap-1 bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2 py-1 rounded-lg text-xs font-bold">
                <span>{analytics.subscription_health.expiring_soon_count} ≤5 gün</span>
              </div>
              <div className="flex items-center gap-1 bg-rose-500/10 text-rose-400 border border-rose-500/20 px-2 py-1 rounded-lg text-xs font-bold">
                <span>{analytics.subscription_health.expired_count} Bitib</span>
              </div>
            </div>
            <div className="mt-3 pt-2 border-t border-slate-800/80 text-[11px] text-slate-400 flex items-center justify-between">
              <span>Cəmi Qeydiyyatlı Agent:</span>
              <span className="font-bold text-slate-200">{analytics.subscription_health.total_tenants}</span>
            </div>
          </div>
        </div>
      )}

      {/* Resellers Breakdown Toggle / Card */}
      {analytics && analytics.sellers_summary && analytics.sellers_summary.length > 0 && (
        <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden bg-slate-900/30">
          <div
            onClick={() => setShowSellersCard(!showSellersCard)}
            className="p-4 flex items-center justify-between cursor-pointer hover:bg-slate-800/30 transition select-none"
          >
            <div className="flex items-center gap-2.5">
              <Award className="w-4 h-4 text-amber-400" />
              <h3 className="text-sm font-bold text-white">Reseller Satış & Komissiya İcmalı ({analytics.sellers_summary.length} Reseller)</h3>
            </div>
            <button className="text-slate-400 hover:text-white transition">
              {showSellersCard ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          </div>

          {showSellersCard && (
            <div className="p-4 pt-0 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 border-t border-slate-800/60">
              {analytics.sellers_summary.map((s) => (
                <div key={s.seller_id} className="p-3.5 bg-slate-950/60 rounded-xl border border-slate-800 hover:border-slate-700 transition">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-bold text-white text-xs flex items-center gap-1.5">
                        <span>{s.name}</span>
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          {s.rank}
                        </span>
                      </div>
                      {s.company_name && (
                        <p className="text-[11px] text-slate-400 mt-0.5">{s.company_name}</p>
                      )}
                    </div>
                    <div className="text-right">
                      <span className="text-[11px] text-slate-400 block">Komissiya</span>
                      <span className="text-xs font-bold text-indigo-400">%{s.commission_rate}</span>
                    </div>
                  </div>

                  <div className="mt-3 pt-2.5 border-t border-slate-800/80 grid grid-cols-3 gap-2 text-center text-[11px]">
                    <div className="p-1.5 bg-slate-900 rounded-lg">
                      <span className="text-slate-500 block text-[10px]">Satış Sayı</span>
                      <span className="font-bold text-white">{s.total_sales_count}</span>
                    </div>
                    <div className="p-1.5 bg-slate-900 rounded-lg">
                      <span className="text-slate-500 block text-[10px]">Gross Həcm</span>
                      <span className="font-bold text-emerald-400">{s.gross_volume} M</span>
                    </div>
                    <div className="p-1.5 bg-slate-900 rounded-lg">
                      <span className="text-slate-500 block text-[10px]">Reseller Payı</span>
                      <span className="font-bold text-purple-400">{s.seller_profit} M</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Toolbar: Search & Multi-Faceted Filters */}
      <div className="glass-card p-4 rounded-2xl border border-slate-800 space-y-3 bg-slate-900/30">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          {/* Search Input */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Agent adı, telefon, reseller adı, paket və ya qeyd üzrə axtarış..."
              className="w-full pl-10 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Reseller Dropdown Filter */}
          {analytics?.sellers_summary && analytics.sellers_summary.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 whitespace-nowrap">Reseller:</span>
              <select
                value={sellerFilter}
                onChange={(e) => setSellerFilter(e.target.value === 'all' ? 'all' : Number(e.target.value))}
                className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
              >
                <option value="all">Bütün Resellerlər</option>
                {analytics.sellers_summary.map((s) => (
                  <option key={s.seller_id} value={s.seller_id}>
                    {s.name} ({s.company_name || 'Fərdi'})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800/60">
          {/* Source Filter Pills */}
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] text-slate-500 font-semibold uppercase tracking-wider mr-1">Mənbə:</span>
            <button
              onClick={() => setSourceFilter('all')}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                sourceFilter === 'all'
                  ? 'bg-emerald-500 text-white shadow-sm'
                  : 'bg-slate-950 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              Hamısı ({payments.length})
            </button>
            <button
              onClick={() => setSourceFilter('reseller')}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition flex items-center gap-1 ${
                sourceFilter === 'reseller'
                  ? 'bg-purple-600 text-white shadow-sm'
                  : 'bg-slate-950 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              <Users className="w-3 h-3" />
              Reseller Satışları
            </button>
            <button
              onClick={() => setSourceFilter('direct')}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition flex items-center gap-1 ${
                sourceFilter === 'direct'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-slate-950 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              <Building2 className="w-3 h-3" />
              Birbaşa Admin Nağd
            </button>
          </div>

          {/* Status Filter Pills */}
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] text-slate-500 font-semibold uppercase tracking-wider mr-1">Status:</span>
            <button
              onClick={() => setStatusFilter('all')}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition ${
                statusFilter === 'all'
                  ? 'bg-slate-700 text-white'
                  : 'bg-slate-950 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              Hamısı
            </button>
            <button
              onClick={() => setStatusFilter('active')}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition flex items-center gap-1 ${
                statusFilter === 'active'
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-950 text-emerald-400 hover:bg-emerald-500/10 border border-emerald-500/20'
              }`}
            >
              🟢 Aktiv
            </button>
            <button
              onClick={() => setStatusFilter('expiring_soon')}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition flex items-center gap-1 ${
                statusFilter === 'expiring_soon'
                  ? 'bg-amber-600 text-white'
                  : 'bg-slate-950 text-amber-400 hover:bg-amber-500/10 border border-amber-500/20'
              }`}
            >
              🟡 ≤5 gün
            </button>
            <button
              onClick={() => setStatusFilter('expired')}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition flex items-center gap-1 ${
                statusFilter === 'expired'
                  ? 'bg-rose-600 text-white'
                  : 'bg-slate-950 text-rose-400 hover:bg-rose-500/10 border border-rose-500/20'
              }`}
            >
              🔴 Bitib
            </button>
          </div>
        </div>
      </div>

      {/* Advanced Ledger Table */}
      <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden bg-slate-900/40">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="p-3.5">#ID & Tarix</th>
                <th className="p-3.5">Mənbə / Reseller</th>
                <th className="p-3.5">Agent / Müştəri</th>
                <th className="p-3.5">Satılan Paket</th>
                <th className="p-3.5">Məbləğ & Bölüşdürmə</th>
                <th className="p-3.5">Abunə Müddəti & Status</th>
                <th className="p-3.5 text-right">Əməliyyat</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredPayments.map((p) => {
                const isReseller = p.is_reseller_sale;
                const daysLeft = p.days_remaining ?? 0;
                const isExp = p.is_expired ?? false;
                const isExpSoon = !isExp && daysLeft <= 5;

                return (
                  <tr key={p.id} className="hover:bg-slate-800/40 transition-colors">
                    {/* ID & Date */}
                    <td className="p-3.5 align-middle">
                      <div className="font-mono text-white font-bold">#{p.id}</div>
                      <span className="text-[11px] text-slate-400 flex items-center gap-1 mt-0.5">
                        <Calendar className="w-3 h-3 text-slate-500" />
                        {new Date(p.received_at).toLocaleDateString()}
                      </span>
                    </td>

                    {/* Source / Reseller */}
                    <td className="p-3.5 align-middle">
                      {isReseller ? (
                        <div className="space-y-1">
                          <div className="flex items-center gap-1.5">
                            <span className="font-bold text-white text-xs">{p.seller_name}</span>
                            {p.seller_rank && (
                              <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30">
                                {p.seller_rank}
                              </span>
                            )}
                          </div>
                          {p.seller_company && (
                            <span className="text-[11px] text-slate-400 block">{p.seller_company}</span>
                          )}
                          <div className="flex items-center gap-1.5 text-[10px]">
                            <span className="text-purple-400 font-semibold">Reseller Komissiyası:</span>
                            <span className="font-mono font-bold text-purple-300">%{p.seller_commission_rate ?? 70}</span>
                          </div>
                        </div>
                      ) : (
                        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[11px] font-semibold">
                          <Building2 className="w-3 h-3" />
                          <span>Birbaşa Admin Nağd</span>
                        </div>
                      )}
                    </td>

                    {/* Agent / Customer */}
                    <td className="p-3.5 align-middle">
                      <div className="font-bold text-white text-xs">{p.tenant_name || `Agent #${p.tenant_id}`}</div>
                      {p.tenant_phone && (
                        <div className="text-[11px] text-slate-400 flex items-center gap-1 mt-0.5">
                          <Phone className="w-3 h-3 text-slate-500" />
                          <span>{p.tenant_phone}</span>
                        </div>
                      )}
                      <div className="mt-1 flex items-center gap-1.5">
                        <span className={`px-1.5 py-0.2 rounded text-[10px] font-medium ${
                          p.preferred_channel === 'whatsapp' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'
                        }`}>
                          {p.preferred_channel === 'whatsapp' ? 'WhatsApp' : 'Telegram'}
                        </span>
                        <span className="text-[10px] text-slate-500">#{p.tenant_id}</span>
                      </div>
                    </td>

                    {/* Package & Addons */}
                    <td className="p-3.5 align-middle">
                      <div className="font-bold text-indigo-300 text-xs flex items-center gap-1">
                        <Tag className="w-3 h-3 text-indigo-400" />
                        <span>{p.package_name || p.tenant_plan || 'Standart'}</span>
                      </div>
                      <div className="text-[11px] text-slate-400 mt-0.5 flex items-center gap-1.5">
                        <span>Müddət: {p.package_duration_days || 30} gün</span>
                        {p.transaction_type && (
                          <span className="text-[10px] px-1 py-0.2 rounded bg-slate-800 text-slate-300">
                            {p.transaction_type === 'addon_sale' ? 'Add-on' : 'Abunə'}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Financial Split */}
                    <td className="p-3.5 align-middle">
                      <div className="font-extrabold text-sm text-white flex items-baseline gap-1">
                        <span>{p.amount.toFixed(2)}</span>
                        <span className="text-xs text-emerald-400 font-bold">{p.currency}</span>
                      </div>
                      {isReseller && (p.seller_profit !== undefined && p.seller_profit > 0) && (
                        <div className="mt-1 space-y-0.5 text-[10px]">
                          <div className="flex items-center gap-1 text-purple-300">
                            <span>Reseller:</span>
                            <span className="font-mono font-bold">+{p.seller_profit?.toFixed(2)} M</span>
                          </div>
                          <div className="flex items-center gap-1 text-blue-300">
                            <span>Platforma:</span>
                            <span className="font-mono font-bold">+{p.platform_fee?.toFixed(2)} M</span>
                          </div>
                        </div>
                      )}
                    </td>

                    {/* Subscription Tracker & Expiry */}
                    <td className="p-3.5 align-middle">
                      <div className="text-[11px] text-slate-300 font-mono">
                        {p.period_covered_start ? new Date(p.period_covered_start).toLocaleDateString() : '-'} &rarr; {p.period_covered_end ? new Date(p.period_covered_end).toLocaleDateString() : '-'}
                      </div>
                      <div className="mt-1.5">
                        {isExp ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30">
                            <AlertTriangle className="w-3 h-3" />
                            Vaxtı bitib ({daysLeft} gün)
                          </span>
                        ) : isExpSoon ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30">
                            <Clock className="w-3 h-3 animate-pulse" />
                            {daysLeft} gün qaldı (Təcili)
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                            <CheckCircle className="w-3 h-3" />
                            {daysLeft} gün aktiv qalıb
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Actions */}
                    <td className="p-3.5 align-middle text-right">
                      <button
                        onClick={() => setSelectedReceipt(p)}
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg transition border border-slate-700 text-xs font-medium"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Detallar</span>
                      </button>
                    </td>
                  </tr>
                );
              })}

              {filteredPayments.length === 0 && (
                <tr>
                  <td colSpan={7} className="p-12 text-center text-slate-400">
                    <FileText className="w-10 h-10 mx-auto text-slate-600 mb-2" />
                    <p className="font-semibold">Seçilmiş filtrlərə uyğun ödəniş qeydi tapılmadı.</p>
                    <p className="text-xs text-slate-500 mt-1">Axtarış sözünü dəyişin və ya "Nağd Ödəniş Qeyd Et" düyməsi ilə yeni ödəniş əlavə edin.</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Payment Details / Receipt Modal */}
      {selectedReceipt && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card w-full max-w-lg p-6 rounded-2xl border border-slate-800 space-y-4 bg-slate-950">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                  <FileText className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Ödəniş & Abunə Qəbzi #{selectedReceipt.id}</h3>
                  <span className="text-xs text-slate-400">{new Date(selectedReceipt.received_at).toLocaleString()}</span>
                </div>
              </div>
              <button
                onClick={() => setSelectedReceipt(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              {/* Gross Amount Pill */}
              <div className="p-3 bg-slate-900 rounded-xl border border-slate-800 flex items-center justify-between">
                <span className="text-slate-400 font-medium">Yığılmış Məbləğ:</span>
                <span className="text-lg font-black text-emerald-400">{selectedReceipt.amount} {selectedReceipt.currency}</span>
              </div>

              {/* Financial Split Breakdown */}
              {selectedReceipt.is_reseller_sale && (
                <div className="p-3 bg-purple-950/20 border border-purple-500/20 rounded-xl space-y-2">
                  <span className="text-purple-300 font-bold block text-[11px] uppercase tracking-wider">Maliyyə Bölüşdürməsi</span>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Reseller Komissiyası (%{selectedReceipt.seller_commission_rate ?? 70}):</span>
                    <span className="font-bold text-purple-400">+{selectedReceipt.seller_profit?.toFixed(2)} AZN</span>
                  </div>
                  <div className="flex items-center justify-between pt-1 border-t border-purple-500/20">
                    <span className="text-slate-400">Platforma Xalis Payı:</span>
                    <span className="font-bold text-blue-400">+{selectedReceipt.platform_fee?.toFixed(2)} AZN</span>
                  </div>
                </div>
              )}

              {/* Agent Information */}
              <div className="p-3 bg-slate-900 rounded-xl border border-slate-800 space-y-1.5">
                <span className="text-slate-400 font-bold block text-[11px] uppercase tracking-wider">Agent Məlumatları</span>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Ad / Şirkət:</span>
                  <span className="font-bold text-white">{selectedReceipt.tenant_name}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Telefon:</span>
                  <span className="font-mono text-white">{selectedReceipt.tenant_phone || '-'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Kanal:</span>
                  <span className="font-medium text-indigo-400 capitalize">{selectedReceipt.preferred_channel || 'Telegram'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Paket:</span>
                  <span className="font-bold text-white">{selectedReceipt.package_name || selectedReceipt.tenant_plan || 'Standart'}</span>
                </div>
              </div>

              {/* Reseller Information if applicable */}
              {selectedReceipt.is_reseller_sale && (
                <div className="p-3 bg-slate-900 rounded-xl border border-slate-800 space-y-1.5">
                  <span className="text-slate-400 font-bold block text-[11px] uppercase tracking-wider">Satıcı / Reseller</span>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Reseller Adı:</span>
                    <span className="font-bold text-white">{selectedReceipt.seller_name}</span>
                  </div>
                  {selectedReceipt.seller_company && (
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Şirkət:</span>
                      <span className="text-slate-200">{selectedReceipt.seller_company}</span>
                    </div>
                  )}
                  {selectedReceipt.seller_phone && (
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Telefon:</span>
                      <span className="font-mono text-slate-200">{selectedReceipt.seller_phone}</span>
                    </div>
                  )}
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Rank:</span>
                    <span className="text-amber-400 font-bold">{selectedReceipt.seller_rank || 'Bronze'}</span>
                  </div>
                </div>
              )}

              {/* Subscription Period */}
              <div className="p-3 bg-slate-900 rounded-xl border border-slate-800 space-y-1.5">
                <span className="text-slate-400 font-bold block text-[11px] uppercase tracking-wider">Abunə Qüvvədəolma Müddəti</span>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Başlanğıc:</span>
                  <span className="font-mono text-white">{selectedReceipt.period_covered_start ? new Date(selectedReceipt.period_covered_start).toLocaleDateString() : '-'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Bitmə Tarixi:</span>
                  <span className="font-mono text-white">{selectedReceipt.period_covered_end ? new Date(selectedReceipt.period_covered_end).toLocaleDateString() : '-'}</span>
                </div>
                <div className="flex items-center justify-between pt-1 border-t border-slate-800">
                  <span className="text-slate-400">Status:</span>
                  <span className={`font-bold ${selectedReceipt.is_expired ? 'text-rose-400' : 'text-emerald-400'}`}>
                    {selectedReceipt.is_expired ? 'Vaxtı bitib' : `${selectedReceipt.days_remaining} gün qalıb`}
                  </span>
                </div>
              </div>

              {/* Notes */}
              {selectedReceipt.notes && (
                <div className="p-3 bg-slate-900 rounded-xl border border-slate-800">
                  <span className="text-slate-400 font-bold block text-[11px] uppercase tracking-wider mb-1">Qeydlər</span>
                  <p className="text-slate-300 leading-relaxed">{selectedReceipt.notes}</p>
                </div>
              )}
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setSelectedReceipt(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold transition"
              >
                Bağla
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Manual Cash Payment Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card w-full max-w-md p-6 rounded-2xl border border-slate-800 space-y-4 bg-slate-950">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white">Nağd Ödəniş Qeyd Et & Hesabı Aktivləşdir</h3>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleRecordPayment} className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Ödəniş Kateqoriyası</label>
                <div className="grid grid-cols-3 gap-1.5 p-1 bg-slate-900 rounded-xl border border-slate-800 text-xs font-medium">
                  <button
                    type="button"
                    onClick={() => handlePeriodOrAddonChange(newPayment.days_covered, newPayment.include_aged_listings, newPayment.include_portfolio_addon, 'full')}
                    className={`py-1.5 rounded-lg text-center transition-all ${
                      paymentCategory === 'full' 
                        ? 'bg-emerald-500 text-white shadow-md font-semibold' 
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Plan + Addon
                  </button>
                  <button
                    type="button"
                    onClick={() => handlePeriodOrAddonChange(newPayment.days_covered, true, true, 'addon_only')}
                    className={`py-1.5 rounded-lg text-center transition-all ${
                      paymentCategory === 'addon_only' 
                        ? 'bg-purple-600 text-white shadow-md font-semibold' 
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Addon Only
                  </button>
                  <button
                    type="button"
                    onClick={() => handlePeriodOrAddonChange(newPayment.days_covered, false, false, 'plan_only')}
                    className={`py-1.5 rounded-lg text-center transition-all ${
                      paymentCategory === 'plan_only' 
                        ? 'bg-blue-600 text-white shadow-md font-semibold' 
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Plan Only
                  </button>
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Agenti Seçin *</label>
                <select
                  value={newPayment.tenant_id}
                  onChange={(e) => handleTenantSelect(Number(e.target.value))}
                  className="w-full bg-slate-900 border border-slate-800 px-3 py-2 rounded-xl text-xs text-white focus:outline-none focus:border-emerald-500"
                >
                  {tenants.map(t => (
                    <option key={t.id} value={t.id}>{t.name} ({(t.plan || 'STARTER').toUpperCase()} - {t.phone})</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">
                    {paymentCategory === 'addon_only' ? 'Add-on Məbləği (AZN)' : 'Ödənilən Məbləğ (AZN)'}
                  </label>
                  <input
                    type="number"
                    required
                    value={newPayment.amount}
                    onChange={(e) => setNewPayment({ ...newPayment, amount: Number(e.target.value) })}
                    className="w-full bg-slate-900 border border-slate-800 px-3 py-2 rounded-xl text-xs text-white font-bold focus:outline-none focus:border-emerald-500"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-400 block mb-1">Əhatə Müddəti</label>
                  <select
                    value={newPayment.days_covered}
                    onChange={(e) => handlePeriodOrAddonChange(Number(e.target.value), newPayment.include_aged_listings, newPayment.include_portfolio_addon, paymentCategory)}
                    className="w-full bg-slate-900 border border-slate-800 px-3 py-2 rounded-xl text-xs text-white focus:outline-none focus:border-emerald-500"
                  >
                    <option value={30}>1 Ay (30 Gün)</option>
                    <option value={60}>2 Ay (60 Gün)</option>
                    <option value={90}>3 Ay (90 Gün)</option>
                    <option value={180}>6 Ay (180 Gün)</option>
                    <option value={365}>1 İl (365 Gün)</option>
                  </select>
                </div>
              </div>

              {/* Aged Listings Addon Option */}
              {paymentCategory === 'full' && (
                <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800 space-y-2">
                  <label className="flex items-center justify-between cursor-pointer">
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={newPayment.include_aged_listings}
                        onChange={(e) => {
                          const val = e.target.checked;
                          handlePeriodOrAddonChange(newPayment.days_covered, val, newPayment.include_portfolio_addon, paymentCategory);
                        }}
                        className="rounded accent-emerald-500"
                      />
                      <span className="text-xs font-semibold text-slate-200">
                        Arxiv Elanlar Add-onunu Daxil Et
                      </span>
                    </div>
                    <span className="text-[11px] text-purple-400 font-mono font-semibold">
                      +15 AZN/ay
                    </span>
                  </label>

                  {newPayment.include_aged_listings && (
                    <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 text-xs">
                      <span className="text-slate-400">Arxiv Baxış Müddəti:</span>
                      <select
                        value={newPayment.addon_aged_max_months}
                        onChange={(e) => setNewPayment({ ...newPayment, addon_aged_max_months: Number(e.target.value) })}
                        className="bg-slate-800 border border-slate-700 text-white rounded-lg px-2 py-1 text-xs font-medium"
                      >
                        <option value={1}>1 Ay</option>
                        <option value={3}>3 Ay</option>
                        <option value={6}>6 Ay</option>
                        <option value={12}>12 Ay (1 İl)</option>
                        <option value={24}>24 Ay (2 İl)</option>
                      </select>
                    </div>
                  )}
                </div>
              )}

              {/* Portfolio Add-on Option */}
              {paymentCategory === 'full' && (
                <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800 space-y-2">
                  <label className="flex items-center justify-between cursor-pointer">
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={newPayment.include_portfolio_addon}
                        onChange={(e) => {
                          const val = e.target.checked;
                          handlePeriodOrAddonChange(newPayment.days_covered, newPayment.include_aged_listings, val, paymentCategory);
                        }}
                        className="rounded accent-emerald-500"
                      />
                      <span className="text-xs font-semibold text-slate-200">
                        Agent Portfel & Showcase Add-onunu Daxil Et
                      </span>
                    </div>
                    <span className="text-[11px] text-emerald-400 font-mono font-semibold">
                      +{newPayment.addon_portfolio_price || 15} AZN/ay
                    </span>
                  </label>
                </div>
              )}

              <div>
                <label className="text-xs text-slate-400 block mb-1">Qeydlər & Qəbz Açıqlaması</label>
                <textarea
                  rows={2}
                  value={newPayment.notes}
                  onChange={(e) => setNewPayment({ ...newPayment, notes: e.target.value })}
                  placeholder="Nağd ödəniş qeydi və ya qəbz nömrəsi..."
                  className="w-full bg-slate-900 border border-slate-800 px-3 py-2 rounded-xl text-xs text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold transition"
                >
                  Ləğv Et
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white rounded-xl text-xs font-bold transition shadow-lg shadow-emerald-500/20"
                >
                  Ödənişi Qeyd Et & Aktivləşdir
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
