import React, { useEffect, useState } from 'react';
import { UserPlus, Search, ShieldCheck, Clock, AlertCircle, Phone, MessageSquare, Plus, CheckCircle, QrCode, RefreshCw, CheckCircle2, Wifi, WifiOff, DollarSign, Edit3, Trash2, X, AlertTriangle, Users, MapPin, Store, Sparkles, Briefcase, ExternalLink, Globe } from 'lucide-react';
import api from '../api';
import { Tenant, SavedSearch } from '../types';

const BAKU_DISTRICT_OPTIONS = [
  "Yasamal", "Nəsimi", "Binəqədi", "Nərimanov", "Səbail",
  "Xətai", "Nizami", "Sabunçu", "Suraxanı", "Xəzər",
  "Abşeron", "Sumqayıt", "Qaradağ", "Pirallahi"
];

const BAKU_METRO_OPTIONS = [
  "28 May", "Gənclik", "Nəriman Nərimanov", "Elmlər Akademiyası", "Nizami",
  "İnşaatçılar", "20 Yanvar", "Memar Əcəmi", "Nəsimi", "Azadlıq prospekti",
  "Dərnəgül", "İçərişəhər", "Sahil", "Xətai", "Cəfər Cabbarlı",
  "Ulduz", "Koroğlu", "Qara Qarayev", "Neftçilər", "Xalqlar Dostluğu",
  "Əhmədli", "Həzi Aslanov", "Avtovağzal", "8 Noyabr", "Xocəsən"
];

export const TenantsView: React.FC = () => {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [sellers, setSellers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTenant, setSelectedTenant] = useState<{ tenant: Tenant; saved_searches: SavedSearch[]; sub_agents?: Tenant[] } | null>(null);
  
  // Move Seller Modal State
  const [moveSellerModalTenant, setMoveSellerModalTenant] = useState<Tenant | null>(null);
  const [selectedSellerId, setSelectedSellerId] = useState<number | ''>('');
  const [movingSeller, setMovingSeller] = useState(false);

  // Modals
  const [showAddModal, setShowAddModal] = useState(false);
  const [newTenant, setNewTenant] = useState({
    name: '',
    phone: '',
    type: 'individual_agent',
    preferred_channel: 'telegram',
    plan: 'starter',
    trial_days: 7,
    telegram_handle: '',
    telegram_chat_id: '',
    whatsapp_number: '',
    backup_enabled: false,
    backup_frequency_days: 7,
    feature_aged_listings: false,
    addon_aged_max_months: 12,
    addon_saved_searches: 0,
    feature_watermark_free_images: false,
    addon_image_requests_limit: 0,
    feature_crm: false,
    addon_crm_price: 0.0,
    feature_portfolio: false,
    portfolio_limit: 25,
    addon_portfolio_price: 15.0,
    portfolio_slug: '',
    feature_custom_domain: false,
    custom_domain: '',
    custom_domain_enabled: false,
    addon_custom_domain_price: 5.0,
  });

  const [availablePlans, setAvailablePlans] = useState<any[]>([]);

  // Sub-Agent Modal State
  const [showAddSubAgentModal, setShowAddSubAgentModal] = useState(false);
  const [subAgentParent, setSubAgentParent] = useState<Tenant | null>(null);
  const [subAgentForm, setSubAgentForm] = useState({
    name: '',
    phone: '',
    preferred_channel: 'telegram',
    whatsapp_number: '',
    telegram_chat_id: '',
    assigned_districts: [] as string[]
  });
  const [subAgentLoading, setSubAgentLoading] = useState(false);

  // Edit Modal State
  const [editTenant, setEditTenant] = useState<Tenant | null>(null);
  const [editFormData, setEditFormData] = useState<Partial<Tenant>>({
    name: '',
    phone: '',
    status: 'active',
    plan: 'free',
    preferred_channel: 'telegram',
    whatsapp_number: '',
    telegram_handle: '',
    telegram_chat_id: '',
    backup_enabled: false,
    backup_frequency_days: 7,
    feature_aged_listings: false,
    addon_aged_max_months: 12,
    addon_saved_searches: 0,
    feature_watermark_free_images: false,
    addon_image_requests_limit: 0,
    addon_image_requests_used: 0,
    feature_crm: false,
    addon_crm_price: 0.0,
    feature_portfolio: false,
    portfolio_limit: 25,
    addon_portfolio_price: 15.0,
    portfolio_slug: '',
    feature_custom_domain: false,
    custom_domain: '',
    custom_domain_enabled: false,
    addon_custom_domain_price: 5.0,
  });

  // Delete Confirmation Modal State
  const [deleteTenantTarget, setDeleteTenantTarget] = useState<Tenant | null>(null);
  const [deleting, setDeleting] = useState(false);

  // WhatsApp Evolution API Pairing State
  const [waStatus, setWaStatus] = useState<{ connected: boolean; state: string; instance_name: string } | null>(null);
  const [waQrCode, setWaQrCode] = useState<string | null>(null);
  const [waPairingCode, setWaPairingCode] = useState<string | null>(null);
  const [waLoading, setWaLoading] = useState(false);

  // Cash Payment Modal State
  const [paymentModalTenant, setPaymentModalTenant] = useState<Tenant | null>(null);
  const [paymentCategory, setPaymentCategory] = useState<'full' | 'addon_only' | 'plan_only'>('full');
  const [paymentPlan, setPaymentPlan] = useState<string>('starter');
  const [cashAmount, setCashAmount] = useState<number>(0);
  const [cashDays, setCashDays] = useState<number>(30);
  const [cashIncludeAgedListings, setCashIncludeAgedListings] = useState<boolean>(false);
  const [cashAgedMaxMonths, setCashAgedMaxMonths] = useState<number>(12);
  const [cashExtraSearches, setCashExtraSearches] = useState<number>(0);
  const [cashFeatureImages, setCashFeatureImages] = useState<boolean>(false);
  const [cashExtraImages, setCashExtraImages] = useState<number>(0);
  const [cashIncludeCrm, setCashIncludeCrm] = useState<boolean>(false);
  const [cashIncludePortfolio, setCashIncludePortfolio] = useState<boolean>(false);
  const [cashPortfolioLimit, setCashPortfolioLimit] = useState<number>(25);
  const [cashPortfolioPrice, setCashPortfolioPrice] = useState<number>(15);
  const [cashIncludeCustomDomain, setCashIncludeCustomDomain] = useState<boolean>(false);
  const [cashCustomDomainPrice, setCashCustomDomainPrice] = useState<number>(5.0);
  const [cashNotes, setCashNotes] = useState<string>('');

  const loadTenants = async () => {
    setLoading(true);
    try {
      const [tRes, pRes, sRes] = await Promise.all([
        api.get('/tenants'),
        api.get('/plans').catch(() => ({ data: [] })),
        api.get('/sellers').catch(() => ({ data: [] }))
      ]);
      setTenants(tRes.data || []);
      const fetchedPlans = pRes.data || [];
      setAvailablePlans(fetchedPlans);
      setSellers(sRes.data || []);

      if (fetchedPlans.length > 0 && !newTenant.plan) {
        setNewTenant(prev => ({ ...prev, plan: fetchedPlans[0].code }));
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const openMoveSellerModal = (t: Tenant) => {
    setMoveSellerModalTenant(t);
    setSelectedSellerId(t.seller_id || '');
  };

  const handleMoveSeller = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!moveSellerModalTenant) return;
    setMovingSeller(true);
    try {
      await api.put(`/tenants/${moveSellerModalTenant.id}/seller`, {
        seller_id: selectedSellerId !== '' ? Number(selectedSellerId) : null
      });
      setMoveSellerModalTenant(null);
      loadTenants();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Agenti satıcıya köçürmək mümkün olmadı.');
    } finally {
      setMovingSeller(false);
    }
  };

  useEffect(() => {
    loadTenants();
  }, []);

  const openAddModal = async () => {
    setWaQrCode(null);
    try {
      const pRes = await api.get('/plans');
      if (pRes.data && pRes.data.length > 0) {
        setAvailablePlans(pRes.data);
        setNewTenant(prev => ({ ...prev, plan: pRes.data[0].code }));
      }
    } catch (e) {
      console.error(e);
    }
    setShowAddModal(true);
  };

  const openEditModal = (t: Tenant) => {
    setEditTenant(t);
    setEditFormData({
      name: t.name,
      phone: t.phone,
      type: t.type || 'individual_agent',
      preferred_channel: t.preferred_channel || 'telegram',
      plan: t.plan || 'starter',
      whatsapp_number: t.whatsapp_number || t.phone || '',
      telegram_chat_id: t.telegram_chat_id || '',
      backup_enabled: t.backup_enabled || false,
      backup_frequency_days: t.backup_frequency_days || 7,
      feature_aged_listings: t.feature_aged_listings || false,
      addon_aged_max_months: t.addon_aged_max_months || 12,
      addon_saved_searches: t.addon_saved_searches || 0,
      feature_watermark_free_images: t.feature_watermark_free_images || false,
      addon_image_requests_limit: t.addon_image_requests_limit || 0,
      addon_image_requests_used: t.addon_image_requests_used || 0,
      feature_crm: t.feature_crm ?? false,
      addon_crm_price: t.addon_crm_price ?? 0.0,
      feature_portfolio: t.feature_portfolio ?? false,
      portfolio_limit: t.portfolio_limit ?? 25,
      addon_portfolio_price: t.addon_portfolio_price ?? 15.0,
      portfolio_slug: t.portfolio_slug || '',
      feature_custom_domain: t.feature_custom_domain ?? false,
      custom_domain: t.custom_domain || '',
      custom_domain_enabled: t.custom_domain_enabled ?? false,
      addon_custom_domain_price: t.addon_custom_domain_price ?? 5.0,
    });
  };

  const handleUpdateTenant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editTenant) return;
    try {
      await api.patch(`/tenants/${editTenant.id}`, editFormData);
      setEditTenant(null);
      loadTenants();
    } catch (err) {
      console.error(err);
      alert('Failed to update tenant details.');
    }
  };

  const handleDeleteTenant = async () => {
    if (!deleteTenantTarget) return;
    setDeleting(true);
    try {
      await api.delete(`/tenants/${deleteTenantTarget.id}`);
      setDeleteTenantTarget(null);
      if (selectedTenant && selectedTenant.tenant.id === deleteTenantTarget.id) {
        setSelectedTenant(null);
      }
      loadTenants();
    } catch (err) {
      console.error(err);
      alert('Failed to delete tenant.');
    } finally {
      setDeleting(false);
    }
  };

  const handleCreateTenant = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/tenants', newTenant);
      setShowAddModal(false);
      setNewTenant({
        name: '',
        phone: '',
        type: 'individual_agent',
        preferred_channel: 'telegram',
        plan: availablePlans[0]?.code || 'starter',
        trial_days: 7,
        telegram_handle: '',
        telegram_chat_id: '',
        whatsapp_number: '',
        backup_enabled: false,
        backup_frequency_days: 7,
        feature_aged_listings: false,
        addon_aged_max_months: 12,
        addon_saved_searches: 0,
        feature_watermark_free_images: false,
        addon_image_requests_limit: 0,
        feature_crm: false,
        addon_crm_price: 0.0,
        feature_portfolio: false,
        portfolio_limit: 25,
        addon_portfolio_price: 15.0,
        portfolio_slug: '',
        feature_custom_domain: false,
        custom_domain: '',
        custom_domain_enabled: false,
        addon_custom_domain_price: 5.0,
      });
      loadTenants();
    } catch (e: any) {
      console.error(e);
      alert(e.response?.data?.detail || 'Failed to create tenant');
    }
  };

  const handleSelectTenant = async (id: number) => {
    try {
      const [tRes, subRes] = await Promise.all([
        api.get(`/tenants/${id}`),
        api.get(`/tenants/${id}/sub-agents`).catch(() => ({ data: [] }))
      ]);
      setSelectedTenant({
        ...tRes.data,
        sub_agents: subRes.data || []
      });
      
      const t = tRes.data.tenant;
      if (t && t.preferred_channel === 'whatsapp') {
        checkWhatsAppStatus(`tenant_${t.id}`);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const openAddSubAgentModal = (parent: Tenant) => {
    setSubAgentParent(parent);
    setSubAgentForm({
      name: '',
      phone: '',
      preferred_channel: parent.preferred_channel || 'telegram',
      whatsapp_number: '',
      telegram_chat_id: '',
      assigned_districts: []
    });
    setShowAddSubAgentModal(true);
  };

  const handleCreateSubAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!subAgentParent) return;
    setSubAgentLoading(true);
    try {
      await api.post(`/tenants/${subAgentParent.id}/sub-agents`, subAgentForm);
      setShowAddSubAgentModal(false);
      alert('Sub-agent uğurla əlavə edildi!');
      handleSelectTenant(subAgentParent.id);
      loadTenants();
    } catch (err: any) {
      console.error(err);
      alert(err.response?.data?.detail || 'Sub-agent əlavə edilərkən xəta baş verdi.');
    } finally {
      setSubAgentLoading(false);
    }
  };

  const toggleDistrictAssignment = (district: string) => {
    setSubAgentForm(prev => {
      const exists = prev.assigned_districts.includes(district);
      return {
        ...prev,
        assigned_districts: exists
          ? prev.assigned_districts.filter(d => d !== district)
          : [...prev.assigned_districts, district]
      };
    });
  };

  const checkWhatsAppStatus = async (instanceName: string) => {
    setWaLoading(true);
    try {
      const res = await api.get(`/whatsapp/status?instance_name=${instanceName}`);
      setWaStatus(res.data);
    } catch (e) {
      console.error(e);
      setWaStatus(null);
    } finally {
      setWaLoading(false);
    }
  };

  const generateWhatsAppQrCode = async (instanceName: string) => {
    setWaLoading(true);
    setWaQrCode(null);
    try {
      const res = await api.post(`/whatsapp/qrcode`, { instance_name: instanceName });
      if (res.data?.qrcode) {
        setWaQrCode(res.data.qrcode);
      } else if (res.data?.status === 'already_connected_or_initializing') {
        alert('WhatsApp instance is already connected or currently initializing. Check status above.');
      } else {
        alert('QR code generation is pending. Please check Evolution API container status.');
      }
    } catch (e: any) {
      console.error(e);
      const detail = e.response?.data?.detail || e.message || 'Failed to generate WhatsApp QR code.';
      alert(`WhatsApp QR Code Error: ${detail}`);
    } finally {
      setWaLoading(false);
    }
  };

  const calculateCashTotal = (
    planCode: string, 
    days: number, 
    includeAged: boolean, 
    extraSearches: number = cashExtraSearches,
    category: string = paymentCategory,
    extraImages: number = cashExtraImages,
    includeCrm: boolean = cashIncludeCrm,
    includePortfolio: boolean = cashIncludePortfolio,
    portPriceVal: number = cashPortfolioPrice,
    includeDomain: boolean = cashIncludeCustomDomain,
    domainPriceVal: number = cashCustomDomainPrice
  ) => {
    const planObj = availablePlans.find(p => p.code === planCode);
    const basePrice = planObj ? planObj.price : 29.0;
    const addonPrice = planObj?.addon_aged_listings_price !== undefined ? planObj.addon_aged_listings_price : 15.0;
    const searchPackPrice = planObj?.addon_saved_searches_price !== undefined ? planObj.addon_saved_searches_price : 10.0;
    const imagePackPrice = planObj?.addon_image_requests_price !== undefined ? planObj.addon_image_requests_price : 10.0;
    const crmPrice = planObj?.addon_crm_price !== undefined ? planObj.addon_crm_price : 15.0;
    const portfolioPrice = portPriceVal || (planObj?.addon_portfolio_price !== undefined ? planObj.addon_portfolio_price : 15.0);
    const customDomainPrice = domainPriceVal || (planObj?.addon_custom_domain_price !== undefined ? planObj.addon_custom_domain_price : 5.0);
    const multiplier = days === 365 ? 10 : (days === 180 ? 5 : (days === 90 ? 2.7 : (days === 60 ? 2.0 : 1)));

    const agedFee = includeAged ? (addonPrice * multiplier) : 0;
    const searchFee = extraSearches > 0 ? ((extraSearches / 5.0) * searchPackPrice * multiplier) : 0;
    const imageFee = extraImages > 0 ? ((extraImages / 25.0) * imagePackPrice * multiplier) : 0;
    const crmFee = includeCrm ? (crmPrice * multiplier) : 0;
    const portfolioFee = includePortfolio ? (portfolioPrice * multiplier) : 0;
    const customDomainFee = includeDomain ? (customDomainPrice * multiplier) : 0;

    if (category === 'addon_only') {
      return Math.round(agedFee + searchFee + imageFee + crmFee + portfolioFee + customDomainFee);
    } else if (category === 'plan_only') {
      return Math.round(basePrice * multiplier);
    } else {
      return Math.round((basePrice * multiplier) + agedFee + searchFee + imageFee + crmFee + portfolioFee + customDomainFee);
    }
  };

  const openCashPaymentModal = (t: Tenant, defaultCategory: 'full' | 'addon_only' | 'plan_only' = 'full') => {
    setPaymentModalTenant(t);
    const planObj = availablePlans.find(p => p.code === t.plan) || availablePlans[0];
    const initialPlan = planObj ? planObj.code : 'starter';
    const isAgedActive = defaultCategory === 'addon_only' ? true : !!t.feature_aged_listings;
    const maxMonths = t.addon_aged_max_months || 12;
    const extraSearches = t.addon_saved_searches || 0;
    const isImageActive = defaultCategory === 'addon_only' ? true : !!t.feature_watermark_free_images;
    const extraImages = t.addon_image_requests_limit || 0;
    const isCrmActive = defaultCategory === 'addon_only' ? true : !!t.feature_crm;
    const isPortfolioActive = defaultCategory === 'addon_only' ? true : !!t.feature_portfolio;
    const portLimit = t.portfolio_limit || 25;
    const portPrice = t.addon_portfolio_price || 15;
    const isDomainActive = defaultCategory === 'addon_only' ? true : !!t.feature_custom_domain;
    const domainPrice = t.addon_custom_domain_price || 5.0;
    
    setPaymentCategory(defaultCategory);
    setPaymentPlan(initialPlan);
    setCashDays(30);
    setCashIncludeAgedListings(isAgedActive);
    setCashAgedMaxMonths(maxMonths);
    setCashExtraSearches(extraSearches);
    setCashFeatureImages(isImageActive);
    setCashExtraImages(extraImages);
    setCashIncludeCrm(isCrmActive);
    setCashIncludePortfolio(isPortfolioActive);
    setCashPortfolioLimit(portLimit);
    setCashPortfolioPrice(portPrice);
    setCashIncludeCustomDomain(isDomainActive);
    setCashCustomDomainPrice(domainPrice);

    const initialAmount = calculateCashTotal(initialPlan, 30, isAgedActive, extraSearches, defaultCategory, extraImages, isCrmActive, isPortfolioActive, portPrice, isDomainActive, domainPrice);
    setCashAmount(initialAmount);
    const notePrefix = defaultCategory === 'addon_only' 
      ? `Cash payment for Addons ONLY - ${t.name}`
      : `Cash payment received for ${t.name} (${t.plan.toUpperCase()} Plan)`;
    setCashNotes(notePrefix);
  };

  const handlePlanOrPeriodChange = (
    planCode: string, 
    days: number, 
    includeAged: boolean = cashIncludeAgedListings, 
    category: 'full' | 'addon_only' | 'plan_only' = paymentCategory,
    extraSearches: number = cashExtraSearches,
    extraImages: number = cashExtraImages,
    featureImages: boolean = cashFeatureImages,
    includeCrm: boolean = cashIncludeCrm,
    includePortfolio: boolean = cashIncludePortfolio,
    portLimit: number = cashPortfolioLimit,
    portPrice: number = cashPortfolioPrice,
    includeDomain: boolean = cashIncludeCustomDomain,
    domainPrice: number = cashCustomDomainPrice
  ) => {
    setPaymentPlan(planCode);
    setCashDays(days);
    setCashIncludeAgedListings(includeAged);
    setPaymentCategory(category);
    setCashExtraSearches(extraSearches);
    setCashExtraImages(extraImages);
    setCashFeatureImages(featureImages);
    setCashIncludeCrm(includeCrm);
    setCashIncludePortfolio(includePortfolio);
    setCashPortfolioLimit(portLimit);
    setCashPortfolioPrice(portPrice);
    setCashIncludeCustomDomain(includeDomain);
    setCashCustomDomainPrice(domainPrice);
    const calculatedAmount = calculateCashTotal(planCode, days, includeAged, extraSearches, category, extraImages, includeCrm, includePortfolio, portPrice, includeDomain, domainPrice);
    setCashAmount(calculatedAmount);
    const label = category === 'addon_only' ? 'Addons Only' : `${planCode.toUpperCase()} Plan`;
    const searchTag = extraSearches > 0 ? ` + ${extraSearches} Searches` : '';
    const imgTag = extraImages > 0 ? ` + ${extraImages} Photos` : '';
    const crmTag = includeCrm ? ` + Telegram CRM` : '';
    const portTag = includePortfolio ? ` + Portfel (${portLimit} elan)` : '';
    const domainTag = includeDomain ? ` + Fərdi Domen` : '';
    setCashNotes(`Cash payment for ${label}${searchTag}${imgTag}${crmTag}${portTag}${domainTag} (${days} days)`);
  };

  const handleRecordCashPayment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!paymentModalTenant) return;
    try {
      await api.post(`/tenants/${paymentModalTenant.id}/cash-payment`, {
        plan: paymentPlan,
        duration_days: cashDays,
        amount_paid: Number(cashAmount),
        payment_category: paymentCategory,
        include_aged_listings: paymentCategory === 'addon_only' ? cashIncludeAgedListings : (paymentCategory === 'plan_only' ? false : cashIncludeAgedListings),
        addon_aged_max_months: cashAgedMaxMonths,
        addon_saved_searches: cashExtraSearches,
        feature_watermark_free_images: cashFeatureImages || (cashExtraImages > 0),
        addon_image_requests_limit: cashExtraImages,
        include_crm_addon: paymentCategory === 'addon_only' ? cashIncludeCrm : (paymentCategory === 'plan_only' ? false : cashIncludeCrm),
        include_portfolio_addon: paymentCategory === 'addon_only' ? cashIncludePortfolio : (paymentCategory === 'plan_only' ? false : cashIncludePortfolio),
        addon_portfolio_limit: cashPortfolioLimit,
        addon_portfolio_price: cashPortfolioPrice,
        include_custom_domain_addon: paymentCategory === 'addon_only' ? cashIncludeCustomDomain : (paymentCategory === 'plan_only' ? false : cashIncludeCustomDomain),
        addon_custom_domain_price: cashCustomDomainPrice,
        notes: cashNotes
      });
      setPaymentModalTenant(null);
      await loadTenants();
      if (selectedTenant && selectedTenant.tenant.id === paymentModalTenant.id) {
        handleSelectTenant(paymentModalTenant.id);
      }
      alert('Cash payment confirmed! Tenant subscription, limits and features activated.');
    } catch (e: any) {
      console.error(e);
      alert(e.response?.data?.detail || 'Failed to record cash payment');
    }
  };

  const getPlanMaxAgents = (planCode: string) => {
    const plan = availablePlans.find(p => p.code === planCode);
    return plan?.max_agents || (planCode === 'agency' ? 10 : (planCode === 'pro' ? 3 : 1));
  };

  const filteredTenants = tenants.filter(t => 
    t.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    t.phone.includes(searchTerm)
  );

  const handleDeleteSavedSearch = async (tenantId: number, searchId: number) => {
    if (!confirm('Are you sure you want to delete this saved search?')) return;
    try {
      await api.delete(`/tenants/${tenantId}/saved-searches/${searchId}`);
      handleSelectTenant(tenantId);
    } catch (e) {
      console.error(e);
      alert('Failed to delete saved search.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white">Tenant & Agent Management</h2>
          <p className="text-slate-400 text-xs mt-0.5">Manage individual agents, agency teams, sub-agent seat allocations, and territory routing.</p>
        </div>
        <button
          onClick={openAddModal}
          className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-all shadow-lg shadow-emerald-500/20"
        >
          <UserPlus className="w-4 h-4" />
          Add Agent / Tenant
        </button>
      </div>

      {/* Search Input */}
      <div className="relative">
        <Search className="w-5 h-5 absolute left-3.5 top-3 text-slate-400" />
        <input
          type="text"
          placeholder="Search tenants by name, agency, or phone..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full glass-input pl-11 pr-4 py-2.5 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
        />
      </div>

      {/* Tenants Table */}
      <div className="glass-card rounded-2xl border border-slate-800 overflow-x-auto">
        <table className="w-full text-left text-sm text-slate-300 min-w-[850px]">
          <thead className="bg-dark-800/80 text-slate-400 font-medium text-xs uppercase tracking-wider border-b border-slate-800">
            <tr>
              <th className="p-4 w-24">ID / Instance</th>
              <th className="p-4">Agent / Agency</th>
              <th className="p-4">Satıcı (Seller)</th>
              <th className="p-4">Account Type</th>
              <th className="p-4">Channel</th>
              <th className="p-4">Plan & Seats</th>
              <th className="p-4">Status</th>
              <th className="p-4">Expires</th>
              <th className="p-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {filteredTenants.map((t) => {
              const maxSeats = getPlanMaxAgents(t.plan);
              const subAgentsCount = tenants.filter(st => st.parent_tenant_id === t.id).length;
              const isSubAgent = Boolean(t.parent_tenant_id);

              return (
                <tr key={t.id} className="hover:bg-dark-700/30 transition-colors">
                  <td className="p-4 whitespace-nowrap">
                    <div className="flex items-center gap-1.5">
                      <span className="px-2 py-0.5 rounded-md bg-dark-900 border border-slate-700 text-emerald-400 font-mono font-bold text-xs shadow-sm">
                        #{t.id}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-500 font-mono mt-0.5">tenant_{t.id}</div>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-2">
                      <div className="font-semibold text-white">{t.name}</div>
                      {isSubAgent && (
                        <span className="text-[10px] bg-blue-500/20 text-blue-300 border border-blue-500/30 px-1.5 py-0.5 rounded font-mono">
                          Sub-Agent
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-slate-400">{t.phone}</div>
                  </td>
                  <td className="p-4">
                    {t.seller_name ? (
                      <div className="flex flex-col">
                        <span className="inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">
                          🏢 {t.seller_name}
                        </span>
                        {t.seller_company && (
                          <span className="text-[10px] text-slate-500 ml-1 mt-0.5">{t.seller_company}</span>
                        )}
                      </div>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium bg-slate-800 text-slate-400 border border-slate-700/60">
                        🌐 Direkt Platforma
                      </span>
                    )}
                  </td>
                  <td className="p-4">
                    <span className={`inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full font-medium ${
                      t.type === 'agency' ? 'bg-purple-500/10 text-purple-300 border border-purple-500/20' : 'bg-slate-700/50 text-slate-300'
                    }`}>
                      {t.type === 'agency' ? '🏢 Agency' : '👤 Individual'}
                    </span>
                  </td>
                  <td className="p-4">
                    <span className={`inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-medium ${
                      t.preferred_channel === 'both'
                        ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                        : t.preferred_channel === 'whatsapp'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                    }`}>
                      {t.preferred_channel === 'both' ? '⚡ Dual (WA + TG)' : t.preferred_channel === 'whatsapp' ? 'WhatsApp' : 'Telegram'}
                    </span>
                  </td>
                  <td className="p-4">
                    <div className="capitalize font-medium text-slate-200">{t.plan}</div>
                    <div className="text-[11px] text-cyan-400 font-mono flex items-center gap-1 mt-0.5">
                      <Search className="w-3 h-3" />
                      {t.active_searches_count || 0} / {t.max_saved_searches || 10} Searches
                    </div>
                    {t.feature_crm && (
                      <div className="text-[11px] text-indigo-400 font-medium flex items-center gap-1 mt-0.5">
                        <Briefcase className="w-3 h-3" />
                        CRM Mini App
                      </div>
                    )}
                    {t.feature_portfolio && (
                      <div className="text-[11px] text-purple-400 font-medium flex items-center gap-1.5 mt-0.5">
                        <span>🗂️</span>
                        <span>Portfel ({t.portfolio_limit || 25} elan)</span>
                        <a
                          href={`/v/${t.portfolio_slug || t.id}`}
                          target="_blank"
                          rel="noreferrer"
                          className="px-1.5 py-0.5 rounded bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 font-mono text-[10px] border border-purple-500/30 flex items-center gap-0.5"
                          title="Vitrini Aç"
                        >
                          <span>/v/{t.portfolio_slug || t.id}</span>
                          <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                      </div>
                    )}
                    {t.feature_custom_domain && (
                      <div className="text-[11px] text-cyan-400 font-medium flex items-center gap-1 mt-0.5">
                        <Globe className="w-3 h-3" />
                        <span>{t.custom_domain ? t.custom_domain : 'Fərdi Domen Aktiv'}</span>
                      </div>
                    )}
                    {t.feature_watermark_free_images && (
                      <div className="text-[11px] text-teal-400 font-mono flex items-center gap-1 mt-0.5">
                        <Sparkles className="w-3 h-3" />
                        {t.addon_image_requests_used || 0} / {t.addon_image_requests_limit || 0} Photos
                      </div>
                    )}
                    {t.type === 'agency' || maxSeats > 1 ? (
                      <div className="text-[11px] text-purple-400 flex items-center gap-1 mt-0.5">
                        <Users className="w-3 h-3" />
                        {subAgentsCount + 1} / {maxSeats} Seats
                      </div>
                    ) : (
                      <div className="text-[11px] text-slate-500">1 Seat</div>
                    )}
                  </td>
                  <td className="p-4">
                    <span className={`inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-medium ${
                      t.status === 'active' ? 'bg-emerald-500/10 text-emerald-400' :
                      t.status === 'pending' ? 'bg-amber-500/10 text-amber-400' : 'bg-red-500/10 text-red-400'
                    }`}>
                      {t.status === 'pending' ? 'Pending Payment' : t.status}
                    </span>
                  </td>
                  <td className="p-4 text-xs text-slate-400">
                    {t.plan_expires_at ? new Date(t.plan_expires_at).toLocaleDateString() : 'Pending Cash Payment'}
                  </td>
                  <td className="p-4 text-right space-x-1.5">
                    {(t.type === 'agency' || maxSeats > 1) && (
                      <button
                        onClick={() => openAddSubAgentModal(t)}
                        className="text-xs px-2.5 py-1.5 rounded-lg bg-purple-500/20 text-purple-300 hover:bg-purple-500/30 border border-purple-500/30 font-medium inline-flex items-center gap-1"
                        title="Add Sub-Agent Seat"
                      >
                        <Plus className="w-3 h-3" />
                        Sub-Agent
                      </button>
                    )}
                    <button
                      onClick={() => handleSelectTenant(t.id)}
                      className="text-xs px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium"
                      title="Team & Details"
                    >
                      Details
                    </button>
                    {t.status !== 'active' ? (
                      <button
                        onClick={() => openCashPaymentModal(t)}
                        className="text-xs px-2.5 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 border border-emerald-500/30 font-semibold"
                      >
                        Activate
                      </button>
                    ) : (
                      <button
                        onClick={() => openCashPaymentModal(t)}
                        className="text-xs px-2.5 py-1.5 rounded-lg bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 font-medium"
                      >
                        Renew
                      </button>
                    )}
                    <button
                      onClick={() => openMoveSellerModal(t)}
                      className="text-xs p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 border border-indigo-500/20"
                      title="Satıcıya Köçür / Dəyiş"
                    >
                      <Store className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => openEditModal(t)}
                      className="text-xs p-1.5 rounded-lg bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 border border-blue-500/20"
                      title="Edit Agent"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => setDeleteTenantTarget(t)}
                      className="text-xs p-1.5 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/20"
                      title="Delete Tenant"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              );
            })}
            {filteredTenants.length === 0 && (
              <tr>
                <td colSpan={7} className="p-8 text-center text-slate-500">
                  No tenants found. Add your first agent tenant!
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Add Sub-Agent Modal */}
      {showAddSubAgentModal && subAgentParent && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card w-full max-w-md p-6 rounded-2xl border border-slate-800 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Users className="w-5 h-5 text-purple-400" />
                  Add Sub-Agent / Team Member
                </h3>
                <p className="text-xs text-purple-300 mt-0.5">
                  Agency: <span className="font-semibold text-white">{subAgentParent.name}</span> ({subAgentParent.plan.toUpperCase()} Plan)
                </p>
              </div>
              <button onClick={() => setShowAddSubAgentModal(false)} className="text-slate-400 hover:text-white">&times;</button>
            </div>

            <form onSubmit={handleCreateSubAgent} className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Agent Full Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Rauf Əliyev"
                  value={subAgentForm.name}
                  onChange={(e) => setSubAgentForm({ ...subAgentForm, name: e.target.value })}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Phone Number *</label>
                <input
                  type="text"
                  required
                  placeholder="+994501234567"
                  value={subAgentForm.phone}
                  onChange={(e) => setSubAgentForm({ ...subAgentForm, phone: e.target.value })}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                />
              </div>

              {/* Connected Channels Checkboxes */}
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Qoşulacaq Bildiriş Kanalları ({subAgentForm.preferred_channel === 'both' ? '⚡ Hər İkisi (WhatsApp + Telegram)' : subAgentForm.preferred_channel === 'whatsapp' ? '💬 Yalnız WhatsApp' : '🤖 Yalnız Telegram'})
                </label>
                <div className="grid grid-cols-2 gap-2.5 mb-2">
                  <label className={`flex items-center gap-2.5 p-2.5 rounded-xl border cursor-pointer transition ${
                    (subAgentForm.preferred_channel === 'whatsapp' || subAgentForm.preferred_channel === 'both')
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                      : 'bg-dark-800 border-slate-700/60 text-slate-400'
                  }`}>
                    <input
                      type="checkbox"
                      checked={subAgentForm.preferred_channel === 'whatsapp' || subAgentForm.preferred_channel === 'both'}
                      onChange={(e) => {
                        const isTg = subAgentForm.preferred_channel === 'telegram' || subAgentForm.preferred_channel === 'both';
                        const next = e.target.checked ? (isTg ? 'both' : 'whatsapp') : (isTg ? 'telegram' : 'whatsapp');
                        setSubAgentForm({ ...subAgentForm, preferred_channel: next });
                      }}
                      className="w-4 h-4 rounded border-slate-700 text-emerald-600 focus:ring-emerald-500"
                    />
                    <div>
                      <div className="text-xs font-bold text-slate-200">WhatsApp</div>
                      <div className="text-[10px] text-slate-400">Elan bildirişləri</div>
                    </div>
                  </label>

                  <label className={`flex items-center gap-2.5 p-2.5 rounded-xl border cursor-pointer transition ${
                    (subAgentForm.preferred_channel === 'telegram' || subAgentForm.preferred_channel === 'both')
                      ? 'bg-blue-500/10 border-blue-500/30 text-blue-300'
                      : 'bg-dark-800 border-slate-700/60 text-slate-400'
                  }`}>
                    <input
                      type="checkbox"
                      checked={subAgentForm.preferred_channel === 'telegram' || subAgentForm.preferred_channel === 'both'}
                      onChange={(e) => {
                        const isWa = subAgentForm.preferred_channel === 'whatsapp' || subAgentForm.preferred_channel === 'both';
                        const next = e.target.checked ? (isWa ? 'both' : 'telegram') : (isWa ? 'whatsapp' : 'telegram');
                        setSubAgentForm({ ...subAgentForm, preferred_channel: next });
                      }}
                      className="w-4 h-4 rounded border-slate-700 text-blue-600 focus:ring-blue-500"
                    />
                    <div>
                      <div className="text-xs font-bold text-slate-200">Telegram Botu</div>
                      <div className="text-[10px] text-slate-400">Elan bildirişləri</div>
                    </div>
                  </label>
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">WhatsApp Nömrəsi</label>
                <input
                  type="text"
                  placeholder="+994501234567"
                  value={subAgentForm.whatsapp_number}
                  onChange={(e) => setSubAgentForm({ ...subAgentForm, whatsapp_number: e.target.value })}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Telegram Chat ID / Username</label>
                <input
                  type="text"
                  placeholder="@agent_username or 123456789"
                  value={subAgentForm.telegram_chat_id}
                  onChange={(e) => setSubAgentForm({ ...subAgentForm, telegram_chat_id: e.target.value })}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1.5 flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 text-emerald-400" />
                  Assigned Territories (Automatic District Routing)
                </label>
                <div className="grid grid-cols-2 gap-1.5 max-h-36 overflow-y-auto p-2 bg-dark-800/80 rounded-xl border border-slate-700/60">
                  {BAKU_DISTRICT_OPTIONS.map((dist) => {
                    const isSelected = subAgentForm.assigned_districts.includes(dist);
                    return (
                      <button
                        type="button"
                        key={dist}
                        onClick={() => toggleDistrictAssignment(dist)}
                        className={`text-xs px-2.5 py-1 rounded-lg text-left transition-all ${
                          isSelected
                            ? 'bg-purple-600 text-white font-semibold'
                            : 'bg-dark-700/40 text-slate-300 hover:bg-dark-700'
                        }`}
                      >
                        {isSelected ? '✓ ' : '+ '}{dist}
                      </button>
                    );
                  })}
                </div>
                <p className="text-[11px] text-slate-500 mt-1">When listings in selected districts are found, they route directly to this agent.</p>
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowAddSubAgentModal(false)}
                  className="px-4 py-2 text-sm text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={subAgentLoading}
                  className="px-5 py-2 text-sm font-medium bg-purple-600 hover:bg-purple-500 text-white rounded-xl shadow-lg shadow-purple-500/20 flex items-center gap-1.5"
                >
                  <Plus className="w-4 h-4" />
                  {subAgentLoading ? 'Adding...' : 'Add Team Member'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Tenant Modal */}
      {editTenant && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card w-full max-w-md p-6 rounded-2xl border border-slate-800 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Edit3 className="w-4 h-4 text-blue-400" />
                Edit Tenant Details
              </h3>
              <button onClick={() => setEditTenant(null)} className="text-slate-400 hover:text-white">&times;</button>
            </div>

            <form onSubmit={handleUpdateTenant} className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Full Name / Agency Name</label>
                <input
                  type="text"
                  required
                  value={editFormData.name}
                  onChange={(e) => setEditFormData({ ...editFormData, name: e.target.value })}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Phone Number</label>
                <input
                  type="text"
                  required
                  value={editFormData.phone}
                  onChange={(e) => setEditFormData({ ...editFormData, phone: e.target.value })}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Account Type</label>
                <select
                  value={editFormData.type}
                  onChange={(e) => setEditFormData({ ...editFormData, type: e.target.value as any })}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800"
                >
                  <option value="individual_agent">Individual Agent</option>
                  <option value="agency">Agency / Brokerage</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Subscription Plan</label>
                <select
                  value={editFormData.plan}
                  onChange={(e) => setEditFormData({ ...editFormData, plan: e.target.value as any })}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800 capitalize"
                >
                  {availablePlans.map((p) => (
                    <option key={p.id} value={p.code}>
                      {p.name} ({p.price} {p.currency}) - {p.max_agents || 1} Seats
                    </option>
                  ))}
                </select>
              </div>

              {/* Connected Channels Checkboxes */}
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Qoşulmuş Bildiriş Kanalları ({editFormData.preferred_channel === 'both' ? '⚡ Hər İkisi (WhatsApp + Telegram)' : editFormData.preferred_channel === 'whatsapp' ? '💬 Yalnız WhatsApp' : '🤖 Yalnız Telegram'})
                </label>
                <div className="grid grid-cols-2 gap-2.5 mb-2">
                  <label className={`flex items-center gap-2.5 p-2.5 rounded-xl border cursor-pointer transition ${
                    (editFormData.preferred_channel === 'whatsapp' || editFormData.preferred_channel === 'both')
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                      : 'bg-dark-800 border-slate-700/60 text-slate-400'
                  }`}>
                    <input
                      type="checkbox"
                      checked={editFormData.preferred_channel === 'whatsapp' || editFormData.preferred_channel === 'both'}
                      onChange={(e) => {
                        const isTg = editFormData.preferred_channel === 'telegram' || editFormData.preferred_channel === 'both';
                        const next = e.target.checked ? (isTg ? 'both' : 'whatsapp') : (isTg ? 'telegram' : 'whatsapp');
                        setEditFormData({ ...editFormData, preferred_channel: next });
                      }}
                      className="w-4 h-4 rounded border-slate-700 text-emerald-600 focus:ring-emerald-500"
                    />
                    <div>
                      <div className="text-xs font-bold text-slate-200">WhatsApp</div>
                      <div className="text-[10px] text-slate-400">Elan bildirişləri</div>
                    </div>
                  </label>

                  <label className={`flex items-center gap-2.5 p-2.5 rounded-xl border cursor-pointer transition ${
                    (editFormData.preferred_channel === 'telegram' || editFormData.preferred_channel === 'both')
                      ? 'bg-blue-500/10 border-blue-500/30 text-blue-300'
                      : 'bg-dark-800 border-slate-700/60 text-slate-400'
                  }`}>
                    <input
                      type="checkbox"
                      checked={editFormData.preferred_channel === 'telegram' || editFormData.preferred_channel === 'both'}
                      onChange={(e) => {
                        const isWa = editFormData.preferred_channel === 'whatsapp' || editFormData.preferred_channel === 'both';
                        const next = e.target.checked ? (isWa ? 'both' : 'telegram') : (isWa ? 'whatsapp' : 'telegram');
                        setEditFormData({ ...editFormData, preferred_channel: next });
                      }}
                      className="w-4 h-4 rounded border-slate-700 text-blue-600 focus:ring-blue-500"
                    />
                    <div>
                      <div className="text-xs font-bold text-slate-200">Telegram Botu</div>
                      <div className="text-[10px] text-slate-400">Elan bildirişləri</div>
                    </div>
                  </label>
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">WhatsApp Nömrəsi</label>
                <input
                  type="text"
                  value={editFormData.whatsapp_number || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, whatsapp_number: e.target.value })}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                  placeholder="+994 50 123 45 67"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Telegram Chat ID / Username</label>
                <input
                  type="text"
                  value={editFormData.telegram_chat_id || editFormData.telegram_handle || ''}
                  onChange={(e) => {
                    const val = e.target.value;
                    setEditFormData({
                      ...editFormData,
                      telegram_handle: val,
                      telegram_chat_id: val.replace('@', '')
                    });
                  }}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                  placeholder="12345678 və ya @username"
                />
              </div>

              {/* CRM Mini App Addon */}
              <div className="pt-2 border-t border-slate-800">
                <label className="flex items-center gap-2 p-2.5 bg-dark-800/80 rounded-xl border border-slate-700/60 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={editFormData.feature_crm || false}
                    onChange={(e) => setEditFormData({ ...editFormData, feature_crm: e.target.checked })}
                    className="rounded accent-blue-500"
                  />
                  <div className="flex-1 text-xs">
                    <span className="font-semibold text-indigo-300">💼 Telegram Mini App & Real Estate CRM</span>
                    <p className="text-[11px] text-slate-400">Agentlər üçün /crm &lt;id&gt; əmri, müştəri boru kəməri və TMA interfeysi</p>
                  </div>
                </label>
              </div>

              {/* Agent Portfolio Addon */}
              <div className="pt-2 border-t border-slate-800 space-y-2">
                <label className="flex items-center gap-2 p-2.5 bg-dark-800/80 rounded-xl border border-slate-700/60 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={editFormData.feature_portfolio || false}
                    onChange={(e) => setEditFormData({ ...editFormData, feature_portfolio: e.target.checked })}
                    className="rounded accent-purple-500"
                  />
                  <div className="flex-1 text-xs">
                    <span className="font-semibold text-purple-300">🗂️ Agent Portfeli & Rəqəmsal Vitrin Add-on</span>
                    <p className="text-[11px] text-slate-400">1 kliklə klonlama, təmiz su nişansız müştəri linki (/p/:id) və fərdi vitrin</p>
                  </div>
                </label>
                {editFormData.feature_portfolio && (
                  <div className="space-y-2 pt-1">
                    <div className="flex items-center justify-between px-3 py-2 bg-dark-950 rounded-xl border border-slate-800 text-xs">
                      <span className="text-slate-400">Portfel Limiti (Aktiv Elan Sayı):</span>
                      <div className="flex items-center gap-1.5">
                        <input
                          type="number"
                          min="1"
                          value={editFormData.portfolio_limit || 25}
                          onChange={(e) => setEditFormData({ ...editFormData, portfolio_limit: Number(e.target.value) })}
                          className="w-20 bg-dark-900 border border-slate-700 rounded-lg px-2 py-1 text-white text-xs font-bold text-center"
                        />
                        <span className="text-slate-400">elan</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between px-3 py-2 bg-dark-950 rounded-xl border border-slate-800 text-xs">
                      <span className="text-slate-400">Fərdi Vitrin URL (Slug):</span>
                      <div className="flex items-center gap-1">
                        <span className="text-slate-500 font-mono text-[11px]">/v/</span>
                        <input
                          type="text"
                          placeholder="elnur-emlak"
                          value={editFormData.portfolio_slug || ''}
                          onChange={(e) => setEditFormData({ ...editFormData, portfolio_slug: e.target.value })}
                          className="w-36 bg-dark-900 border border-slate-700 rounded-lg px-2 py-1 text-purple-300 font-mono text-xs focus:border-purple-500"
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Custom Domain Addon */}
              <div className="pt-2 border-t border-slate-800 space-y-2">
                <label className="flex items-center gap-2 p-2.5 bg-dark-800/80 rounded-xl border border-slate-700/60 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={editFormData.feature_custom_domain || false}
                    onChange={(e) => setEditFormData({ ...editFormData, feature_custom_domain: e.target.checked })}
                    className="rounded accent-indigo-500"
                  />
                  <div className="flex-1 text-xs">
                    <span className="font-semibold text-indigo-300">🌐 Fərdi Domen Adı (Custom Domain)</span>
                    <p className="text-[11px] text-slate-400">Agentin öz domeni (məs. samiremlak.az) vitrin və portfel linkləri üçün</p>
                  </div>
                </label>
                {editFormData.feature_custom_domain && (
                  <div className="space-y-2 pt-1">
                    <div className="flex items-center justify-between px-3 py-2 bg-dark-950 rounded-xl border border-slate-800 text-xs">
                      <span className="text-slate-400">Domen Adı:</span>
                      <input
                        type="text"
                        placeholder="samiremlak.az"
                        value={editFormData.custom_domain || ''}
                        onChange={(e) => setEditFormData({ ...editFormData, custom_domain: e.target.value })}
                        className="w-48 bg-dark-900 border border-slate-700 rounded-lg px-2 py-1 text-indigo-300 font-mono text-xs focus:border-indigo-500"
                      />
                    </div>
                    <div className="flex items-center justify-between px-3 py-2 bg-dark-950 rounded-xl border border-slate-800 text-xs">
                      <span className="text-slate-400">Domen Aktivdir:</span>
                      <input
                        type="checkbox"
                        checked={editFormData.custom_domain_enabled ?? true}
                        onChange={(e) => setEditFormData({ ...editFormData, custom_domain_enabled: e.target.checked })}
                        className="rounded accent-indigo-500"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Aged Listings Addon */}
              <div>
                <label className="flex items-center gap-2 p-2.5 bg-dark-800/80 rounded-xl border border-slate-700/60 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={editFormData.feature_aged_listings}
                    onChange={(e) => setEditFormData({ ...editFormData, feature_aged_listings: e.target.checked })}
                    className="rounded accent-emerald-500"
                  />
                  <div className="flex-1 flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-200">Aged Inventory Archive Add-on</span>
                    {editFormData.feature_aged_listings && (
                      <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                        <span className="text-slate-400 text-[11px]">Max:</span>
                        <select
                          value={editFormData.addon_aged_max_months}
                          onChange={(e) => setEditFormData({ ...editFormData, addon_aged_max_months: Number(e.target.value) })}
                          className="bg-dark-900 border border-slate-700 text-emerald-400 rounded-lg px-2 py-0.5 text-xs font-semibold"
                        >
                          <option value={1}>1 Month</option>
                          <option value={3}>3 Months</option>
                          <option value={6}>6 Months</option>
                          <option value={12}>12 Months</option>
                          <option value={24}>24 Months</option>
                        </select>
                      </div>
                    )}
                  </div>
                </label>
              </div>

              {/* Watermark-Free Photos Addon */}
              <div className="p-2.5 bg-dark-800/80 rounded-xl border border-slate-700/60 space-y-2">
                <label className="flex items-center justify-between cursor-pointer text-xs">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={editFormData.feature_watermark_free_images}
                      onChange={(e) => setEditFormData({ ...editFormData, feature_watermark_free_images: e.target.checked })}
                      className="rounded accent-emerald-500"
                    />
                    <span className="font-semibold text-teal-300">Su Nişansız Foto Add-on (Watermark-Free)</span>
                  </div>
                </label>
                {editFormData.feature_watermark_free_images && (
                  <div className="grid grid-cols-2 gap-2 pt-1 border-t border-slate-700/50 text-xs">
                    <div>
                      <label className="text-slate-400 text-[11px] block mb-0.5">Top-up Limit (Foto)</label>
                      <input
                        type="number"
                        min="0"
                        value={editFormData.addon_image_requests_limit}
                        onChange={(e) => setEditFormData({ ...editFormData, addon_image_requests_limit: Number(e.target.value) })}
                        className="w-full bg-dark-900 border border-slate-700 rounded-lg px-2.5 py-1 text-white text-xs font-bold"
                        placeholder="Məs: 25"
                      />
                    </div>
                    <div>
                      <label className="text-slate-400 text-[11px] block mb-0.5">İstifadə Edilən</label>
                      <input
                        type="number"
                        min="0"
                        value={editFormData.addon_image_requests_used}
                        onChange={(e) => setEditFormData({ ...editFormData, addon_image_requests_used: Number(e.target.value) })}
                        className="w-full bg-dark-900 border border-slate-700 rounded-lg px-2.5 py-1 text-white text-xs font-bold"
                        placeholder="0"
                      />
                    </div>
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setEditTenant(null)}
                  className="px-4 py-2 text-sm text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-500 text-white rounded-xl shadow-lg shadow-blue-500/20"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteTenantTarget && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card w-full max-w-sm p-6 rounded-2xl border border-red-500/30 space-y-4">
            <div className="flex items-center gap-3 text-red-400">
              <AlertTriangle className="w-6 h-6" />
              <h3 className="text-base font-bold text-white">Delete Tenant Account</h3>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Are you sure you want to permanently delete <strong className="text-white">{deleteTenantTarget.name}</strong> ({deleteTenantTarget.phone})? This will delete all their saved searches, matches, and sub-agents.
            </p>
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setDeleteTenantTarget(null)}
                className="px-3 py-1.5 text-xs text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deleting}
                onClick={handleDeleteTenant}
                className="px-4 py-1.5 text-xs font-semibold bg-red-600 hover:bg-red-500 text-white rounded-xl shadow-lg shadow-red-500/20"
              >
                {deleting ? 'Deleting...' : 'Confirm Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Tenant Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card w-full max-w-md p-6 rounded-2xl border border-slate-800 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-emerald-400" />
                Add New Agent / Agency
              </h3>
              <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-white">&times;</button>
            </div>

            <form onSubmit={handleCreateTenant} className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Full Name / Agency Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Elnur Məmmədov və ya Real Estate Agency"
                  value={newTenant.name}
                  onChange={(e) => setNewTenant({ ...newTenant, name: e.target.value })}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Phone Number (Login & Identity) *</label>
                <input
                  type="text"
                  required
                  placeholder="+994501234567"
                  value={newTenant.phone}
                  onChange={(e) => setNewTenant({ ...newTenant, phone: e.target.value })}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Account Type</label>
                <select
                  value={newTenant.type}
                  onChange={(e) => setNewTenant({ ...newTenant, type: e.target.value })}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800"
                >
                  <option value="individual_agent">Individual Agent</option>
                  <option value="agency">Agency / Team</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Subscription Plan</label>
                <select
                  value={newTenant.plan}
                  onChange={(e) => setNewTenant({ ...newTenant, plan: e.target.value as any })}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800 capitalize"
                >
                  {availablePlans.map((p) => (
                    <option key={p.id} value={p.code}>
                      {p.name} ({p.sale_enabled && p.sale_price !== undefined ? `${p.sale_price} AZN (🔥 Endirimlə, əvvəl ${p.price} AZN)` : `${p.price} ${p.currency}`}) - {p.max_agents || 1} Seats
                    </option>
                  ))}
                </select>
              </div>

              {/* Connected Channels Checkboxes */}
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Qoşulacaq Bildiriş Kanalları ({newTenant.preferred_channel === 'both' ? '⚡ Hər İkisi (WhatsApp + Telegram)' : newTenant.preferred_channel === 'whatsapp' ? '💬 Yalnız WhatsApp' : '🤖 Yalnız Telegram'})
                </label>
                <div className="grid grid-cols-2 gap-2.5 mb-2">
                  <label className={`flex items-center gap-2.5 p-2.5 rounded-xl border cursor-pointer transition ${
                    (newTenant.preferred_channel === 'whatsapp' || newTenant.preferred_channel === 'both')
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                      : 'bg-dark-800 border-slate-700/60 text-slate-400'
                  }`}>
                    <input
                      type="checkbox"
                      checked={newTenant.preferred_channel === 'whatsapp' || newTenant.preferred_channel === 'both'}
                      onChange={(e) => {
                        const isTg = newTenant.preferred_channel === 'telegram' || newTenant.preferred_channel === 'both';
                        const next = e.target.checked ? (isTg ? 'both' : 'whatsapp') : (isTg ? 'telegram' : 'whatsapp');
                        setNewTenant({ ...newTenant, preferred_channel: next });
                      }}
                      className="w-4 h-4 rounded border-slate-700 text-emerald-600 focus:ring-emerald-500"
                    />
                    <div>
                      <div className="text-xs font-bold text-slate-200">WhatsApp</div>
                      <div className="text-[10px] text-slate-400">Elan bildirişləri</div>
                    </div>
                  </label>

                  <label className={`flex items-center gap-2.5 p-2.5 rounded-xl border cursor-pointer transition ${
                    (newTenant.preferred_channel === 'telegram' || newTenant.preferred_channel === 'both')
                      ? 'bg-blue-500/10 border-blue-500/30 text-blue-300'
                      : 'bg-dark-800 border-slate-700/60 text-slate-400'
                  }`}>
                    <input
                      type="checkbox"
                      checked={newTenant.preferred_channel === 'telegram' || newTenant.preferred_channel === 'both'}
                      onChange={(e) => {
                        const isWa = newTenant.preferred_channel === 'whatsapp' || newTenant.preferred_channel === 'both';
                        const next = e.target.checked ? (isWa ? 'both' : 'telegram') : (isWa ? 'whatsapp' : 'telegram');
                        setNewTenant({ ...newTenant, preferred_channel: next });
                      }}
                      className="w-4 h-4 rounded border-slate-700 text-blue-600 focus:ring-blue-500"
                    />
                    <div>
                      <div className="text-xs font-bold text-slate-200">Telegram Botu</div>
                      <div className="text-[10px] text-slate-400">Elan bildirişləri</div>
                    </div>
                  </label>
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">WhatsApp Nömrəsi</label>
                <input
                  type="text"
                  placeholder="+994501234567"
                  value={newTenant.whatsapp_number}
                  onChange={(e) => setNewTenant({ ...newTenant, whatsapp_number: e.target.value })}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Telegram Chat ID / İstifadəçi Adı</label>
                <input
                  type="text"
                  placeholder="12345678 və ya @agent_username"
                  value={newTenant.telegram_chat_id || newTenant.telegram_handle}
                  onChange={(e) => {
                    const val = e.target.value;
                    setNewTenant({
                      ...newTenant,
                      telegram_handle: val,
                      telegram_chat_id: val.replace('@', '')
                    });
                  }}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                />
              </div>

              {/* CRM Mini App Addon */}
              <div className="pt-2 border-t border-slate-800">
                <label className="flex items-center gap-2 p-2.5 bg-dark-800/80 rounded-xl border border-slate-700/60 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={newTenant.feature_crm || false}
                    onChange={(e) => setNewTenant({ ...newTenant, feature_crm: e.target.checked })}
                    className="rounded accent-blue-500"
                  />
                  <div className="flex-1 text-xs">
                    <span className="font-semibold text-indigo-300">💼 Telegram Mini App & Real Estate CRM</span>
                    <p className="text-[11px] text-slate-400">Agentlər üçün /crm &lt;id&gt; əmri və TMA boru kəməri</p>
                  </div>
                </label>
              </div>

              {/* Agent Portfolio Addon */}
              <div className="pt-2 border-t border-slate-800 space-y-2">
                <label className="flex items-center gap-2 p-2.5 bg-dark-800/80 rounded-xl border border-slate-700/60 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={newTenant.feature_portfolio || false}
                    onChange={(e) => setNewTenant({ ...newTenant, feature_portfolio: e.target.checked })}
                    className="rounded accent-purple-500"
                  />
                  <div className="flex-1 text-xs">
                    <span className="font-semibold text-purple-300">🗂️ Agent Portfeli & Rəqəmsal Vitrin Add-on</span>
                    <p className="text-[11px] text-slate-400">1 kliklə klonlama, təmiz su nişansız müştəri linki (/p/:id) və fərdi vitrin</p>
                  </div>
                </label>
                {newTenant.feature_portfolio && (
                  <div className="space-y-2 pt-1">
                    <div className="flex items-center justify-between px-3 py-2 bg-dark-950 rounded-xl border border-slate-800 text-xs">
                      <span className="text-slate-400">Portfel Limiti (Aktiv Elan Sayı):</span>
                      <div className="flex items-center gap-1.5">
                        <input
                          type="number"
                          min="1"
                          value={newTenant.portfolio_limit || 25}
                          onChange={(e) => setNewTenant({ ...newTenant, portfolio_limit: Number(e.target.value) })}
                          className="w-20 bg-dark-900 border border-slate-700 rounded-lg px-2 py-1 text-white text-xs font-bold text-center"
                        />
                        <span className="text-slate-400">elan</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between px-3 py-2 bg-dark-950 rounded-xl border border-slate-800 text-xs">
                      <span className="text-slate-400">Fərdi Vitrin URL (Slug):</span>
                      <div className="flex items-center gap-1">
                        <span className="text-slate-500 font-mono text-[11px]">/v/</span>
                        <input
                          type="text"
                          placeholder="elnur-emlak (boş qalsa avtomatik yaradılacaq)"
                          value={newTenant.portfolio_slug || ''}
                          onChange={(e) => setNewTenant({ ...newTenant, portfolio_slug: e.target.value })}
                          className="w-48 bg-dark-900 border border-slate-700 rounded-lg px-2 py-1 text-purple-300 font-mono text-xs focus:border-purple-500"
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Custom Domain Addon */}
              <div className="pt-2 border-t border-slate-800 space-y-2">
                <label className="flex items-center gap-2 p-2.5 bg-dark-800/80 rounded-xl border border-slate-700/60 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={newTenant.feature_custom_domain || false}
                    onChange={(e) => setNewTenant({ ...newTenant, feature_custom_domain: e.target.checked })}
                    className="rounded accent-indigo-500"
                  />
                  <div className="flex-1 text-xs">
                    <span className="font-semibold text-indigo-300">🌐 Fərdi Domen Adı (Custom Domain)</span>
                    <p className="text-[11px] text-slate-400">Agentin öz domeni (məs. samiremlak.az) vitrin və portfel linkləri üçün</p>
                  </div>
                </label>
                {newTenant.feature_custom_domain && (
                  <div className="space-y-2 pt-1">
                    <div className="flex items-center justify-between px-3 py-2 bg-dark-950 rounded-xl border border-slate-800 text-xs">
                      <span className="text-slate-400">Domen Adı:</span>
                      <input
                        type="text"
                        placeholder="samiremlak.az"
                        value={newTenant.custom_domain || ''}
                        onChange={(e) => setNewTenant({ ...newTenant, custom_domain: e.target.value })}
                        className="w-48 bg-dark-900 border border-slate-700 rounded-lg px-2 py-1 text-indigo-300 font-mono text-xs focus:border-indigo-500"
                      />
                    </div>
                    <div className="flex items-center justify-between px-3 py-2 bg-dark-950 rounded-xl border border-slate-800 text-xs">
                      <span className="text-slate-400">Domen Aktivdir:</span>
                      <input
                        type="checkbox"
                        checked={newTenant.custom_domain_enabled ?? true}
                        onChange={(e) => setNewTenant({ ...newTenant, custom_domain_enabled: e.target.checked })}
                        className="rounded accent-indigo-500"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Aged Listings Addon */}
              <div>
                <label className="flex items-center gap-2 p-2.5 bg-dark-800/80 rounded-xl border border-slate-700/60 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={newTenant.feature_aged_listings}
                    onChange={(e) => setNewTenant({ ...newTenant, feature_aged_listings: e.target.checked })}
                    className="rounded accent-emerald-500"
                  />
                  <div className="flex-1 flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-200">Aged Inventory Archive Add-on</span>
                    {newTenant.feature_aged_listings && (
                      <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                        <span className="text-slate-400 text-[11px]">Max:</span>
                        <select
                          value={newTenant.addon_aged_max_months}
                          onChange={(e) => setNewTenant({ ...newTenant, addon_aged_max_months: Number(e.target.value) })}
                          className="bg-dark-900 border border-slate-700 text-emerald-400 rounded-lg px-2 py-0.5 text-xs font-semibold"
                        >
                          <option value={1}>1 Month</option>
                          <option value={3}>3 Months</option>
                          <option value={6}>6 Months</option>
                          <option value={12}>12 Months</option>
                          <option value={24}>24 Months</option>
                        </select>
                      </div>
                    )}
                  </div>
                </label>
              </div>

              {/* Watermark-Free Photos Addon */}
              <div className="p-2.5 bg-dark-800/80 rounded-xl border border-slate-700/60 space-y-2">
                <label className="flex items-center justify-between cursor-pointer text-xs">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={newTenant.feature_watermark_free_images}
                      onChange={(e) => setNewTenant({ ...newTenant, feature_watermark_free_images: e.target.checked })}
                      className="rounded accent-emerald-500"
                    />
                    <span className="font-semibold text-teal-300">Su Nişansız Foto Add-on (Watermark-Free)</span>
                  </div>
                </label>
                {newTenant.feature_watermark_free_images && (
                  <div className="pt-1 border-t border-slate-700/50 text-xs">
                    <label className="text-slate-400 text-[11px] block mb-0.5">İlkin Foto Limiti (Sorğu Sayı)</label>
                    <input
                      type="number"
                      min="0"
                      value={newTenant.addon_image_requests_limit}
                      onChange={(e) => setNewTenant({ ...newTenant, addon_image_requests_limit: Number(e.target.value) })}
                      className="w-full bg-dark-900 border border-slate-700 rounded-lg px-2.5 py-1 text-white text-xs font-bold"
                      placeholder="Məs: 25"
                    />
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-sm text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-sm font-medium bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl shadow-lg shadow-emerald-500/20 flex items-center gap-1.5"
                >
                  <Plus className="w-4 h-4" />
                  Create Agent
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Cash Payment Modal */}
      {paymentModalTenant && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card w-full max-w-md p-6 rounded-2xl border border-slate-800 space-y-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-emerald-400" />
                Record Cash Payment & Activate
              </h3>
              <button onClick={() => setPaymentModalTenant(null)} className="text-slate-400 hover:text-white">&times;</button>
            </div>

            <form onSubmit={handleRecordCashPayment} className="space-y-3">
              {/* Payment Category Selector */}
              <div>
                <label className="text-xs text-slate-400 block mb-1">Payment Type / Item</label>
                <div className="grid grid-cols-3 gap-1.5 p-1 bg-dark-900 rounded-xl border border-slate-800 text-xs font-medium">
                  <button
                    type="button"
                    onClick={() => handlePlanOrPeriodChange(paymentPlan, cashDays, cashIncludeAgedListings, 'full')}
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
                    onClick={() => handlePlanOrPeriodChange(paymentPlan, cashDays, true, 'addon_only')}
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
                    onClick={() => handlePlanOrPeriodChange(paymentPlan, cashDays, false, 'plan_only')}
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

              {paymentCategory !== 'addon_only' && (
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Subscription Plan</label>
                  <select
                    value={paymentPlan}
                    onChange={(e) => handlePlanOrPeriodChange(e.target.value, cashDays, cashIncludeAgedListings, paymentCategory)}
                    className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800 capitalize"
                  >
                    {availablePlans.map((p) => (
                      <option key={p.id} value={p.code}>
                        {p.name} ({p.sale_enabled && p.sale_price !== undefined ? `${p.sale_price} AZN (🔥 Endirimlə, əvvəl ${p.price} AZN)` : `${p.price} ${p.currency}`}) - {p.max_agents || 1} Seats
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">
                    {paymentCategory === 'addon_only' ? 'Add-on Fee (AZN)' : 'Amount Paid (AZN)'}
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={cashAmount}
                    onChange={(e) => setCashAmount(Number(e.target.value))}
                    className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white font-bold"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Coverage Period</label>
                  <select
                    value={cashDays}
                    onChange={(e) => handlePlanOrPeriodChange(paymentPlan, Number(e.target.value), cashIncludeAgedListings, paymentCategory)}
                    className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800"
                  >
                    <option value={30}>1 Month (30 Days)</option>
                    <option value={60}>2 Months (60 Days)</option>
                    <option value={90}>3 Months (90 Days)</option>
                    <option value={180}>6 Months (180 Days)</option>
                    <option value={365}>1 Year (365 Days)</option>
                  </select>
                </div>
              </div>

              {/* Aged Listings Add-on Option */}
              {paymentCategory === 'full' && (
                <div className="p-3 bg-dark-900/80 rounded-xl border border-slate-800 space-y-2">
                  <label className="flex items-center justify-between cursor-pointer">
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={cashIncludeAgedListings}
                        onChange={(e) => {
                          const val = e.target.checked;
                          setCashIncludeAgedListings(val);
                          handlePlanOrPeriodChange(paymentPlan, cashDays, val, paymentCategory);
                        }}
                        className="rounded accent-emerald-500"
                      />
                      <span className="text-xs font-semibold text-slate-200">
                        Include Aged Active Listings Add-on
                      </span>
                    </div>
                    <span className="text-[11px] text-purple-400 font-mono font-semibold">
                      +{((availablePlans.find(p => p.code === paymentPlan)?.addon_aged_listings_price) ?? 15)} AZN/mo
                    </span>
                  </label>

                  {cashIncludeAgedListings && (
                    <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 text-xs">
                      <span className="text-slate-400">Historical Lookback Limit:</span>
                      <select
                        value={cashAgedMaxMonths}
                        onChange={(e) => setCashAgedMaxMonths(Number(e.target.value))}
                        className="bg-dark-800 border border-slate-700 text-white rounded-lg px-2 py-1 text-xs font-medium"
                      >
                        <option value={1}>1 Month</option>
                        <option value={3}>3 Months</option>
                        <option value={6}>6 Months</option>
                        <option value={12}>12 Months (1 Year)</option>
                        <option value={24}>24 Months (2 Years)</option>
                      </select>
                    </div>
                  )}
                </div>
              )}

              {paymentCategory === 'addon_only' && (
                <div className="p-3 bg-purple-950/20 rounded-xl border border-purple-500/30 space-y-2 text-xs">
                  <div className="flex items-center justify-between text-purple-300 font-semibold">
                    <span>Aged Listings Archive Add-on</span>
                    <span>15 AZN / month</span>
                  </div>
                  <div className="flex items-center justify-between pt-1 border-t border-purple-500/20">
                    <span className="text-slate-400">Historical Lookback Limit:</span>
                    <select
                      value={cashAgedMaxMonths}
                      onChange={(e) => setCashAgedMaxMonths(Number(e.target.value))}
                      className="bg-dark-800 border border-slate-700 text-white rounded-lg px-2 py-1 text-xs font-medium"
                    >
                      <option value={1}>1 Month</option>
                      <option value={3}>3 Months</option>
                      <option value={6}>6 Months</option>
                      <option value={12}>12 Months (1 Year)</option>
                      <option value={24}>24 Months (2 Years)</option>
                    </select>
                  </div>
                </div>
              )}

              {/* Extra Search Slots Add-on Option */}
              {(paymentCategory === 'full' || paymentCategory === 'addon_only') && (
                <div className="p-3 bg-dark-900/80 rounded-xl border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-cyan-300 flex items-center gap-1.5">
                      <Search className="w-3.5 h-3.5" />
                      Extra Search Slots Add-on
                    </span>
                    <span className="text-[11px] text-teal-400 font-mono font-semibold">
                      +{((availablePlans.find(p => p.code === paymentPlan)?.addon_saved_searches_price) ?? 10)} AZN / +5 slots
                    </span>
                  </div>
                  <div className="grid grid-cols-4 gap-1.5 pt-1 text-xs">
                    {[0, 5, 10, 25].map((slots) => (
                      <button
                        type="button"
                        key={slots}
                        onClick={() => handlePlanOrPeriodChange(paymentPlan, cashDays, cashIncludeAgedListings, paymentCategory, slots, cashExtraImages, cashFeatureImages)}
                        className={`py-1.5 rounded-lg font-mono text-center transition-all ${
                          cashExtraSearches === slots
                            ? 'bg-cyan-500 text-dark-950 font-bold shadow-md'
                            : 'bg-dark-800 text-slate-300 hover:bg-dark-700 border border-slate-700/60'
                        }`}
                      >
                        {slots === 0 ? '0 Slots' : `+${slots} Slots`}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Watermark-Free Photos Add-on Option */}
              {(paymentCategory === 'full' || paymentCategory === 'addon_only') && (
                <div className="p-3 bg-dark-900/80 rounded-xl border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-teal-300 flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5" />
                      Su Nişansız Foto Paketi (Watermark-Free)
                    </span>
                    <span className="text-[11px] text-teal-400 font-mono font-semibold">
                      +{((availablePlans.find(p => p.code === paymentPlan)?.addon_image_requests_price) ?? 10)} AZN / +25 foto
                    </span>
                  </div>
                  <div className="grid grid-cols-4 gap-1.5 pt-1 text-xs">
                    {[0, 25, 50, 100].map((requests) => (
                      <button
                        type="button"
                        key={requests}
                        onClick={() => handlePlanOrPeriodChange(paymentPlan, cashDays, cashIncludeAgedListings, paymentCategory, cashExtraSearches, requests, requests > 0)}
                        className={`py-1.5 rounded-lg font-mono text-center transition-all ${
                          cashExtraImages === requests
                            ? 'bg-teal-500 text-dark-950 font-bold shadow-md'
                            : 'bg-dark-800 text-slate-300 hover:bg-dark-700 border border-slate-700/60'
                        }`}
                      >
                        {requests === 0 ? '0 Foto' : `+${requests} Foto`}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Telegram Mini App & CRM Add-on Option */}
              {(paymentCategory === 'full' || paymentCategory === 'addon_only') && (
                <div className="p-3 bg-dark-900/80 rounded-xl border border-indigo-500/30 space-y-2">
                  <label className="flex items-center justify-between cursor-pointer">
                    <div className="flex items-center gap-2.5">
                      <input
                        type="checkbox"
                        checked={cashIncludeCrm}
                        onChange={(e) => {
                          const val = e.target.checked;
                          setCashIncludeCrm(val);
                          handlePlanOrPeriodChange(paymentPlan, cashDays, cashIncludeAgedListings, paymentCategory, cashExtraSearches, cashExtraImages, cashFeatureImages, val);
                        }}
                        className="w-4 h-4 rounded accent-indigo-500"
                      />
                      <div>
                        <span className="text-xs font-semibold text-indigo-200 block">
                          💼 Telegram Mini App & Real Estate CRM Add-on
                        </span>
                        <span className="text-[10px] text-slate-400">
                          Agent üçün /crm əmri və TMA müştəri boru kəmərini aktivləşdirir
                        </span>
                      </div>
                    </div>
                    <span className="text-[11px] text-indigo-400 font-mono font-semibold">
                      +{((availablePlans.find(p => p.code === paymentPlan)?.addon_crm_price) ?? 15)} AZN/ay
                    </span>
                  </label>
                </div>
              )}

              {/* Agent Portfolio & Digital Showcase Add-on Option */}
              {(paymentCategory === 'full' || paymentCategory === 'addon_only') && (
                <div className="p-3 bg-dark-900/80 rounded-xl border border-blue-500/30 space-y-2">
                  <label className="flex items-center justify-between cursor-pointer">
                    <div className="flex items-center gap-2.5">
                      <input
                        type="checkbox"
                        checked={cashIncludePortfolio}
                        onChange={(e) => {
                          const val = e.target.checked;
                          setCashIncludePortfolio(val);
                          handlePlanOrPeriodChange(paymentPlan, cashDays, cashIncludeAgedListings, paymentCategory, cashExtraSearches, cashExtraImages, cashFeatureImages, cashIncludeCrm, val, cashPortfolioLimit, cashPortfolioPrice, cashIncludeCustomDomain, cashCustomDomainPrice);
                        }}
                        className="w-4 h-4 rounded accent-blue-500"
                      />
                      <div>
                        <span className="text-xs font-semibold text-blue-200 block">
                          🗂️ Agent Portfeli & Rəqəmsal Vitrin Add-on
                        </span>
                        <span className="text-[10px] text-slate-400">
                          1-kliklə elan əlavəsi, fərdi brendinq və ictimai müştəri vitrini
                        </span>
                      </div>
                    </div>
                    <span className="text-[11px] text-blue-400 font-mono font-semibold">
                      +{cashPortfolioPrice || ((availablePlans.find(p => p.code === paymentPlan)?.addon_portfolio_price) ?? 15)} AZN/ay
                    </span>
                  </label>

                  {cashIncludePortfolio && (
                    <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 text-xs">
                      <span className="text-slate-400">Maksimum Portfel Elan Limiti:</span>
                      <select
                        value={cashPortfolioLimit}
                        onChange={(e) => {
                          const lim = Number(e.target.value);
                          setCashPortfolioLimit(lim);
                          handlePlanOrPeriodChange(paymentPlan, cashDays, cashIncludeAgedListings, paymentCategory, cashExtraSearches, cashExtraImages, cashFeatureImages, cashIncludeCrm, true, lim, cashPortfolioPrice, cashIncludeCustomDomain, cashCustomDomainPrice);
                        }}
                        className="bg-dark-800 border border-slate-700 text-white rounded-lg px-2 py-1 text-xs font-medium"
                      >
                        <option value={25}>25 Elan (Standart)</option>
                        <option value={50}>50 Elan (Genişləndirilmiş)</option>
                        <option value={100}>100 Elan (Pro)</option>
                        <option value={250}>250 Elan (Agency / Limitsiz)</option>
                      </select>
                    </div>
                  )}
                </div>
              )}

              {/* Agent Custom Domain Add-on Option */}
              {(paymentCategory === 'full' || paymentCategory === 'addon_only') && (
                <div className="p-3 bg-dark-900/80 rounded-xl border border-indigo-500/30 space-y-2">
                  <label className="flex items-center justify-between cursor-pointer">
                    <div className="flex items-center gap-2.5">
                      <input
                        type="checkbox"
                        checked={cashIncludeCustomDomain}
                        onChange={(e) => {
                          const val = e.target.checked;
                          setCashIncludeCustomDomain(val);
                          handlePlanOrPeriodChange(paymentPlan, cashDays, cashIncludeAgedListings, paymentCategory, cashExtraSearches, cashExtraImages, cashFeatureImages, cashIncludeCrm, cashIncludePortfolio, cashPortfolioLimit, cashPortfolioPrice, val, cashCustomDomainPrice);
                        }}
                        className="w-4 h-4 rounded accent-indigo-500"
                      />
                      <div>
                        <span className="text-xs font-semibold text-indigo-200 block">
                          🌐 Fərdi Domen Adı Add-on (Custom Domain)
                        </span>
                        <span className="text-[10px] text-slate-400">
                          Agentin öz fərdi domeni ilə portfel vitrini (məs: samiremlak.az)
                        </span>
                      </div>
                    </div>
                    <span className="text-[11px] text-indigo-400 font-mono font-semibold">
                      +{cashCustomDomainPrice || ((availablePlans.find(p => p.code === paymentPlan)?.addon_custom_domain_price) ?? 5.0)} AZN/ay
                    </span>
                  </label>
                </div>
              )}

              <div>
                <label className="text-xs text-slate-400 block mb-1">Payment Reference / Notes</label>
                <textarea
                  rows={2}
                  value={cashNotes}
                  onChange={(e) => setCashNotes(e.target.value)}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setPaymentModalTenant(null)}
                  className="px-4 py-2 text-sm text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-sm font-medium bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl flex items-center gap-1.5 shadow-lg shadow-emerald-500/20"
                >
                  <CheckCircle className="w-4 h-4" />
                  Confirm Cash & Activate Account
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Tenant Detail Modal */}
      {selectedTenant && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card w-full max-w-lg p-6 rounded-2xl border border-slate-800 space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex justify-between items-center">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded-md bg-dark-900 border border-emerald-500/30 text-emerald-400 font-mono font-bold text-xs">
                    #{selectedTenant.tenant.id} (tenant_{selectedTenant.tenant.id})
                  </span>
                  <h3 className="text-lg font-bold text-white">{selectedTenant.tenant.name}</h3>
                </div>
                <span className="text-xs text-purple-400 font-mono capitalize block mt-1">{selectedTenant.tenant.type.replace('_', ' ')}</span>
              </div>
              <button onClick={() => setSelectedTenant(null)} className="text-slate-400 hover:text-white text-xl font-bold">&times;</button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs bg-dark-700/40 p-3 rounded-xl">
              <div><span className="text-slate-400">Phone:</span> {selectedTenant.tenant.phone}</div>
              <div><span className="text-slate-400">Plan:</span> {selectedTenant.tenant.plan}</div>
              <div><span className="text-slate-400">Channel:</span> {selectedTenant.tenant.preferred_channel}</div>
              <div><span className="text-slate-400">Status:</span> {selectedTenant.tenant.status}</div>
              <div className="col-span-2 flex items-center gap-2 pt-1 border-t border-slate-700/50">
                <span className="text-slate-400">Multi-Location Search:</span>
                {selectedTenant.tenant.feature_multi_location ? (
                  <span className="text-blue-400 font-semibold flex items-center gap-1">
                    ✓ Active (Up to {selectedTenant.tenant.max_locations_per_search || 5} Areas / Metros)
                  </span>
                ) : (
                  <span className="text-slate-500 font-normal">Single Location Only</span>
                )}
              </div>
              <div className="col-span-2 flex items-center gap-2 pt-1 border-t border-slate-700/50">
                <span className="text-slate-400">Aged Listings Archive:</span>
                {selectedTenant.tenant.feature_aged_listings ? (
                  <span className="text-emerald-400 font-semibold flex items-center gap-1">
                    ✓ Active (Up to {selectedTenant.tenant.addon_aged_max_months || 12} Months Lookback)
                  </span>
                ) : (
                  <span className="text-slate-500 font-normal">Add-on Not Active</span>
                )}
              </div>
            </div>

              {/* Saved Search Limits & Top-Up Add-on Box */}
            <div className="p-3 bg-dark-900 border border-cyan-500/30 rounded-xl space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-cyan-300 flex items-center gap-1.5">
                  <Search className="w-4 h-4" /> Saved Search Limits & Add-ons
                </span>
                <span className="font-mono text-cyan-400 font-bold bg-cyan-500/10 px-2 py-0.5 rounded-lg border border-cyan-500/20">
                  {selectedTenant.saved_searches?.filter(s => s.is_active).length || 0} / {selectedTenant.tenant.max_saved_searches || 10} Active
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-slate-300 text-[11px] pt-1">
                <div>Base Plan Limit: <strong className="text-white font-mono">{(selectedTenant.tenant.max_saved_searches || 10) - (selectedTenant.tenant.addon_saved_searches || 0)}</strong></div>
                <div>Extra Add-on Slots: <strong className="text-teal-400 font-mono">+{selectedTenant.tenant.addon_saved_searches || 0} Slots</strong></div>
              </div>
            </div>

            {/* Watermark-Free Photos Box */}
            {selectedTenant.tenant.feature_watermark_free_images && (
              <div className="p-3 bg-dark-900 border border-teal-500/30 rounded-xl space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-teal-300 flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4" /> Su Nişansız Şəkil Sorğuları
                  </span>
                  <span className="font-mono text-teal-400 font-bold bg-teal-500/10 px-2 py-0.5 rounded-lg border border-teal-500/20">
                    {selectedTenant.tenant.addon_image_requests_used || 0} / {selectedTenant.tenant.addon_image_requests_limit || 0} İstifadə Edilib
                  </span>
                </div>
                <div className="text-slate-300 text-[11px] pt-1 flex justify-between items-center">
                  <span>Qalan Sorğu Limiti:</span>
                  <strong className="text-emerald-400 font-mono">
                    {Math.max(0, (selectedTenant.tenant.addon_image_requests_limit || 0) - (selectedTenant.tenant.addon_image_requests_used || 0))} Şəkil
                  </strong>
                </div>
              </div>
            )}

            {/* Agency Team Members Section */}
            {(selectedTenant.tenant.type === 'agency' || (selectedTenant.sub_agents && selectedTenant.sub_agents.length > 0)) && (
              <div className="p-4 bg-dark-900 border border-purple-500/30 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-purple-300 flex items-center gap-1.5">
                    <Users className="w-4 h-4" /> Team Members & Sub-Agents ({selectedTenant.sub_agents?.length || 0})
                  </span>
                  <button
                    onClick={() => openAddSubAgentModal(selectedTenant.tenant)}
                    className="text-[11px] px-2.5 py-1 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-semibold flex items-center gap-1"
                  >
                    <Plus className="w-3 h-3" />
                    Add Sub-Agent
                  </button>
                </div>

                <div className="space-y-2">
                  {selectedTenant.sub_agents && selectedTenant.sub_agents.length > 0 ? (
                    selectedTenant.sub_agents.map(sa => (
                      <div key={sa.id} className="p-2.5 rounded-xl bg-dark-800 border border-slate-700/60 flex items-center justify-between text-xs">
                        <div>
                          <div className="font-semibold text-white">{sa.name}</div>
                          <div className="text-slate-400 text-[11px]">{sa.phone} • {sa.preferred_channel}</div>
                          {sa.assigned_districts && sa.assigned_districts.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-1">
                              {sa.assigned_districts.map((d: string) => (
                                <span key={d} className="text-[10px] bg-purple-500/20 text-purple-300 px-1.5 py-0.2 rounded font-mono">
                                  {d}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                        <button
                          onClick={() => setDeleteTenantTarget(sa)}
                          className="text-red-400 hover:text-red-300 p-1.5"
                          title="Remove Sub-Agent"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-slate-500 italic p-2 text-center">
                      No sub-agents added yet. Click 'Add Sub-Agent' above to assign seats to team members.
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* WhatsApp Connection Card */}
            {selectedTenant.tenant.preferred_channel === 'whatsapp' && (
              <div className="p-4 bg-dark-900 border border-emerald-500/30 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-emerald-400 flex items-center gap-1.5">
                    <QrCode className="w-4 h-4" /> WhatsApp Pairing Status
                  </span>
                  <button
                    onClick={() => generateWhatsAppQrCode(`tenant_${selectedTenant.tenant.id}`)}
                    className="text-[11px] px-2.5 py-1 rounded-lg bg-emerald-500/20 text-emerald-300 font-semibold hover:bg-emerald-500/30"
                  >
                    Scan New QR Code
                  </button>
                </div>

                {waQrCode && (
                  <div className="flex flex-col items-center space-y-2 pt-2 bg-white/5 p-3 rounded-xl border border-slate-700">
                    <img src={waQrCode} alt="WhatsApp QR Code" className="w-48 h-48 rounded-lg shadow-lg bg-white p-2" />
                    <span className="text-[11px] text-slate-300 text-center font-medium">
                      Scan with WhatsApp on phone to link this tenant to Evolution API
                    </span>
                  </div>
                )}
              </div>
            )}

            <div>
              <h4 className="text-sm font-semibold text-slate-200 mb-2">Saved Search Criteria ({selectedTenant.saved_searches.length})</h4>
              <div className="space-y-2">
                {selectedTenant.saved_searches.map(s => (
                  <div key={s.id} className="p-3 rounded-xl bg-dark-800 border border-slate-700/50 text-xs flex items-center justify-between">
                    <div className="space-y-1">
                      <div className="font-medium text-emerald-400">#{s.id} {s.name}</div>
                      <div className="text-slate-300">{s.raw_criteria_text}</div>
                      <div className="text-slate-500">
                        District: {s.district || 'Any'} {s.metro_station ? `• Metro: ${s.metro_station}${s.include_adjacent_metro ? ' (+ Qonşu stansiyalar)' : ''}` : ''} | Price: {s.min_price || 0}-{s.max_price || 'Any'} AZN
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteSavedSearch(selectedTenant.tenant.id, s.id)}
                      className="text-red-400 hover:text-red-300 p-1.5 rounded-lg hover:bg-red-500/10 ml-2 shrink-0"
                      title="Delete Saved Search"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                {selectedTenant.saved_searches.length === 0 && (
                  <div className="text-xs text-slate-500 italic">No active saved search criteria set.</div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Move / Reassign Seller Modal */}
      {moveSellerModalTenant && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card w-full max-w-md p-6 rounded-2xl border border-slate-800 space-y-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Store className="w-5 h-5 text-indigo-400" />
                <span>Agenti Satıcıya Köçür / Təyin Et</span>
              </h3>
              <button onClick={() => setMoveSellerModalTenant(null)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-xl space-y-1 text-xs">
              <div className="font-semibold text-white">Agent: {moveSellerModalTenant.name} (#{moveSellerModalTenant.id})</div>
              <div className="text-slate-400">Telefon: {moveSellerModalTenant.phone}</div>
              <div className="text-slate-400">
                Hazırki Satıcı: <span className="text-indigo-300 font-bold">{moveSellerModalTenant.seller_name || 'Direkt / Əsas Platforma'}</span>
              </div>
            </div>

            <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-xs text-emerald-300 flex items-start gap-2">
              <ShieldCheck className="w-4 h-4 shrink-0 mt-0.5" />
              <span>
                <strong>Təhlükəsiz Köçürmə:</strong> Agent satıcıya köçürüldükdə və ya direkt platformaya keçirildikdə onun aktiv axtarışları, plan müddəti və bildiriş parametrləri 100% toxunulmaz qalır.
              </span>
            </div>

            <form onSubmit={handleMoveSeller} className="space-y-4 pt-2">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">Yeni Satıcı Hesabını Seçin *</label>
                <select
                  value={selectedSellerId}
                  onChange={(e) => setSelectedSellerId(e.target.value === '' ? '' : Number(e.target.value))}
                  className="w-full glass-input px-3.5 py-2.5 rounded-xl text-sm text-white bg-slate-950 border border-slate-700"
                >
                  <option value="">🌐 Direkt Platforma (Satıcısız / Əsas Hesab)</option>
                  {sellers.map((s) => (
                    <option key={s.id} value={s.id}>
                      🏢 {s.name} ({s.company_name || 'Satıcı'}) — {s.rank}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setMoveSellerModalTenant(null)}
                  className="w-1/2 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-medium transition"
                >
                  Ləğv et
                </button>
                <button
                  type="submit"
                  disabled={movingSeller}
                  className="w-1/2 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-indigo-500/25 transition disabled:opacity-50"
                >
                  {movingSeller ? 'Köçürülür...' : 'Təsdiqlə və Köçür'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
