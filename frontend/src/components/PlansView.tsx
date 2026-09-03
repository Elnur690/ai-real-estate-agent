import React, { useEffect, useState } from 'react';
import { Package, Plus, Check, X, Edit3, ShieldAlert, Sparkles, Users, RefreshCw, Layers, Search, Trash2 } from 'lucide-react';
import api from '../api';

export interface PlanItem {
  id: number;
  code: string;
  name: string;
  description?: string;
  price: number;
  currency: string;
  billing_period: string;
  trial_days?: number;
  is_active: boolean;
  max_agents: number;
  max_saved_searches?: number;
  addon_saved_searches?: number;
  addon_saved_searches_price?: number;
  addon_search_tiers?: Array<{ searches: number; price: number }>;
  feature_makler_detector: boolean;
  feature_avm_bargain_finder: boolean;
  feature_social_brochure: boolean;
  feature_client_intake_bot: boolean;
  feature_multi_location?: boolean;
  max_locations_per_search?: number;
  feature_aged_listings?: boolean;
  addon_aged_listings_price?: number;
  addon_aged_max_months?: number;
  addon_aged_tiers?: Array<{ months: number; price: number }>;
  feature_watermark_free_images?: boolean;
  included_image_requests?: number;
  addon_image_requests_price?: number;
  addon_image_tiers?: Array<{ requests: number; price: number }>;
  feature_crm?: boolean;
  addon_crm_price?: number;
  addon_crm_tiers?: Array<{ months: number; price: number }>;
  feature_portfolio?: boolean;
  addon_portfolio_price?: number;
  addon_portfolio_limit?: number;
  addon_portfolio_tiers?: Array<{ listings: number; price: number }>;
  sale_enabled?: boolean;
  sale_price?: number;
  sale_discount_percent?: number;
  sale_type?: string;
  sale_expires_at?: string;
  sale_badge_label?: string;
  backup_enabled: boolean;
  subscriber_count: number;
}

export function PlansView() {
  const [activeTab, setActiveTab] = useState<'plans' | 'addons'>('plans');
  const [plans, setPlans] = useState<PlanItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingPlan, setEditingPlan] = useState<PlanItem | null>(null);

  // Add-ons Management State
  const [addonsList, setAddonsList] = useState<any[]>([]);
  const [loadingAddons, setLoadingAddons] = useState(false);
  const [editingAddon, setEditingAddon] = useState<any | null>(null);
  const [addonPriceInput, setAddonPriceInput] = useState<number>(15);
  const [addonTiersInput, setAddonTiersInput] = useState<any[]>([]);
  const [addonSaleEnabled, setAddonSaleEnabled] = useState(false);
  const [addonSalePrice, setAddonSalePrice] = useState<number | undefined>(undefined);
  const [addonSaleDiscountPercent, setAddonSaleDiscountPercent] = useState<number | undefined>(undefined);
  const [addonSaleType, setAddonSaleType] = useState<string>('permanent');
  const [addonSaleExpiresAt, setAddonSaleExpiresAt] = useState<string>('');
  const [addonSaleBadgeLabel, setAddonSaleBadgeLabel] = useState<string>('');
  const [savingAddon, setSavingAddon] = useState(false);

  // Form State
  const [formCode, setFormCode] = useState('');
  const [formName, setFormName] = useState('');
  const [formDescription, setFormDescription] = useState('');
  const [formPrice, setFormPrice] = useState<number>(29);
  const [formCurrency, setFormCurrency] = useState('AZN');
  const [formBillingPeriod, setFormBillingPeriod] = useState('monthly');
  const [formTrialDays, setFormTrialDays] = useState<number>(7);
  const [formMaxAgents, setFormMaxAgents] = useState<number>(1);
  const [formMaxSavedSearches, setFormMaxSavedSearches] = useState<number>(10);
  const [formAddonSearchPrice, setFormAddonSearchPrice] = useState<number>(10);
  const [formAddonSearches, setFormAddonSearches] = useState<number>(0);
  const [formSearchTiers, setFormSearchTiers] = useState<Array<{ searches: number; price: number }>>([
    { searches: 5, price: 10 },
    { searches: 10, price: 18 },
    { searches: 20, price: 30 }
  ]);

  const [formMakler, setFormMakler] = useState(true);
  const [formAvm, setFormAvm] = useState(true);
  const [formBrochure, setFormBrochure] = useState(true);
  const [formIntake, setFormIntake] = useState(true);
  const [formMultiLocation, setFormMultiLocation] = useState(true);
  const [formMaxLocations, setFormMaxLocations] = useState<number>(5);
  const [formBackup, setFormBackup] = useState(true);
  
  const [formAgedListings, setFormAgedListings] = useState(false);
  const [formAddonPrice, setFormAddonPrice] = useState<number>(15);
  const [formAgedMaxMonths, setFormAgedMaxMonths] = useState<number>(12);
  const [formAgedTiers, setFormAgedTiers] = useState<Array<{ months: number; price: number }>>([
    { months: 1, price: 10 },
    { months: 3, price: 25 },
    { months: 6, price: 45 },
    { months: 12, price: 80 }
  ]);

  const [formWatermarkImages, setFormWatermarkImages] = useState(false);
  const [formIncludedImageRequests, setFormIncludedImageRequests] = useState<number>(0);
  const [formAddonImagePrice, setFormAddonImagePrice] = useState<number>(10);
  const [formImageTiers, setFormImageTiers] = useState<Array<{ requests: number; price: number }>>([
    { requests: 25, price: 10 },
    { requests: 50, price: 18 },
    { requests: 100, price: 30 }
  ]);

  const [formCrm, setFormCrm] = useState(false);
  const [formAddonCrmPrice, setFormAddonCrmPrice] = useState<number>(15);
  const [formCrmTiers, setFormCrmTiers] = useState<Array<{ months: number; price: number }>>([
    { months: 1, price: 15 },
    { months: 3, price: 35 },
    { months: 6, price: 65 }
  ]);

  const [formPortfolio, setFormPortfolio] = useState(false);
  const [formAddonPortfolioPrice, setFormAddonPortfolioPrice] = useState<number>(15);
  const [formAddonPortfolioLimit, setFormAddonPortfolioLimit] = useState<number>(25);
  const [formPortfolioTiers, setFormPortfolioTiers] = useState<Array<{ listings: number; price: number }>>([
    { listings: 25, price: 15 },
    { listings: 50, price: 25 },
    { listings: 100, price: 40 }
  ]);

  // Promotional Sale State
  const [formSaleEnabled, setFormSaleEnabled] = useState(false);
  const [formSalePrice, setFormSalePrice] = useState<number | undefined>(undefined);
  const [formSaleDiscountPercent, setFormSaleDiscountPercent] = useState<number | undefined>(undefined);
  const [formSaleType, setFormSaleType] = useState<string>('permanent');
  const [formSaleExpiresAt, setFormSaleExpiresAt] = useState<string>('');
  const [formSaleBadgeLabel, setFormSaleBadgeLabel] = useState<string>('');

  const [submitting, setSubmitting] = useState(false);

  const fetchPlans = () => {
    setLoading(true);
    api.get('/plans')
      .then((res) => {
        setPlans(res.data || []);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchPlans();
  }, []);

  const handleAddAgedTier = () => {
    const nextMonths = formAgedTiers.length > 0 ? formAgedTiers[formAgedTiers.length - 1].months * 2 : 3;
    const nextPrice = formAgedTiers.length > 0 ? formAgedTiers[formAgedTiers.length - 1].price + 15 : 15;
    setFormAgedTiers([...formAgedTiers, { months: nextMonths, price: nextPrice }]);
  };

  const handleRemoveAgedTier = (index: number) => {
    setFormAgedTiers(formAgedTiers.filter((_, i) => i !== index));
  };

  const handleUpdateAgedTier = (index: number, field: 'months' | 'price', val: number) => {
    const updated = [...formAgedTiers];
    updated[index] = { ...updated[index], [field]: val };
    setFormAgedTiers(updated);
  };

  const handleAddSearchTier = () => {
    const nextSearches = formSearchTiers.length > 0 ? formSearchTiers[formSearchTiers.length - 1].searches + 5 : 5;
    const nextPrice = formSearchTiers.length > 0 ? formSearchTiers[formSearchTiers.length - 1].price + 10 : 10;
    setFormSearchTiers([...formSearchTiers, { searches: nextSearches, price: nextPrice }]);
  };

  const handleRemoveSearchTier = (index: number) => {
    setFormSearchTiers(formSearchTiers.filter((_, i) => i !== index));
  };

  const handleUpdateSearchTier = (index: number, field: 'searches' | 'price', val: number) => {
    const updated = [...formSearchTiers];
    updated[index] = { ...updated[index], [field]: val };
    setFormSearchTiers(updated);
  };

  const handleAddImageTier = () => {
    const nextRequests = formImageTiers.length > 0 ? formImageTiers[formImageTiers.length - 1].requests + 25 : 25;
    const nextPrice = formImageTiers.length > 0 ? formImageTiers[formImageTiers.length - 1].price + 10 : 10;
    setFormImageTiers([...formImageTiers, { requests: nextRequests, price: nextPrice }]);
  };

  const handleRemoveImageTier = (index: number) => {
    setFormImageTiers(formImageTiers.filter((_, i) => i !== index));
  };

  const handleUpdateImageTier = (index: number, field: 'requests' | 'price', val: number) => {
    const updated = [...formImageTiers];
    updated[index] = { ...updated[index], [field]: val };
    setFormImageTiers(updated);
  };

  const openCreateModal = () => {
    setFormCode('');
    setFormName('');
    setFormDescription('');
    setFormPrice(49);
    setFormCurrency('AZN');
    setFormBillingPeriod('monthly');
    setFormTrialDays(7);
    setFormMaxAgents(1);
    setFormMaxSavedSearches(10);
    setFormAddonSearchPrice(10);
    setFormAddonSearches(0);
    setFormSearchTiers([
      { searches: 5, price: 10 },
      { searches: 10, price: 18 },
      { searches: 20, price: 30 }
    ]);
    setFormMakler(true);
    setFormAvm(true);
    setFormBrochure(true);
    setFormIntake(true);
    setFormMultiLocation(true);
    setFormMaxLocations(5);
    setFormBackup(true);
    setFormAgedListings(false);
    setFormAddonPrice(15);
    setFormAgedMaxMonths(12);
    setFormAgedTiers([
      { months: 1, price: 10 },
      { months: 3, price: 25 },
      { months: 6, price: 45 },
      { months: 12, price: 80 }
    ]);
    setFormWatermarkImages(false);
    setFormIncludedImageRequests(0);
    setFormAddonImagePrice(10);
    setFormImageTiers([
      { requests: 25, price: 10 },
      { requests: 50, price: 18 },
      { requests: 100, price: 30 }
    ]);
    setFormCrm(false);
    setFormAddonCrmPrice(15);
    setFormPortfolio(false);
    setFormAddonPortfolioPrice(15);
    setFormAddonPortfolioLimit(25);
    setFormPortfolioTiers([
      { listings: 25, price: 15 },
      { listings: 50, price: 25 },
      { listings: 100, price: 40 }
    ]);
    setFormSaleEnabled(false);
    setFormSalePrice(undefined);
    setFormSaleDiscountPercent(undefined);
    setFormSaleType('permanent');
    setFormSaleExpiresAt('');
    setFormSaleBadgeLabel('');
    setEditingPlan(null);
    setIsCreateOpen(true);
  };

  const openEditModal = (plan: PlanItem) => {
    setEditingPlan(plan);
    setFormCode(plan.code);
    setFormName(plan.name);
    setFormDescription(plan.description || '');
    setFormPrice(plan.price);
    setFormCurrency(plan.currency);
    setFormBillingPeriod(plan.billing_period);
    setFormTrialDays(plan.trial_days || 7);
    setFormMaxAgents(plan.max_agents);
    setFormMaxSavedSearches(plan.max_saved_searches || 10);
    setFormAddonSearchPrice(plan.addon_saved_searches_price || 10);
    setFormAddonSearches(plan.addon_saved_searches || 0);
    setFormSearchTiers(plan.addon_search_tiers && plan.addon_search_tiers.length > 0 ? plan.addon_search_tiers : [
      { searches: 5, price: 10 },
      { searches: 10, price: 18 },
      { searches: 20, price: 30 }
    ]);
    setFormMakler(plan.feature_makler_detector);
    setFormAvm(plan.feature_avm_bargain_finder);
    setFormBrochure(plan.feature_social_brochure);
    setFormIntake(plan.feature_client_intake_bot);
    setFormMultiLocation(plan.feature_multi_location ?? true);
    setFormMaxLocations(plan.max_locations_per_search || 5);
    setFormBackup(plan.backup_enabled);
    setFormAgedListings(!!plan.feature_aged_listings);
    setFormAddonPrice(plan.addon_aged_listings_price || 15);
    setFormAgedMaxMonths(plan.addon_aged_max_months || 12);
    setFormAgedTiers(plan.addon_aged_tiers && plan.addon_aged_tiers.length > 0 ? plan.addon_aged_tiers : [
      { months: 1, price: 10 },
      { months: 3, price: 25 },
      { months: 6, price: 45 },
      { months: 12, price: 80 }
    ]);
    setFormWatermarkImages(!!plan.feature_watermark_free_images);
    setFormIncludedImageRequests(plan.included_image_requests || 0);
    setFormAddonImagePrice(plan.addon_image_requests_price || 10);
    setFormImageTiers(plan.addon_image_tiers && plan.addon_image_tiers.length > 0 ? plan.addon_image_tiers : [
      { requests: 25, price: 10 },
      { requests: 50, price: 18 },
      { requests: 100, price: 30 }
    ]);
    setFormCrm(!!plan.feature_crm);
    setFormAddonCrmPrice(plan.addon_crm_price || 15);
    setFormCrmTiers(plan.addon_crm_tiers && plan.addon_crm_tiers.length > 0 ? plan.addon_crm_tiers : [
      { months: 1, price: 15 },
      { months: 3, price: 35 },
      { months: 6, price: 65 }
    ]);
    setFormPortfolio(!!plan.feature_portfolio);
    setFormAddonPortfolioPrice(plan.addon_portfolio_price || 15);
    setFormAddonPortfolioLimit(plan.addon_portfolio_limit || 25);
    setFormPortfolioTiers(plan.addon_portfolio_tiers && plan.addon_portfolio_tiers.length > 0 ? plan.addon_portfolio_tiers : [
      { listings: 25, price: 15 },
      { listings: 50, price: 25 },
      { listings: 100, price: 40 }
    ]);
    setFormSaleEnabled(plan.sale_enabled ?? false);
    setFormSalePrice(plan.sale_price);
    setFormSaleDiscountPercent(plan.sale_discount_percent);
    setFormSaleType(plan.sale_type || 'permanent');
    setFormSaleExpiresAt(plan.sale_expires_at ? plan.sale_expires_at.split('T')[0] : '');
    setFormSaleBadgeLabel(plan.sale_badge_label || '');
    setIsCreateOpen(true);
  };

  const handleSavePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      if (editingPlan) {
        // Edit existing plan
        await api.put(`/plans/${editingPlan.id}`, {
          name: formName,
          description: formDescription,
          price: formPrice,
          currency: formCurrency,
          billing_period: formBillingPeriod,
          trial_days: formTrialDays,
          max_agents: formMaxAgents,
          max_saved_searches: formMaxSavedSearches,
          addon_saved_searches: formAddonSearches,
          addon_saved_searches_price: formAddonSearchPrice,
          addon_search_tiers: formSearchTiers,
          feature_makler_detector: formMakler,
          feature_avm_bargain_finder: formAvm,
          feature_social_brochure: formBrochure,
          feature_client_intake_bot: formIntake,
          feature_multi_location: formMultiLocation,
          max_locations_per_search: formMaxLocations,
          feature_aged_listings: formAgedListings,
          addon_aged_listings_price: formAddonPrice,
          addon_aged_max_months: formAgedMaxMonths,
          addon_aged_tiers: formAgedTiers,
          feature_watermark_free_images: formWatermarkImages,
          included_image_requests: formIncludedImageRequests,
          addon_image_requests_price: formAddonImagePrice,
          addon_image_tiers: formImageTiers,
          feature_crm: formCrm,
          addon_crm_price: formAddonCrmPrice,
          addon_crm_tiers: formCrmTiers,
          feature_portfolio: formPortfolio,
          addon_portfolio_price: formAddonPortfolioPrice,
          addon_portfolio_limit: formAddonPortfolioLimit,
          addon_portfolio_tiers: formPortfolioTiers,
          sale_enabled: formSaleEnabled,
          sale_price: formSaleEnabled ? formSalePrice : undefined,
          sale_discount_percent: formSaleEnabled ? formSaleDiscountPercent : undefined,
          sale_type: formSaleType,
          sale_expires_at: formSaleExpiresAt ? new Date(formSaleExpiresAt).toISOString() : undefined,
          sale_badge_label: formSaleBadgeLabel || undefined,
          backup_enabled: formBackup,
        });
      } else {
        // Create new plan
        await api.post('/plans', {
          code: formCode,
          name: formName,
          description: formDescription,
          price: formPrice,
          currency: formCurrency,
          billing_period: formBillingPeriod,
          trial_days: formTrialDays,
          max_agents: formMaxAgents,
          max_saved_searches: formMaxSavedSearches,
          addon_saved_searches: formAddonSearches,
          addon_saved_searches_price: formAddonSearchPrice,
          addon_search_tiers: formSearchTiers,
          feature_makler_detector: formMakler,
          feature_avm_bargain_finder: formAvm,
          feature_social_brochure: formBrochure,
          feature_client_intake_bot: formIntake,
          feature_multi_location: formMultiLocation,
          max_locations_per_search: formMaxLocations,
          feature_aged_listings: formAgedListings,
          addon_aged_listings_price: formAddonPrice,
          addon_aged_max_months: formAgedMaxMonths,
          addon_aged_tiers: formAgedTiers,
          feature_watermark_free_images: formWatermarkImages,
          included_image_requests: formIncludedImageRequests,
          addon_image_requests_price: formAddonImagePrice,
          addon_image_tiers: formImageTiers,
          feature_crm: formCrm,
          addon_crm_price: formAddonCrmPrice,
          addon_crm_tiers: formCrmTiers,
          feature_portfolio: formPortfolio,
          addon_portfolio_price: formAddonPortfolioPrice,
          addon_portfolio_limit: formAddonPortfolioLimit,
          addon_portfolio_tiers: formPortfolioTiers,
          sale_enabled: formSaleEnabled,
          sale_price: formSaleEnabled ? formSalePrice : undefined,
          sale_discount_percent: formSaleEnabled ? formSaleDiscountPercent : undefined,
          sale_type: formSaleType,
          sale_expires_at: formSaleExpiresAt ? new Date(formSaleExpiresAt).toISOString() : undefined,
          sale_badge_label: formSaleBadgeLabel || undefined,
          backup_enabled: formBackup,
        });
      }

      setIsCreateOpen(false);
      fetchPlans();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Error saving subscription plan');
    } finally {
      setSubmitting(false);
    }
  };

  const fetchAddons = async () => {
    setLoadingAddons(true);
    try {
      const res = await api.get('/plans/addons/overview');
      setAddonsList(res.data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingAddons(false);
    }
  };

  const openEditAddon = (addon: any) => {
    setEditingAddon(addon);
    setAddonPriceInput(addon.default_price || 15);
    setAddonTiersInput(addon.tiers || []);
    setAddonSaleEnabled(addon.sale_enabled ?? false);
    setAddonSalePrice(addon.sale_price);
    setAddonSaleDiscountPercent(addon.sale_discount_percent ?? 20);
    setAddonSaleType(addon.sale_type || 'permanent');
    setAddonSaleExpiresAt(addon.sale_expires_at ? addon.sale_expires_at.split('T')[0] : '');
    setAddonSaleBadgeLabel(addon.sale_badge_label || `🔥 ${addon.sale_discount_percent || 20}% Xüsusi Təklif`);
  };

  const handleSaveAddon = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingAddon) return;
    setSavingAddon(true);
    try {
      await api.put(`/plans/addons/${editingAddon.key}`, {
        price: addonPriceInput,
        tiers: addonTiersInput,
        sale_enabled: addonSaleEnabled,
        sale_price: addonSaleEnabled ? addonSalePrice : undefined,
        sale_discount_percent: addonSaleEnabled ? addonSaleDiscountPercent : undefined,
        sale_type: addonSaleType,
        sale_expires_at: addonSaleExpiresAt ? new Date(addonSaleExpiresAt).toISOString() : undefined,
        sale_badge_label: addonSaleBadgeLabel || undefined
      });
      setEditingAddon(null);
      fetchAddons();
      fetchPlans();
      alert(`"${editingAddon.name}" üçün qiymətlər və kampaniya uğurla yeniləndi!`);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Addon qiymətlərini yeniləyərkən xəta baş verdi');
    } finally {
      setSavingAddon(false);
    }
  };

  const togglePlanActive = async (plan: PlanItem) => {
    try {
      await api.put(`/plans/${plan.id}`, {
        is_active: !plan.is_active,
      });
      fetchPlans();
    } catch (err: any) {
      alert('Error updating plan status');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-dark-800/80 border border-slate-800 p-6 rounded-2xl shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <Package className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white tracking-tight">Tariflər, Paketlər və Əlavə Xidmətlər (Add-ons)</h2>
              <p className="text-xs text-slate-400">Abunə tariflərini, funksiyaları, əlavə xidmətlərin qiymət pillələrini və endirimləri idarə edin</p>
            </div>
          </div>
        </div>

        {activeTab === 'plans' && (
          <button
            onClick={openCreateModal}
            className="flex items-center gap-2 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white px-4 py-2.5 rounded-xl font-semibold text-sm shadow-lg shadow-emerald-500/20 transition-all self-start sm:self-auto"
          >
            <Plus className="w-4 h-4" />
            <span>Yeni Abunə Planı</span>
          </button>
        )}
      </div>

      {/* Top Tabs Switcher */}
      <div className="flex items-center gap-2 p-1.5 bg-dark-800/90 border border-slate-800 rounded-2xl w-fit">
        <button
          onClick={() => setActiveTab('plans')}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold transition ${
            activeTab === 'plans'
              ? 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-500/20'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <Package className="w-4 h-4" />
          <span>📦 Abunə Paketləri ({plans.length})</span>
        </button>
        <button
          onClick={() => { setActiveTab('addons'); fetchAddons(); }}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold transition ${
            activeTab === 'addons'
              ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/20'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>🛒 Əlavə Xidmətlər (Add-ons & Qiymətlər)</span>
        </button>
      </div>

      {/* TAB 1: Grid of Plans */}
      {activeTab === 'plans' && (
        loading ? (
          <div className="flex items-center justify-center py-16">
            <RefreshCw className="w-7 h-7 text-emerald-400 animate-spin" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {plans.map((plan) => (
            <div
              key={plan.id}
              className={`bg-dark-800/90 border rounded-2xl p-6 flex flex-col justify-between transition-all relative overflow-hidden ${
                plan.is_active ? 'border-slate-800 hover:border-emerald-500/40 shadow-xl' : 'border-slate-800/50 opacity-60'
              }`}
            >
              {/* Top Row: Code Badge & Subscriber Count */}
              <div>
                <div className="flex items-center justify-between gap-2 mb-3">
                  <span className="text-[11px] font-extrabold uppercase tracking-wider px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    {plan.code}
                  </span>
                  <div className="flex items-center gap-1.5 text-xs text-slate-400 bg-dark-900/80 px-2.5 py-1 rounded-lg border border-slate-800">
                    <Users className="w-3.5 h-3.5 text-indigo-400" />
                    <span>{plan.subscriber_count} Active Tenants</span>
                  </div>
                </div>

                {/* Plan Title & Pricing */}
                {plan.sale_enabled && (
                  <div className="mb-2 flex flex-wrap items-center gap-1.5">
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/15 text-rose-300 border border-rose-500/30">
                      <Sparkles className="w-3 h-3 text-rose-400" />
                      <span>{plan.sale_badge_label || `🔥 ${plan.sale_discount_percent ? `${plan.sale_discount_percent}% ENDİRİM` : 'XÜSUSİ TƏKLİF'}`}</span>
                    </span>
                    {plan.sale_type === 'first_month' && (
                      <span className="text-[9px] px-2 py-0.2 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/25 font-semibold">
                        İlk 1 ay
                      </span>
                    )}
                    {plan.sale_type === 'first_3_months' && (
                      <span className="text-[9px] px-2 py-0.2 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/25 font-semibold">
                        İlk 3 ay
                      </span>
                    )}
                    {plan.sale_type === 'first_6_months' && (
                      <span className="text-[9px] px-2 py-0.2 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/25 font-semibold">
                        İlk 6 ay
                      </span>
                    )}
                  </div>
                )}
                <h3 className="text-lg font-bold text-white mb-1">{plan.name}</h3>
                <p className="text-xs text-slate-400 min-h-[36px] line-clamp-2 mb-4">{plan.description || 'No description provided.'}</p>

                <div className="bg-dark-900/60 p-3 rounded-xl border border-slate-800/80 mb-5">
                  <div className="flex items-baseline gap-1.5">
                    {plan.sale_enabled && plan.sale_price !== undefined ? (
                      <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-extrabold text-emerald-400">{plan.sale_price}</span>
                        <span className="text-sm font-semibold text-slate-500 line-through">{plan.price}</span>
                        <span className="text-sm font-semibold text-emerald-400">{plan.currency}</span>
                      </div>
                    ) : (
                      <div className="flex items-baseline gap-1">
                        <span className="text-2xl font-extrabold text-white">{plan.price}</span>
                        <span className="text-sm font-semibold text-emerald-400">{plan.currency}</span>
                      </div>
                    )}
                    <span className="text-xs text-slate-400">
                      / {plan.billing_period === 'daily' || plan.code === 'free' ? `${plan.trial_days || 7} Days Trial` : plan.billing_period}
                    </span>
                    <span className="ml-auto text-[11px] text-slate-400 font-medium">Max {plan.max_agents} Agents</span>
                  </div>
                  {plan.sale_enabled && plan.sale_price !== undefined && (
                    <span className="text-[10px] text-emerald-400/80 font-medium block mt-1">
                      {plan.sale_type === 'first_month' && '⚡ İlk 1 ay endirimlə, sonrakı aylar standart tarif'}
                      {plan.sale_type === 'first_3_months' && '⚡ İlk 3 ay endirimlə, sonrakı aylar standart tarif'}
                      {plan.sale_type === 'first_6_months' && '⚡ İlk 6 ay endirimlə, sonrakı aylar standart tarif'}
                      {plan.sale_type === 'limited_time' && plan.sale_expires_at && `⚡ Kampaniya bitmə: ${new Date(plan.sale_expires_at).toLocaleDateString('az-AZ')}`}
                      {plan.sale_type === 'permanent' && '⚡ Bütün abunəlik müddəti üçün daimi endirim'}
                    </span>
                  )}
                </div>

                {/* Features Included Checklist */}
                <div className="space-y-2 text-xs mb-6">
                  <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Included Features</div>
                  
                  <div className="flex items-center gap-2">
                    {plan.feature_makler_detector ? (
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    ) : (
                      <X className="w-4 h-4 text-slate-600 shrink-0" />
                    )}
                    <span className={plan.feature_makler_detector ? 'text-slate-200' : 'text-slate-500 line-through'}>
                      AI Makler & Agency Detector
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    {plan.feature_avm_bargain_finder ? (
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    ) : (
                      <X className="w-4 h-4 text-slate-600 shrink-0" />
                    )}
                    <span className={plan.feature_avm_bargain_finder ? 'text-slate-200' : 'text-slate-500 line-through'}>
                      AVM Valuation & Bargain Finder
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    {plan.feature_social_brochure ? (
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    ) : (
                      <X className="w-4 h-4 text-slate-600 shrink-0" />
                    )}
                    <span className={plan.feature_social_brochure ? 'text-slate-200' : 'text-slate-500 line-through'}>
                      PDF & Social Brochure Generator
                    </span>
                  </div>

                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      {plan.feature_multi_location ? (
                        <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                      ) : (
                        <X className="w-4 h-4 text-slate-600 shrink-0" />
                      )}
                      <span className={plan.feature_multi_location ? 'text-slate-200' : 'text-slate-500 line-through'}>
                        Multi-Location Search (Multiple Metros/Areas)
                      </span>
                    </div>
                    {plan.feature_multi_location ? (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/15 text-blue-300 font-semibold">
                        Max {plan.max_locations_per_search || 5} areas
                      </span>
                    ) : null}
                  </div>

                  <div className="flex items-center gap-2">
                    {plan.feature_client_intake_bot ? (
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    ) : (
                      <X className="w-4 h-4 text-slate-600 shrink-0" />
                    )}
                    <span className={plan.feature_client_intake_bot ? 'text-slate-200' : 'text-slate-500 line-through'}>
                      Branded Client Intake Bot
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    {plan.backup_enabled ? (
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    ) : (
                      <X className="w-4 h-4 text-slate-600 shrink-0" />
                    )}
                    <span className={plan.backup_enabled ? 'text-slate-200' : 'text-slate-500 line-through'}>
                      Automated BaaS Data Backups
                    </span>
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Search className="w-4 h-4 text-cyan-400 shrink-0" />
                        <span className="text-slate-200">Max Saved Searches</span>
                      </div>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-500/15 text-cyan-300 font-semibold">
                        {plan.max_saved_searches || 10} Searches
                      </span>
                    </div>
                    {plan.addon_search_tiers && plan.addon_search_tiers.length > 0 && (
                      <div className="flex flex-wrap gap-1 pl-6">
                        {plan.addon_search_tiers.map((t, idx) => (
                          <span key={idx} className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                            +{t.searches} axtarış ({t.price} ₼)
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        {plan.feature_aged_listings ? (
                          <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                        ) : (
                          <X className="w-4 h-4 text-slate-600 shrink-0" />
                        )}
                        <span className={plan.feature_aged_listings ? 'text-slate-200' : 'text-slate-500 line-through'}>
                          Aged Inventory Archive ({plan.addon_aged_max_months || 12} mo.)
                        </span>
                      </div>
                      {plan.addon_aged_listings_price && plan.addon_aged_listings_price > 0 ? (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/15 text-purple-300 font-semibold">
                          +{plan.addon_aged_listings_price} AZN Base
                        </span>
                      ) : null}
                    </div>
                    {plan.feature_aged_listings && plan.addon_aged_tiers && plan.addon_aged_tiers.length > 0 && (
                      <div className="flex flex-wrap gap-1 pl-6">
                        {plan.addon_aged_tiers.map((t, idx) => (
                          <span key={idx} className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                            {t.months} ay ({t.price} ₼)
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        {plan.feature_watermark_free_images ? (
                          <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                        ) : (
                          <X className="w-4 h-4 text-slate-600 shrink-0" />
                        )}
                        <span className={plan.feature_watermark_free_images ? 'text-slate-200' : 'text-slate-500 line-through'}>
                          Su Nişansız Foto Add-on (Watermark-Free)
                        </span>
                      </div>
                      {plan.included_image_requests && plan.included_image_requests > 0 ? (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-teal-500/15 text-teal-300 font-semibold">
                          {plan.included_image_requests} Daxildir
                        </span>
                      ) : null}
                    </div>
                    {plan.feature_watermark_free_images && plan.addon_image_tiers && plan.addon_image_tiers.length > 0 && (
                      <div className="flex flex-wrap gap-1 pl-6">
                        {plan.addon_image_tiers.map((t, idx) => (
                          <span key={idx} className="text-[9px] px-1.5 py-0.5 rounded bg-teal-500/10 text-teal-300 border border-teal-500/20">
                            +{t.requests} foto ({t.price} ₼)
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        {plan.feature_crm ? (
                          <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                        ) : (
                          <X className="w-4 h-4 text-slate-600 shrink-0" />
                        )}
                        <span className={plan.feature_crm ? 'text-slate-200 font-semibold' : 'text-slate-500 line-through'}>
                          💼 Telegram Mini App & Real Estate CRM
                        </span>
                      </div>
                      {plan.addon_crm_price && plan.addon_crm_price > 0 ? (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/15 text-indigo-300 font-semibold">
                          +{plan.addon_crm_price} AZN Addon
                        </span>
                      ) : null}
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        {plan.feature_portfolio ? (
                          <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                        ) : (
                          <X className="w-4 h-4 text-slate-600 shrink-0" />
                        )}
                        <span className={plan.feature_portfolio ? 'text-slate-200 font-semibold' : 'text-slate-500 line-through'}>
                          🗂️ Agent Portfeli & Vitrin ({plan.addon_portfolio_limit || 25} elan)
                        </span>
                      </div>
                      {plan.addon_portfolio_price && plan.addon_portfolio_price > 0 ? (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/15 text-purple-300 font-semibold">
                          +{plan.addon_portfolio_price} AZN Addon
                        </span>
                      ) : null}
                    </div>
                    {plan.feature_portfolio && plan.addon_portfolio_tiers && plan.addon_portfolio_tiers.length > 0 && (
                      <div className="flex flex-wrap gap-1 pl-6">
                        {plan.addon_portfolio_tiers.map((t, idx) => (
                          <span key={idx} className="text-[9px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20">
                            {t.listings} elan ({t.price} ₼)
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-4 border-t border-slate-800/80 flex items-center justify-between gap-3">
                <button
                  onClick={() => openEditModal(plan)}
                  className="flex-1 flex items-center justify-center gap-2 bg-dark-700 hover:bg-dark-600 text-slate-200 py-2 rounded-xl text-xs font-semibold border border-slate-700/60 transition-colors"
                >
                  <Edit3 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Edit Plan</span>
                </button>

                <button
                  onClick={() => togglePlanActive(plan)}
                  className={`px-3 py-2 rounded-xl text-xs font-semibold border transition-colors ${
                    plan.is_active
                      ? 'bg-rose-500/10 text-rose-400 border-rose-500/20 hover:bg-rose-500/20'
                      : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/20'
                  }`}
                >
                  {plan.is_active ? 'Deactivate' : 'Activate'}
                </button>
              </div>
            </div>
          ))}
        </div>
        )
      )}

      {/* TAB 2: Grid of Add-ons */}
      {activeTab === 'addons' && (
        loadingAddons ? (
          <div className="flex items-center justify-center py-16">
            <RefreshCw className="w-7 h-7 text-indigo-400 animate-spin" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {addonsList.map((addon) => (
              <div
                key={addon.key}
                className="bg-dark-800/90 border border-slate-800 hover:border-indigo-500/40 rounded-2xl p-6 flex flex-col justify-between transition-all shadow-xl relative overflow-hidden"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <span className="text-[11px] font-extrabold uppercase tracking-wider px-2.5 py-1 rounded-md bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                      {addon.category.toUpperCase()} ADD-ON
                    </span>
                    <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      Aktiv
                    </span>
                  </div>

                  <h3 className="text-lg font-bold text-white mb-1.5">{addon.name}</h3>
                  <p className="text-xs text-slate-400 mb-4 leading-relaxed">{addon.description}</p>

                  {/* Pricing Overview */}
                  <div className="p-3.5 bg-dark-900/80 rounded-xl border border-slate-800 mb-4 space-y-2">
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-slate-400">Baza Aylıq Qiymət:</span>
                      <span className="text-base font-black text-emerald-400 font-mono">
                        {addon.default_price.toFixed(2)} AZN / ay
                      </span>
                    </div>

                    {addon.tiers && addon.tiers.length > 0 && (
                      <div className="pt-2 border-t border-slate-800/80">
                        <span className="text-[11px] font-semibold text-slate-400 block mb-1.5">Müddət Pillələri və Qiymətlər:</span>
                        <div className="flex flex-wrap gap-1.5">
                          {addon.tiers.map((t: any, idx: number) => (
                            <span key={idx} className="px-2 py-1 rounded-lg bg-dark-950 border border-slate-800 text-[11px] font-mono text-indigo-300">
                              {t.months ? `${t.months} ay` : t.searches ? `+${t.searches} axtarış` : t.requests ? `+${t.requests} foto` : t.listings ? `${t.listings} elan` : ''}: <strong>{t.price} AZN</strong>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Features Included List */}
                  <div className="space-y-1.5 mb-5">
                    <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">Daxil Olan Funksiyalar:</span>
                    {addon.features_included?.map((f: string, i: number) => (
                      <div key={i} className="flex items-center gap-2 text-xs text-slate-300">
                        <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                        <span>{f}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-800/80 flex items-center justify-end">
                  <button
                    onClick={() => openEditAddon(addon)}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-bold text-xs shadow-lg shadow-indigo-600/20 transition"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    <span>Qiymət və Pillələri Redaktə Et</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )
      )}

      {/* Modal: Edit Add-on */}
      {editingAddon && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-dark-800 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5 my-8">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-lg font-bold text-white">
                {editingAddon.name} — Qiymət Tənzimləmələri
              </h3>
              <button onClick={() => setEditingAddon(null)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveAddon} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Baza Aylıq Qiymət (AZN) *
                </label>
                <input
                  type="number"
                  step="0.5"
                  required
                  value={addonPriceInput}
                  onChange={(e) => setAddonPriceInput(Number(e.target.value))}
                  className="w-full bg-dark-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white font-mono font-bold text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Tiers Editor */}
              {addonTiersInput && addonTiersInput.length > 0 && (
                <div className="space-y-2 pt-2 border-t border-slate-800">
                  <label className="block text-xs font-semibold text-indigo-300 mb-1">
                    Müddət və Həcm Pillələri üzrə Qiymətlər (AZN)
                  </label>
                  <div className="space-y-2">
                    {addonTiersInput.map((tier: any, idx: number) => (
                      <div key={idx} className="flex items-center gap-3 bg-dark-950/60 p-2.5 rounded-xl border border-slate-800">
                        <span className="text-xs text-slate-300 font-mono w-28">
                          {tier.months ? `${tier.months} Ay` : tier.searches ? `+${tier.searches} Axtarış` : tier.requests ? `+${tier.requests} Foto` : tier.listings ? `${tier.listings} Elan` : ''}
                        </span>
                        <div className="flex items-center gap-1.5 flex-1">
                          <input
                            type="number"
                            step="0.5"
                            value={tier.price}
                            onChange={(e) => {
                              const nextTiers = [...addonTiersInput];
                              nextTiers[idx].price = Number(e.target.value);
                              setAddonTiersInput(nextTiers);
                            }}
                            className="w-full bg-dark-900 border border-slate-700 rounded-lg px-2.5 py-1 text-white text-xs font-mono font-bold"
                          />
                          <span className="text-xs text-slate-400">AZN</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Promotional Sale & Discount Campaign for Add-on */}
              <div className="p-3.5 bg-rose-500/10 border border-rose-500/30 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={addonSaleEnabled}
                      onChange={(e) => setAddonSaleEnabled(e.target.checked)}
                      className="rounded accent-rose-500 w-4 h-4"
                    />
                    <span className="font-bold text-rose-300 text-xs flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-rose-400" />
                      <span>Xüsusi Endirim / Kampaniya Aktivləşdir</span>
                    </span>
                  </label>
                </div>

                {addonSaleEnabled && (
                  <div className="space-y-2.5 pt-2 border-t border-rose-500/20 text-xs">
                    <div className="grid grid-cols-2 gap-2.5">
                      <div>
                        <label className="text-slate-300 text-[11px] block mb-1">Endirim Faizi (%)</label>
                        <input
                          type="number"
                          min="1"
                          max="99"
                          value={addonSaleDiscountPercent || ''}
                          onChange={(e) => {
                            const pct = Number(e.target.value);
                            setAddonSaleDiscountPercent(pct);
                            if (pct > 0 && addonPriceInput > 0) {
                              setAddonSalePrice(Number((addonPriceInput * (1 - pct / 100)).toFixed(2)));
                            }
                          }}
                          placeholder="20"
                          className="w-full bg-dark-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-white text-xs font-bold"
                        />
                      </div>

                      <div>
                        <label className="text-slate-300 text-[11px] block mb-1">Endirimli Satış Qiyməti (AZN)</label>
                        <input
                          type="number"
                          step="0.5"
                          value={addonSalePrice || ''}
                          onChange={(e) => setAddonSalePrice(Number(e.target.value))}
                          placeholder="12.0"
                          className="w-full bg-dark-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-rose-300 text-xs font-bold font-mono"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="text-slate-300 text-[11px] block mb-1">Kampaniya Etiketi (Badge Label)</label>
                      <input
                        type="text"
                        value={addonSaleBadgeLabel}
                        onChange={(e) => setAddonSaleBadgeLabel(e.target.value)}
                        placeholder="🔥 20% Xüsusi Endirim"
                        className="w-full bg-dark-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-white text-xs"
                      />
                    </div>
                  </div>
                )}
              </div>

              <div className="pt-4 border-t border-slate-800 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setEditingAddon(null)}
                  className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-slate-300 rounded-xl font-semibold text-xs"
                >
                  Ləğv et
                </button>

                <button
                  type="submit"
                  disabled={savingAddon}
                  className="px-5 py-2 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl font-semibold text-xs shadow-lg shadow-indigo-500/20 disabled:opacity-50"
                >
                  {savingAddon ? 'Saxlanılır...' : 'Qiymətləri Yadda Saxla'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Create / Edit Plan */}
      {isCreateOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-dark-800 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5 my-8">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-lg font-bold text-white">
                {editingPlan ? `Edit Subscription Plan (${editingPlan.code})` : 'Create New Subscription Plan'}
              </h3>
              <button onClick={() => setIsCreateOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSavePlan} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="font-semibold text-slate-300">Plan Code</label>
                  <input
                    type="text"
                    required
                    disabled={!!editingPlan}
                    value={formCode}
                    onChange={(e) => setFormCode(e.target.value)}
                    placeholder="e.g. pro_custom"
                    className="w-full bg-dark-900 border border-slate-700 rounded-xl px-3 py-2 text-slate-100 placeholder-slate-500 disabled:opacity-50"
                  />
                </div>

                <div className="space-y-1">
                  <label className="font-semibold text-slate-300">Plan Name</label>
                  <input
                    type="text"
                    required
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    placeholder="e.g. Pro Custom Plan"
                    className="w-full bg-dark-900 border border-slate-700 rounded-xl px-3 py-2 text-slate-100 placeholder-slate-500"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-slate-300">Description</label>
                <textarea
                  rows={2}
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  placeholder="Short description of what is included in this plan..."
                  className="w-full bg-dark-900 border border-slate-700 rounded-xl px-3 py-2 text-slate-100 placeholder-slate-500"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-1">
                  <label className="font-semibold text-slate-300">Price</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={formPrice}
                    onChange={(e) => setFormPrice(parseFloat(e.target.value) || 0)}
                    className="w-full bg-dark-900 border border-slate-700 rounded-xl px-3 py-2 text-slate-100"
                  />
                </div>

                <div className="space-y-1">
                  <label className="font-semibold text-slate-300">Currency</label>
                  <select
                    value={formCurrency}
                    onChange={(e) => setFormCurrency(e.target.value)}
                    className="w-full bg-dark-900 border border-slate-700 rounded-xl px-3 py-2 text-slate-100"
                  >
                    <option value="AZN">AZN</option>
                    <option value="USD">USD</option>
                    <option value="EUR">EUR</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="font-semibold text-slate-300">Billing Period</label>
                  <select
                    value={formBillingPeriod}
                    onChange={(e) => setFormBillingPeriod(e.target.value)}
                    className="w-full bg-dark-900 border border-slate-700 rounded-xl px-3 py-2 text-slate-100"
                  >
                    <option value="daily">Daily (Free Trial in Days)</option>
                    <option value="monthly">Monthly</option>
                    <option value="quarterly">Quarterly</option>
                    <option value="annual">Annual</option>
                    <option value="lifetime">Lifetime</option>
                  </select>
                </div>
              </div>

              {(formBillingPeriod === 'daily' || formBillingPeriod === 'trial' || formCode === 'free') && (
                <div className="space-y-1 p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl">
                  <label className="font-semibold text-amber-300 text-xs block">Free Trial Duration (Days)</label>
                  <input
                    type="number"
                    min="1"
                    max="90"
                    value={formTrialDays}
                    onChange={(e) => setFormTrialDays(parseInt(e.target.value) || 7)}
                    className="w-full bg-dark-900 border border-amber-500/40 rounded-lg px-3 py-1.5 text-sm text-white font-bold"
                  />
                  <p className="text-[10px] text-amber-300/80">
                    Agent will get active access for {formTrialDays} days. System will auto-expire and broadcast upgrade offers on day {formTrialDays}.
                  </p>
                </div>
              )}

              {/* Promotional Sale & Campaign Settings */}
              <div className="p-4 bg-gradient-to-br from-rose-950/30 via-dark-900 to-dark-900 border border-rose-500/30 rounded-2xl space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-rose-400" />
                    <div>
                      <h4 className="text-xs font-bold text-white">Xüsusi Endirim & Kampaniya Təklif Et</h4>
                      <p className="text-[10px] text-slate-400">Agentləri cəlb etmək üçün faizlə və ya ilk aylara özəl endirim qurun.</p>
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formSaleEnabled}
                      onChange={(e) => {
                        const enabled = e.target.checked;
                        setFormSaleEnabled(enabled);
                        if (enabled && !formSalePrice && !formSaleDiscountPercent) {
                          const defPercent = 20;
                          setFormSaleDiscountPercent(defPercent);
                          setFormSalePrice(Math.round(formPrice * (1 - defPercent / 100)));
                        }
                      }}
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-rose-600"></div>
                  </label>
                </div>

                {formSaleEnabled && (
                  <div className="space-y-3 pt-2 border-t border-rose-500/20 text-xs">
                    <div>
                      <label className="block text-slate-300 font-semibold mb-1">Endirim Növü (Kampaniya Şərti)</label>
                      <select
                        value={formSaleType}
                        onChange={(e) => setFormSaleType(e.target.value)}
                        className="w-full bg-dark-900 border border-rose-500/40 rounded-xl px-3 py-2 text-white font-medium focus:outline-none focus:border-rose-400"
                      >
                        <option value="first_month">🔥 Yalnız İlk 1 Ay Endirimlə (1st Month Promo)</option>
                        <option value="first_3_months">⚡ İlk 3 Ay Endirimlə (First 3 Months Sale)</option>
                        <option value="first_6_months">⭐ İlk 6 Ay Endirimlə (First 6 Months)</option>
                        <option value="permanent">♾️ Bütün Müddət Üçün Daimi Endirim</option>
                        <option value="limited_time">⏳ Müddətli Kampaniya (Tarixə qədər)</option>
                      </select>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-slate-300 font-semibold mb-1">Endirim Faizi (%)</label>
                        <input
                          type="number"
                          min="1"
                          max="90"
                          step="1"
                          placeholder="Məs: 20%"
                          value={formSaleDiscountPercent || ''}
                          onChange={(e) => {
                            const pct = Number(e.target.value);
                            setFormSaleDiscountPercent(pct);
                            if (pct > 0 && formPrice > 0) {
                              setFormSalePrice(Math.round(formPrice * (1 - pct / 100)));
                            }
                          }}
                          className="w-full bg-dark-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-rose-400"
                        />
                      </div>

                      <div>
                        <label className="block text-slate-300 font-semibold mb-1">Endirimli Qiymət ({formCurrency})</label>
                        <input
                          type="number"
                          min="1"
                          step="1"
                          placeholder="Məs: 39 AZN"
                          value={formSalePrice || ''}
                          onChange={(e) => {
                            const pr = Number(e.target.value);
                            setFormSalePrice(pr);
                            if (pr > 0 && formPrice > 0) {
                              setFormSaleDiscountPercent(Math.round(((formPrice - pr) / formPrice) * 100));
                            }
                          }}
                          className="w-full bg-dark-900 border border-emerald-500/50 rounded-xl px-3 py-2 text-emerald-400 font-bold focus:outline-none focus:border-emerald-400"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-slate-300 font-semibold mb-1">Xüsusi Nişan Mətni (Könüllü)</label>
                        <input
                          type="text"
                          placeholder="Məs: 🔥 YAZ ENDİRİMİ"
                          value={formSaleBadgeLabel}
                          onChange={(e) => setFormSaleBadgeLabel(e.target.value)}
                          className="w-full bg-dark-900 border border-slate-700 rounded-xl px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-rose-400"
                        />
                      </div>

                      {formSaleType === 'limited_time' ? (
                        <div>
                          <label className="block text-slate-300 font-semibold mb-1">Kampaniya Bitmə Tarixi</label>
                          <input
                            type="date"
                            value={formSaleExpiresAt}
                            onChange={(e) => setFormSaleExpiresAt(e.target.value)}
                            className="w-full bg-dark-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-rose-400"
                          />
                        </div>
                      ) : (
                        <div className="flex flex-col justify-center">
                          <span className="text-[11px] text-slate-400">Faktiki Qiymət:</span>
                          <span className="text-emerald-400 font-bold text-sm">
                            {formSalePrice || formPrice} {formCurrency} / {formBillingPeriod}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="font-semibold text-slate-300 text-xs">Max Agents Seats</label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={formMaxAgents}
                    onChange={(e) => setFormMaxAgents(parseInt(e.target.value) || 1)}
                    className="w-full bg-dark-900 border border-slate-700 rounded-xl px-3 py-2 text-slate-100 text-sm font-semibold"
                  />
                </div>

                <div className="space-y-1">
                  <label className="font-semibold text-slate-300 text-xs">Baza Axtarış Limiti (Max Searches)</label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={formMaxSavedSearches}
                    onChange={(e) => setFormMaxSavedSearches(parseInt(e.target.value) || 1)}
                    className="w-full bg-dark-900 border border-slate-700 rounded-xl px-3 py-2 text-cyan-300 text-sm font-semibold"
                  />
                </div>
              </div>

              {/* Multi-Tier Extra Searches Addon Section */}
              <div className="p-3.5 bg-dark-900/60 border border-slate-800 rounded-2xl space-y-2.5">
                <div className="flex items-center justify-between">
                  <label className="font-bold text-cyan-300 text-xs flex items-center gap-1.5">
                    <Search className="w-3.5 h-3.5" />
                    <span>Əlavə Axtarış Limitləri (Addon Paketləri)</span>
                  </label>
                  <button
                    type="button"
                    onClick={handleAddSearchTier}
                    className="px-2.5 py-1 bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 border border-cyan-500/30 rounded-lg text-[11px] font-bold transition flex items-center gap-1"
                  >
                    <Plus className="w-3 h-3" />
                    <span>+ Sətir Əlavə Et</span>
                  </button>
                </div>

                {formSearchTiers.length === 0 ? (
                  <div className="text-[11px] text-slate-500 italic py-1">
                    Əlavə axtarış tarifi əlavə edilməyib. Yuxarıdakı düymə ilə yeni sətir əlavə edə bilərsiniz.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {formSearchTiers.map((tier, idx) => (
                      <div key={idx} className="flex items-center gap-2">
                        <div className="flex-1 flex items-center gap-1.5 bg-dark-950 border border-slate-700/80 rounded-xl px-3 py-1.5">
                          <span className="text-slate-400 text-xs font-bold">+</span>
                          <input
                            type="number"
                            min="1"
                            value={tier.searches}
                            onChange={(e) => handleUpdateSearchTier(idx, 'searches', Number(e.target.value))}
                            className="w-full bg-transparent text-white text-xs font-bold focus:outline-none"
                            placeholder="Məs: 5"
                          />
                          <span className="text-slate-400 text-xs font-medium shrink-0">axtarış</span>
                        </div>
                        <div className="w-32 flex items-center gap-1.5 bg-dark-950 border border-slate-700/80 rounded-xl px-3 py-1.5">
                          <input
                            type="number"
                            min="0"
                            step="0.5"
                            value={tier.price}
                            onChange={(e) => handleUpdateSearchTier(idx, 'price', Number(e.target.value))}
                            className="w-full bg-transparent text-cyan-300 text-xs font-bold focus:outline-none"
                            placeholder="Qiymət"
                          />
                          <span className="text-slate-400 text-xs font-medium shrink-0">AZN</span>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRemoveSearchTier(idx)}
                          className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition"
                          title="Sətiri Sil"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Feature Toggles */}
              <div className="pt-2 border-t border-slate-800 space-y-2">
                <label className="font-bold text-slate-200 block">Feature Permissions Included</label>

                <div className="grid grid-cols-2 gap-2">
                  <label className="flex items-center gap-2 p-2 bg-dark-900/60 rounded-xl border border-slate-800 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formMakler}
                      onChange={(e) => setFormMakler(e.target.checked)}
                      className="rounded accent-emerald-500"
                    />
                    <span className="text-slate-300">Makler Detector</span>
                  </label>

                  <label className="flex items-center gap-2 p-2 bg-dark-900/60 rounded-xl border border-slate-800 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formAvm}
                      onChange={(e) => setFormAvm(e.target.checked)}
                      className="rounded accent-emerald-500"
                    />
                    <span className="text-slate-300">AVM Bargain Finder</span>
                  </label>

                  <label className="flex items-center gap-2 p-2 bg-dark-900/60 rounded-xl border border-slate-800 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formBrochure}
                      onChange={(e) => setFormBrochure(e.target.checked)}
                      className="rounded accent-emerald-500"
                    />
                    <span className="text-slate-300">Social Brochure Generator</span>
                  </label>

                  <label className="flex items-center gap-2 p-2 bg-dark-900/60 rounded-xl border border-slate-800 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formIntake}
                      onChange={(e) => setFormIntake(e.target.checked)}
                      className="rounded accent-emerald-500"
                    />
                    <span className="text-slate-300">Client Intake Bot</span>
                  </label>

                  <label className="flex items-center gap-2 p-2 bg-dark-900/60 rounded-xl border border-slate-800 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formBackup}
                      onChange={(e) => setFormBackup(e.target.checked)}
                      className="rounded accent-emerald-500"
                    />
                    <span className="text-slate-300">BaaS Data Backups</span>
                  </label>

                  <label className="flex items-center gap-2 p-2 bg-dark-900/60 rounded-xl border border-slate-800 cursor-pointer col-span-2">
                    <input
                      type="checkbox"
                      checked={formMultiLocation}
                      onChange={(e) => setFormMultiLocation(e.target.checked)}
                      className="rounded accent-emerald-500"
                    />
                    <div className="flex-1 flex items-center justify-between">
                      <span className="text-slate-300">Multi-Location Search (Selecting 2, 3 or more areas simultaneously)</span>
                      {formMultiLocation && (
                        <div className="flex items-center gap-1.5 text-xs">
                          <span className="text-slate-400">Max Areas:</span>
                          <input
                            type="number"
                            min="1"
                            max="50"
                            value={formMaxLocations}
                            onChange={(e) => setFormMaxLocations(Number(e.target.value))}
                            className="w-16 bg-dark-800 border border-slate-700 rounded-lg px-2 py-1 text-white text-xs"
                            onClick={(e) => e.stopPropagation()}
                          />
                        </div>
                      )}
                    </div>
                  </label>
                </div>

                {/* Aged Listings Multi-Tier Addon Section */}
                <div className="p-3.5 bg-dark-900/60 border border-slate-800 rounded-2xl space-y-3 mt-2">
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formAgedListings}
                        onChange={(e) => setFormAgedListings(e.target.checked)}
                        className="rounded accent-emerald-500"
                      />
                      <span className="font-bold text-amber-300 text-xs">Köhnə Arxiv Elanlar (Aged Listings Archive)</span>
                    </label>
                    {formAgedListings && (
                      <button
                        type="button"
                        onClick={handleAddAgedTier}
                        className="px-2.5 py-1 bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/30 rounded-lg text-[11px] font-bold transition flex items-center gap-1"
                      >
                        <Plus className="w-3 h-3" />
                        <span>+ Sətir Əlavə Et</span>
                      </button>
                    )}
                  </div>

                  {formAgedListings && (
                    <div className="space-y-2.5 pt-1">
                      <div className="flex items-center justify-between text-xs text-slate-400">
                        <span>Maksimal Arxiv Müddəti:</span>
                        <div className="flex items-center gap-1.5">
                          <input
                            type="number"
                            min="1"
                            max="60"
                            value={formAgedMaxMonths}
                            onChange={(e) => setFormAgedMaxMonths(Number(e.target.value))}
                            className="w-16 bg-dark-950 border border-slate-700 rounded-lg px-2 py-1 text-white text-xs text-center font-bold"
                          />
                          <span>ay</span>
                        </div>
                      </div>

                      {formAgedTiers.length === 0 ? (
                        <div className="text-[11px] text-slate-500 italic py-1">
                          Arxiv müddəti tarifi əlavə edilməyib. Yuxarıdakı düymə ilə hər müddət üçün fərdi qiymət sətiri əlavə edin.
                        </div>
                      ) : (
                        <div className="space-y-2">
                          {formAgedTiers.map((tier, idx) => (
                            <div key={idx} className="flex items-center gap-2">
                              <div className="flex-1 flex items-center gap-1.5 bg-dark-950 border border-slate-700/80 rounded-xl px-3 py-1.5">
                                <input
                                  type="number"
                                  min="1"
                                  max="60"
                                  value={tier.months}
                                  onChange={(e) => handleUpdateAgedTier(idx, 'months', Number(e.target.value))}
                                  className="w-full bg-transparent text-white text-xs font-bold focus:outline-none"
                                  placeholder="Məs: 3"
                                />
                                <span className="text-slate-400 text-xs font-medium shrink-0">ay arxiv</span>
                              </div>
                              <div className="w-32 flex items-center gap-1.5 bg-dark-950 border border-slate-700/80 rounded-xl px-3 py-1.5">
                                <input
                                  type="number"
                                  min="0"
                                  step="0.5"
                                  value={tier.price}
                                  onChange={(e) => handleUpdateAgedTier(idx, 'price', Number(e.target.value))}
                                  className="w-full bg-transparent text-amber-300 text-xs font-bold focus:outline-none"
                                  placeholder="Qiymət"
                                />
                                <span className="text-slate-400 text-xs font-medium shrink-0">AZN</span>
                              </div>
                              <button
                                type="button"
                                onClick={() => handleRemoveAgedTier(idx)}
                                className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition"
                                title="Sətiri Sil"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Watermark-Free Photos Multi-Tier Addon Section */}
                <div className="p-3.5 bg-dark-900/60 border border-slate-800 rounded-2xl space-y-3 mt-2">
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formWatermarkImages}
                        onChange={(e) => setFormWatermarkImages(e.target.checked)}
                        className="rounded accent-emerald-500"
                      />
                      <span className="font-bold text-teal-300 text-xs">Su Nişansız Şəkillər Add-on (Watermark-Free Photos)</span>
                    </label>
                    {formWatermarkImages && (
                      <button
                        type="button"
                        onClick={handleAddImageTier}
                        className="px-2.5 py-1 bg-teal-600/20 hover:bg-teal-600/30 text-teal-300 border border-teal-500/30 rounded-lg text-[11px] font-bold transition flex items-center gap-1"
                      >
                        <Plus className="w-3 h-3" />
                        <span>+ Sətir Əlavə Et</span>
                      </button>
                    )}
                  </div>

                  {formWatermarkImages && (
                    <div className="space-y-2.5 pt-1">
                      <div className="flex items-center justify-between text-xs text-slate-400">
                        <span>Paketə Daxil Olan Foto Sorğu Sayı:</span>
                        <div className="flex items-center gap-1.5">
                          <input
                            type="number"
                            min="0"
                            value={formIncludedImageRequests}
                            onChange={(e) => setFormIncludedImageRequests(Number(e.target.value))}
                            className="w-20 bg-dark-950 border border-slate-700 rounded-lg px-2 py-1 text-white text-xs text-center font-bold"
                            placeholder="Məs: 25"
                          />
                          <span>foto</span>
                        </div>
                      </div>

                      {formImageTiers.length === 0 ? (
                        <div className="text-[11px] text-slate-500 italic py-1">
                          Foto sorğu paketi tarifi əlavə edilməyib. Yuxarıdakı düymə ilə əlavə foto paketləri təyin edin.
                        </div>
                      ) : (
                        <div className="space-y-2">
                          {formImageTiers.map((tier, idx) => (
                            <div key={idx} className="flex items-center gap-2">
                              <div className="flex-1 flex items-center gap-1.5 bg-dark-950 border border-slate-700/80 rounded-xl px-3 py-1.5">
                                <span className="text-slate-400 text-xs font-bold">+</span>
                                <input
                                  type="number"
                                  min="1"
                                  value={tier.requests}
                                  onChange={(e) => handleUpdateImageTier(idx, 'requests', Number(e.target.value))}
                                  className="w-full bg-transparent text-white text-xs font-bold focus:outline-none"
                                  placeholder="Məs: 25"
                                />
                                <span className="text-slate-400 text-xs font-medium shrink-0">foto</span>
                              </div>
                              <div className="w-32 flex items-center gap-1.5 bg-dark-950 border border-slate-700/80 rounded-xl px-3 py-1.5">
                                <input
                                  type="number"
                                  min="0"
                                  step="0.5"
                                  value={tier.price}
                                  onChange={(e) => handleUpdateImageTier(idx, 'price', Number(e.target.value))}
                                  className="w-full bg-transparent text-teal-300 text-xs font-bold focus:outline-none"
                                  placeholder="Qiymət"
                                />
                                <span className="text-slate-400 text-xs font-medium shrink-0">AZN</span>
                              </div>
                              <button
                                type="button"
                                onClick={() => handleRemoveImageTier(idx)}
                                className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition"
                                title="Sətiri Sil"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* CRM Mini App Addon Section */}
                <div className="p-3.5 bg-dark-900/60 border border-slate-800 rounded-2xl space-y-3 mt-2">
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formCrm}
                        onChange={(e) => setFormCrm(e.target.checked)}
                        className="rounded accent-blue-500"
                      />
                      <span className="font-bold text-indigo-300 text-xs">💼 Telegram Mini App & Real Estate CRM Add-on</span>
                    </label>
                  </div>

                  {formCrm && (
                    <div className="space-y-2.5 pt-1">
                      <div className="flex items-center justify-between text-xs text-slate-400">
                        <span>Standart Aylıq Əlavə Qiymət (AZN):</span>
                        <div className="flex items-center gap-1.5">
                          <input
                            type="number"
                            min="0"
                            step="0.5"
                            value={formAddonCrmPrice}
                            onChange={(e) => setFormAddonCrmPrice(Number(e.target.value))}
                            className="w-24 bg-dark-950 border border-slate-700 rounded-lg px-2 py-1 text-white text-xs text-center font-bold"
                            placeholder="15"
                          />
                          <span>AZN/ay</span>
                        </div>
                      </div>
                      <p className="text-[11px] text-slate-400">
                        Bu parametr aktiv olduqda, həmin tarifdəki agentlər həm WhatsApp, həm Telegram-da <code className="text-blue-400">/crm &lt;id&gt;</code> əmri vasitəsilə elanları CRM-ə göndərə və Telegram Mini App-dən idarə edə bilərlər.
                      </p>
                    </div>
                  )}
                </div>

                {/* Agent Portfolio Addon Section */}
                <div className="p-3.5 bg-dark-900/60 border border-slate-800 rounded-2xl space-y-3 mt-2">
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formPortfolio}
                        onChange={(e) => setFormPortfolio(e.target.checked)}
                        className="rounded accent-purple-500"
                      />
                      <span className="font-bold text-purple-300 text-xs">🗂️ Agent Portfeli & Rəqəmsal Vitrin Add-on</span>
                    </label>
                  </div>

                  {formPortfolio && (
                    <div className="space-y-3 pt-1">
                      <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1">
                          <label className="text-[11px] text-slate-400 font-semibold block">Standart Limit (Aktiv Elan Sayı):</label>
                          <div className="flex items-center gap-1.5">
                            <input
                              type="number"
                              min="1"
                              value={formAddonPortfolioLimit}
                              onChange={(e) => setFormAddonPortfolioLimit(Number(e.target.value))}
                              className="w-full bg-dark-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-white text-xs text-center font-bold"
                              placeholder="25"
                            />
                            <span className="text-xs text-slate-400">elan</span>
                          </div>
                        </div>

                        <div className="space-y-1">
                          <label className="text-[11px] text-slate-400 font-semibold block">Aylıq Əlavə Qiymət (AZN):</label>
                          <div className="flex items-center gap-1.5">
                            <input
                              type="number"
                              min="0"
                              step="0.5"
                              value={formAddonPortfolioPrice}
                              onChange={(e) => setFormAddonPortfolioPrice(Number(e.target.value))}
                              className="w-full bg-dark-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-white text-xs text-center font-bold"
                              placeholder="15"
                            />
                            <span className="text-xs text-slate-400">AZN/ay</span>
                          </div>
                        </div>
                      </div>

                      <p className="text-[11px] text-slate-400">
                        Agentlər gələn bildirişlərdən və ya bot-dan 1 kliklə elanı öz portfellərinə kopyalaya, hər parametri redaktə edə və müştəriyə rəqib portalların loqosu olmadan təmiz link göndərə bilərlər. Elan satıldıqda və ya vaxtı bitdikdə silindikdə boşalan limit yuvası dərhal azad olunur.
                      </p>
                    </div>
                  )}
                </div>
              </div>

              <div className="pt-4 border-t border-slate-800 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-slate-300 rounded-xl font-semibold"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-xl font-semibold shadow-lg shadow-emerald-500/20 disabled:opacity-50"
                >
                  {submitting ? 'Saving...' : editingPlan ? 'Save Changes' : 'Create Plan'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
