import React, { useEffect, useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { 
  Store, Users, Package, DollarSign, Award, Plus, Edit3, Trash2, CheckCircle, 
  AlertTriangle, RefreshCw, X, Shield, Phone, Send, Sparkles, Check, ChevronRight, TrendingUp,
  Globe, ExternalLink, Lock, Gift, Copy, QrCode, Search, Zap, ShieldCheck, CheckCircle2,
  Calendar, Layers, MessageSquare, Database, ArrowUpRight, Clock, Info, Smartphone, KeyRound, Key
} from 'lucide-react';
import api from '../api';

export interface SellerDashboardData {
  seller_id: number;
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
  rank_description?: string;
  rank_max_packages?: number;
  rank_custom_domain_allowed?: boolean;
  next_rank?: string;
  next_sales_target?: number;
  status: string;
  balance: number;
  total_earnings: number;
  total_sales_volume: number;
  total_platform_fee?: number;
  platform_fee_settled?: number;
  pending_platform_debt?: number;
  total_agents: number;
  active_agents: number;
  total_packages: number;
  min_package_price?: number;
  max_trial_days?: number;
  free_trial_enabled?: boolean;
  free_trial_duration_days?: number;
  free_trial_max_searches?: number;
  free_trial_max_locations?: number;
  free_trial_feature_makler?: boolean;
  free_trial_feature_avm?: boolean;
  free_trial_feature_social_brochure?: boolean;
  free_trial_feature_multi_location?: boolean;
  free_trial_feature_watermark_images?: boolean;
  free_trial_image_requests?: number;
  custom_domain?: string;
  custom_domain_enabled?: boolean;
  domain_status?: string;
  custom_brand_title?: string;
  custom_brand_logo?: string;
}

export interface SellerAgent {
  id: number;
  name: string;
  phone: string;
  telegram_handle?: string;
  whatsapp_number?: string;
  preferred_channel: string;
  plan: string;
  plan_price?: number;
  is_transferred?: boolean;
  status: string;
  is_expired?: boolean;
  plan_started_at?: string;
  plan_expires_at?: string;
  created_at: string;
  feature_makler_detector?: boolean;
  feature_avm_bargain_finder?: boolean;
  feature_social_brochure?: boolean;
  feature_multi_location?: boolean;
  max_locations_per_search?: number;
  feature_client_intake_bot?: boolean;
  backup_enabled?: boolean;
  feature_aged_listings?: boolean;
  addon_aged_max_months?: number;
  addon_saved_searches?: number;
  addon_saved_searches_price?: number;
  feature_watermark_free_images?: boolean;
  addon_image_requests_limit?: number;
  addon_image_requests_used?: number;
  addon_image_requests_price?: number;
  seller_package_id?: number;
  package_data?: any;
  saved_searches_count?: number;
  matches_count?: number;
  telegram_bot_url?: string;
  whatsapp_bot_url?: string;
  invite_url?: string;
  telegram_bot_username?: string;
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
  feature_social_brochure: boolean;
  feature_multi_location: boolean;
  feature_client_intake_bot: boolean;
  feature_backup_service: boolean;
  feature_aged_listings: boolean;
  addon_aged_listings_price: number;
  addon_aged_max_months: number;
  addon_aged_tiers: { months: number; price: number }[];
  addon_saved_searches: number;
  addon_saved_searches_price: number;
  addon_search_tiers: { searches: number; price: number }[];
  feature_watermark_free_images?: boolean;
  included_image_requests?: number;
  addon_image_requests_price?: number;
  addon_image_tiers?: { requests: number; price: number }[];
  sale_enabled?: boolean;
  sale_price?: number;
  sale_discount_percent?: number;
  sale_type?: string;
  sale_expires_at?: string;
  sale_badge_label?: string;
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

export interface SellerPayoutItem {
  id: number;
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

export function SellerPortalView() {
  const [activeTab, setActiveTab] = useState<'agents' | 'packages' | 'earnings' | 'domain' | 'security'>('agents');
  const [dashboard, setDashboard] = useState<SellerDashboardData | null>(null);
  const [agents, setAgents] = useState<SellerAgent[]>([]);
  const [packages, setPackages] = useState<SellerPackageItem[]>([]);
  const [earnings, setEarnings] = useState<{ balance: number; total_earnings: number; transactions: SellerTransactionItem[] } | null>(null);
  const [payouts, setPayouts] = useState<SellerPayoutItem[]>([]);
  const [domainSettings, setDomainSettings] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  // 2FA Security State
  const [totpStatus, setTotpStatus] = useState<{ enabled: boolean; backup_codes_count: number } | null>(null);
  const [showTotpSetup, setShowTotpSetup] = useState(false);
  const [totpSecret, setTotpSecret] = useState('');
  const [otpauthUrl, setOtpauthUrl] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [totpPassword, setTotpPassword] = useState('');
  const [showDisableModal, setShowDisableModal] = useState(false);
  const [totpLoading, setTotpLoading] = useState(false);
  const [totpError, setTotpError] = useState<string | null>(null);
  const [totpSuccess, setTotpSuccess] = useState<string | null>(null);

  // Password change state
  const [currPassword, setCurrPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [savingPassword, setSavingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null);

  // Custom Domain State
  const [domainHost, setDomainHost] = useState('');
  const [brandTitle, setBrandTitle] = useState('');
  const [brandLogo, setBrandLogo] = useState('');
  const [savingDomain, setSavingDomain] = useState(false);
  const [verifyingDns, setVerifyingDns] = useState(false);
  const [dnsResult, setDnsResult] = useState<{ success: boolean; message: string } | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2500);
  };

  // Withdraw Modal State
  const [isWithdrawOpen, setIsWithdrawOpen] = useState(false);
  const [withdrawAmount, setWithdrawAmount] = useState<number>(0);
  const [withdrawCard, setWithdrawCard] = useState('');
  const [withdrawName, setWithdrawName] = useState('');
  const [withdrawIban, setWithdrawIban] = useState('');
  const [withdrawNotes, setWithdrawNotes] = useState('');
  const [withdrawError, setWithdrawError] = useState<string | null>(null);
  const [submittingWithdraw, setSubmittingWithdraw] = useState(false);

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

  // Free Trial Offer Settings State & Modal
  const [isTrialModalOpen, setIsTrialModalOpen] = useState(false);
  const [trialEnabled, setTrialEnabled] = useState(true);
  const [trialDays, setTrialDays] = useState(7);
  const [trialSearches, setTrialSearches] = useState(3);
  const [trialLocations, setTrialLocations] = useState(3);
  const [trialMakler, setTrialMakler] = useState(true);
  const [trialAvm, setTrialAvm] = useState(true);
  const [trialBrochure, setTrialBrochure] = useState(true);
  const [trialMultiLocation, setTrialMultiLocation] = useState(true);
  const [trialWatermarkImages, setTrialWatermarkImages] = useState(true);
  const [trialImageRequests, setTrialImageRequests] = useState(5);
  const [savingTrial, setSavingTrial] = useState(false);
  const [trialSavedMsg, setTrialSavedMsg] = useState(false);

  // Package Modal State
  const [isAddPkgOpen, setIsAddPkgOpen] = useState(false);
  const [editingPkg, setEditingPkg] = useState<SellerPackageItem | null>(null);
  const [pkgName, setPkgName] = useState('');
  const [pkgPrice, setPkgPrice] = useState<number>(49);
  const [pkgDescription, setPkgDescription] = useState('');
  const [pkgPeriod, setPkgPeriod] = useState('monthly');
  const [pkgDuration, setPkgDuration] = useState<number>(30);
  const [pkgMaxSearches, setPkgMaxSearches] = useState<number>(10);
  const [pkgMaxLocations, setPkgMaxLocations] = useState<number>(5);
  const [pkgMakler, setPkgMakler] = useState(true);
  const [pkgAvm, setPkgAvm] = useState(true);
  const [pkgSocialBrochure, setPkgSocialBrochure] = useState(true);
  const [pkgMultiLocation, setPkgMultiLocation] = useState(true);
  const [pkgIntakeBot, setPkgIntakeBot] = useState(false);
  const [pkgBackup, setPkgBackup] = useState(false);
  const [pkgAgedListings, setPkgAgedListings] = useState(false);
  const [pkgAgedPrice, setPkgAgedPrice] = useState<number>(15);
  const [pkgAgedMonths, setPkgAgedMonths] = useState<number>(12);
  const [pkgAddonSearches, setPkgAddonSearches] = useState<number>(0);
  const [pkgAddonSearchesPrice, setPkgAddonSearchesPrice] = useState<number>(10);
  const [pkgAgedTiers, setPkgAgedTiers] = useState<{ months: number; price: number }[]>([]);
  const [pkgSearchTiers, setPkgSearchTiers] = useState<{ searches: number; price: number }[]>([]);
  const [pkgWatermarkImages, setPkgWatermarkImages] = useState(false);
  const [pkgIncludedImages, setPkgIncludedImages] = useState<number>(0);
  const [pkgAddonImagesPrice, setPkgAddonImagesPrice] = useState<number>(10);
  const [pkgImageTiers, setPkgImageTiers] = useState<{ requests: number; price: number }[]>([]);
  
  // Package Promotional Sale State
  const [pkgSaleEnabled, setPkgSaleEnabled] = useState(false);
  const [pkgSalePrice, setPkgSalePrice] = useState<number | undefined>(undefined);
  const [pkgSaleDiscountPercent, setPkgSaleDiscountPercent] = useState<number | undefined>(undefined);
  const [pkgSaleType, setPkgSaleType] = useState<string>('permanent');
  const [pkgSaleExpiresAt, setPkgSaleExpiresAt] = useState<string>('');
  const [pkgSaleBadgeLabel, setPkgSaleBadgeLabel] = useState<string>('');
  
  const [activeTooltip, setActiveTooltip] = useState<string | null>(null);
  const [submittingPkg, setSubmittingPkg] = useState(false);

  // Agent Registration Addon Selections
  const [agentSelectedAgedMonths, setAgentSelectedAgedMonths] = useState<number>(0);
  const [agentSelectedAgedPrice, setAgentSelectedAgedPrice] = useState<number>(0);
  const [agentSelectedExtraSearches, setAgentSelectedExtraSearches] = useState<number>(0);
  const [agentSelectedExtraSearchesPrice, setAgentSelectedExtraSearchesPrice] = useState<number>(0);
  const [agentSelectedImageRequests, setAgentSelectedImageRequests] = useState<number>(0);
  const [agentSelectedImagePrice, setAgentSelectedImagePrice] = useState<number>(0);

  // Agent Detail & Management Modal State
  const [isAgentDetailOpen, setIsAgentDetailOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<SellerAgent | null>(null);
  const [agentModalTab, setAgentModalTab] = useState<'overview' | 'qr' | 'renew' | 'edit'>('overview');
  const [loadingAgentDetail, setLoadingAgentDetail] = useState(false);

  // Edit Agent State
  const [editAgentName, setEditAgentName] = useState('');
  const [editAgentPhone, setEditAgentPhone] = useState('');
  const [editAgentTg, setEditAgentTg] = useState('');
  const [editAgentWa, setEditAgentWa] = useState('');
  const [editAgentChannel, setEditAgentChannel] = useState('telegram');
  const [editAgentStatus, setEditAgentStatus] = useState('active');
  const [editAgentMakler, setEditAgentMakler] = useState(true);
  const [editAgentAvm, setEditAgentAvm] = useState(true);
  const [editAgentBrochure, setEditAgentBrochure] = useState(true);
  const [editAgentMultiLoc, setEditAgentMultiLoc] = useState(true);
  const [editAgentMaxLocs, setEditAgentMaxLocs] = useState(5);
  const [editAgentBot, setEditAgentBot] = useState(false);
  const [editAgentBackup, setEditAgentBackup] = useState(false);
  const [editAgentAged, setEditAgentAged] = useState(false);
  const [editAgentAgedMonths, setEditAgentAgedMonths] = useState(12);
  const [editAgentSearches, setEditAgentSearches] = useState(0);
  const [editAgentWatermarkImages, setEditAgentWatermarkImages] = useState(false);
  const [editAgentImageLimit, setEditAgentImageLimit] = useState(0);
  const [editAgentImageUsed, setEditAgentImageUsed] = useState(0);
  const [savingAgentEdit, setSavingAgentEdit] = useState(false);
  const [agentEditError, setAgentEditError] = useState<string | null>(null);
  const [agentEditSuccessMsg, setAgentEditSuccessMsg] = useState<string | null>(null);

  // Renew Agent State
  const [renewPkgId, setRenewPkgId] = useState<number>(0);
  const [renewAgedMonths, setRenewAgedMonths] = useState<number>(0);
  const [renewAgedPrice, setRenewAgedPrice] = useState<number>(0);
  const [renewExtraSearches, setRenewExtraSearches] = useState<number>(0);
  const [renewExtraSearchesPrice, setRenewExtraSearchesPrice] = useState<number>(0);
  const [renewImageRequests, setRenewImageRequests] = useState<number>(0);
  const [renewImagePrice, setRenewImagePrice] = useState<number>(0);
  const [renewingAgent, setRenewingAgent] = useState(false);
  const [renewError, setRenewError] = useState<string | null>(null);
  const [renewSuccessMsg, setRenewSuccessMsg] = useState<string | null>(null);

  const fetchDashboard = async () => {
    try {
      const res = await api.get('/sellers/me/dashboard');
      setDashboard(res.data);
      if (res.data) {
        setDomainHost(res.data.custom_domain || '');
        setBrandTitle(res.data.custom_brand_title || '');
        setBrandLogo(res.data.custom_brand_logo || '');
        setTrialEnabled(res.data.free_trial_enabled ?? true);
        setTrialDays(res.data.free_trial_duration_days || 7);
        setTrialSearches(res.data.free_trial_max_searches || 3);
        setTrialLocations(res.data.free_trial_max_locations || 3);
        setTrialMakler(res.data.free_trial_feature_makler ?? true);
        setTrialAvm(res.data.free_trial_feature_avm ?? true);
        setTrialBrochure(res.data.free_trial_feature_social_brochure ?? true);
        setTrialMultiLocation(res.data.free_trial_feature_multi_location ?? true);
        setTrialWatermarkImages(res.data.free_trial_feature_watermark_images ?? true);
        setTrialImageRequests(res.data.free_trial_image_requests || 5);
      }
    } catch (err) {
      console.error('Error fetching seller dashboard:', err);
    }
  };

  const handleSaveTrialSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingTrial(true);
    setTrialSavedMsg(false);
    try {
      await api.post('/sellers/me/trial-settings', {
        free_trial_enabled: trialEnabled,
        free_trial_duration_days: trialDays,
        free_trial_max_searches: trialSearches,
        free_trial_max_locations: trialLocations,
        free_trial_feature_makler: trialMakler,
        free_trial_feature_avm: trialAvm,
        free_trial_feature_social_brochure: trialBrochure,
        free_trial_feature_multi_location: trialMultiLocation,
        free_trial_feature_watermark_images: trialWatermarkImages,
        free_trial_image_requests: trialImageRequests
      });
      setTrialSavedMsg(true);
      setIsTrialModalOpen(false);
      setTimeout(() => setTrialSavedMsg(false), 4000);
      fetchDashboard();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Sınaq parametrlərini yadda saxlamaq mümkün olmadı');
    } finally {
      setSavingTrial(false);
    }
  };

  const fetchDomainSettings = async () => {
    try {
      const res = await api.get('/sellers/me/domain');
      setDomainSettings(res.data);
      if (res.data) {
        setDomainHost(res.data.custom_domain || '');
        setBrandTitle(res.data.custom_brand_title || '');
        setBrandLogo(res.data.custom_brand_logo || '');
      }
    } catch (err) {
      console.error('Error fetching domain settings:', err);
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

  const fetchPayouts = async () => {
    try {
      const res = await api.get('/sellers/me/payouts');
      setPayouts(res.data || []);
    } catch (err) {
      console.error('Error fetching payouts:', err);
    }
  };

  const fetchTotpStatus = async () => {
    try {
      const res = await api.get('/auth/2fa/status');
      setTotpStatus(res.data);
    } catch (e) {
      console.error('Error loading 2FA status:', e);
    }
  };

  const handleStartTotpSetup = async () => {
    setTotpLoading(true);
    setTotpError(null);
    setTotpSuccess(null);
    try {
      const res = await api.post('/auth/2fa/setup');
      setTotpSecret(res.data.secret);
      setOtpauthUrl(res.data.otpauth_url);
      setShowTotpSetup(true);
    } catch (e: any) {
      setTotpError(e.response?.data?.detail || '2FA quraşdırmasını başlatmaq mümkün olmadı.');
    } finally {
      setTotpLoading(false);
    }
  };

  const handleEnableTotp = async (e: React.FormEvent) => {
    e.preventDefault();
    setTotpLoading(true);
    setTotpError(null);
    setTotpSuccess(null);
    try {
      const res = await api.post('/auth/2fa/enable', { code: totpCode });
      setBackupCodes(res.data.backup_codes || []);
      setShowTotpSetup(false);
      setTotpCode('');
      setTotpSuccess('İki mərhələli doğrulama (2FA) uğurla aktivləşdirildi! Ehtiyat kodlarınızı təhlükəsiz yerdə saxlayın.');
      await fetchTotpStatus();
    } catch (e: any) {
      setTotpError(e.response?.data?.detail || '2FA təsdiq kodu yanlışdır.');
    } finally {
      setTotpLoading(false);
    }
  };

  const handleDisableTotp = async (e: React.FormEvent) => {
    e.preventDefault();
    setTotpLoading(true);
    setTotpError(null);
    setTotpSuccess(null);
    try {
      await api.post('/auth/2fa/disable', { password: totpPassword });
      setShowDisableModal(false);
      setTotpPassword('');
      setBackupCodes([]);
      setTotpSuccess('2FA uğurla deaktiv edildi.');
      await fetchTotpStatus();
    } catch (e: any) {
      setTotpError(e.response?.data?.detail || 'Şifrə yanlışdır.');
    } finally {
      setTotpLoading(false);
    }
  };

  const handleUpdatePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(null);
    setSavingPassword(true);
    try {
      await api.put('/auth/profile', {
        current_password: currPassword,
        new_password: newPassword
      });
      setCurrPassword('');
      setNewPassword('');
      setPasswordSuccess('Hesab şifrəniz uğurla yeniləndi!');
      setTimeout(() => setPasswordSuccess(null), 4000);
    } catch (e: any) {
      setPasswordError(e.response?.data?.detail || 'Şifrəni yeniləmək mümkün olmadı.');
    } finally {
      setSavingPassword(false);
    }
  };

  const reloadAll = async () => {
    setLoading(true);
    await Promise.all([
      fetchDashboard(),
      fetchAgents(),
      fetchPackages(),
      fetchEarnings(),
      fetchPayouts(),
      fetchDomainSettings(),
      fetchTotpStatus()
    ]);
    setLoading(false);
  };

  const handleRequestPayout = async (e: React.FormEvent) => {
    e.preventDefault();
    setWithdrawError(null);
    setSubmittingWithdraw(true);
    try {
      await api.post('/sellers/me/payouts', {
        amount: withdrawAmount,
        card_number: withdrawCard,
        card_holder_name: withdrawName,
        iban: withdrawIban || undefined,
        notes: withdrawNotes || undefined
      });
      setIsWithdrawOpen(false);
      setWithdrawAmount(0);
      setWithdrawCard('');
      setWithdrawName('');
      setWithdrawIban('');
      setWithdrawNotes('');
      alert('Çıxarış tələbiniz uğurla qeydə alındı!');
      reloadAll();
    } catch (err: any) {
      setWithdrawError(err.response?.data?.detail || 'Çıxarış tələbi göndərilərkən xəta baş verdi.');
    } finally {
      setSubmittingWithdraw(false);
    }
  };

  useEffect(() => {
    reloadAll();
  }, []);

  const handleSaveDomain = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingDomain(true);
    setDnsResult(null);
    try {
      const res = await api.post('/sellers/me/domain', {
        custom_domain: domainHost.trim() || null,
        custom_brand_title: brandTitle.trim() || null,
        custom_brand_logo: brandLogo.trim() || null
      });
      alert(res.data.message || 'Domen parametrləri saxlanıldı.');
      fetchDomainSettings();
      fetchDashboard();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Xəta baş verdi.');
    } finally {
      setSavingDomain(false);
    }
  };

  const handleVerifyDns = async () => {
    setVerifyingDns(true);
    setDnsResult(null);
    try {
      const res = await api.post('/sellers/me/domain/verify');
      setDnsResult({
        success: res.data.success,
        message: res.data.message
      });
      fetchDomainSettings();
      fetchDashboard();
    } catch (err: any) {
      setDnsResult({
        success: false,
        message: err.response?.data?.detail || 'DNS yoxlanışı zamanı xəta baş verdi.'
      });
    } finally {
      setVerifyingDns(false);
    }
  };

  const handleRegisterAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    setAgentError(null);
    setSubmittingAgent(true);
    try {
      const isTrial = agentPkgId === -1 || agentPkgId === undefined;
      await api.post('/sellers/me/agents', {
        name: agentName,
        phone: agentPhone,
        telegram_handle: agentTg || undefined,
        whatsapp_number: agentWhatsapp || undefined,
        preferred_channel: agentChannel,
        package_id: isTrial ? undefined : agentPkgId,
        is_trial: isTrial,
        selected_aged_months: agentSelectedAgedMonths > 0 ? agentSelectedAgedMonths : undefined,
        selected_aged_price: agentSelectedAgedPrice > 0 ? agentSelectedAgedPrice : undefined,
        selected_extra_searches: agentSelectedExtraSearches > 0 ? agentSelectedExtraSearches : undefined,
        selected_extra_searches_price: agentSelectedExtraSearchesPrice > 0 ? agentSelectedExtraSearchesPrice : undefined,
        selected_image_requests: agentSelectedImageRequests > 0 ? agentSelectedImageRequests : undefined,
        selected_image_price: agentSelectedImagePrice > 0 ? agentSelectedImagePrice : undefined
      });
      setIsAddAgentOpen(false);
      setAgentName('');
      setAgentPhone('');
      setAgentTg('');
      setAgentWhatsapp('');
      setAgentPkgId(undefined);
      setAgentSelectedAgedMonths(0);
      setAgentSelectedAgedPrice(0);
      setAgentSelectedExtraSearches(0);
      setAgentSelectedExtraSearchesPrice(0);
      setAgentSelectedImageRequests(0);
      setAgentSelectedImagePrice(0);
      reloadAll();
    } catch (err: any) {
      setAgentError(err.response?.data?.detail || 'Xəta baş verdi');
    } finally {
      setSubmittingAgent(false);
    }
  };

  const openAgentDetail = async (agent: SellerAgent, defaultTab: 'overview' | 'qr' | 'renew' | 'edit' = 'overview') => {
    setSelectedAgent(agent);
    setAgentModalTab(defaultTab);
    setIsAgentDetailOpen(true);
    setAgentEditError(null);
    setAgentEditSuccessMsg(null);
    setRenewError(null);
    setRenewSuccessMsg(null);

    // Initialize edit fields
    setEditAgentName(agent.name);
    setEditAgentPhone(agent.phone);
    setEditAgentTg(agent.telegram_handle || '');
    setEditAgentWa(agent.whatsapp_number || '');
    setEditAgentChannel(agent.preferred_channel || 'telegram');
    setEditAgentStatus(agent.status || 'active');
    setEditAgentMakler(agent.feature_makler_detector ?? true);
    setEditAgentAvm(agent.feature_avm_bargain_finder ?? true);
    setEditAgentBrochure(agent.feature_social_brochure ?? true);
    setEditAgentMultiLoc(agent.feature_multi_location ?? true);
    setEditAgentMaxLocs(agent.max_locations_per_search || 5);
    setEditAgentBot(agent.feature_client_intake_bot ?? false);
    setEditAgentBackup(agent.backup_enabled ?? false);
    setEditAgentAged(agent.feature_aged_listings ?? false);
    setEditAgentAgedMonths(agent.addon_aged_max_months || 12);
    setEditAgentSearches(agent.addon_saved_searches || 0);
    setEditAgentWatermarkImages(agent.feature_watermark_free_images ?? false);
    setEditAgentImageLimit(agent.addon_image_requests_limit || 0);
    setEditAgentImageUsed(agent.addon_image_requests_used || 0);

    // Initialize renew fields (0 means keep current/transferred plan)
    const defaultPkgId = agent.seller_package_id || 0;
    setRenewPkgId(defaultPkgId);
    setRenewAgedMonths(0);
    setRenewAgedPrice(0);
    setRenewExtraSearches(0);
    setRenewExtraSearchesPrice(0);
    setRenewImageRequests(0);
    setRenewImagePrice(0);

    // Fetch fresh details with counts & QR URLs
    setLoadingAgentDetail(true);
    try {
      const res = await api.get(`/sellers/me/agents/${agent.id}`);
      setSelectedAgent(res.data);
      if (res.data) {
        setEditAgentName(res.data.name);
        setEditAgentPhone(res.data.phone);
        setEditAgentTg(res.data.telegram_handle || '');
        setEditAgentWa(res.data.whatsapp_number || '');
        setEditAgentChannel(res.data.preferred_channel || 'telegram');
        setEditAgentStatus(res.data.status || 'active');
        setEditAgentMakler(res.data.feature_makler_detector ?? true);
        setEditAgentAvm(res.data.feature_avm_bargain_finder ?? true);
        setEditAgentBrochure(res.data.feature_social_brochure ?? true);
        setEditAgentMultiLoc(res.data.feature_multi_location ?? true);
        setEditAgentMaxLocs(res.data.max_locations_per_search || 5);
        setEditAgentBot(res.data.feature_client_intake_bot ?? false);
        setEditAgentBackup(res.data.backup_enabled ?? false);
        setEditAgentAged(res.data.feature_aged_listings ?? false);
        setEditAgentAgedMonths(res.data.addon_aged_max_months || 12);
        setEditAgentSearches(res.data.addon_saved_searches || 0);
        setEditAgentWatermarkImages(res.data.feature_watermark_free_images ?? false);
        setEditAgentImageLimit(res.data.addon_image_requests_limit || 0);
        setEditAgentImageUsed(res.data.addon_image_requests_used || 0);
        if (res.data.seller_package_id) {
          setRenewPkgId(res.data.seller_package_id);
        } else {
          setRenewPkgId(0);
        }
      }
    } catch (err) {
      console.error('Error fetching agent detail:', err);
    } finally {
      setLoadingAgentDetail(false);
    }
  };

  const handleSaveAgentEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAgent) return;
    setSavingAgentEdit(true);
    setAgentEditError(null);
    setAgentEditSuccessMsg(null);

    try {
      await api.put(`/sellers/me/agents/${selectedAgent.id}`, {
        name: editAgentName,
        phone: editAgentPhone,
        telegram_handle: editAgentTg || undefined,
        whatsapp_number: editAgentWa || undefined,
        preferred_channel: editAgentChannel,
        status: editAgentStatus,
        feature_makler_detector: editAgentMakler,
        feature_avm_bargain_finder: editAgentAvm,
        feature_social_brochure: editAgentBrochure,
        feature_multi_location: editAgentMultiLoc,
        max_locations_per_search: editAgentMaxLocs,
        feature_client_intake_bot: editAgentBot,
        backup_enabled: editAgentBackup,
        feature_aged_listings: editAgentAged,
        addon_aged_max_months: editAgentAgedMonths,
        addon_saved_searches: editAgentSearches,
        feature_watermark_free_images: editAgentWatermarkImages,
        addon_image_requests_limit: editAgentImageLimit,
        addon_image_requests_used: editAgentImageUsed
      });

      setAgentEditSuccessMsg('Agent məlumatları uğurla yeniləndi!');
      fetchAgents();
      // Refresh current detail
      const res = await api.get(`/sellers/me/agents/${selectedAgent.id}`);
      setSelectedAgent(res.data);
    } catch (err: any) {
      setAgentEditError(err.response?.data?.detail || 'Məlumatları yeniləyərkən xəta baş verdi.');
    } finally {
      setSavingAgentEdit(false);
    }
  };

  const handleRenewAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAgent) return;
    setRenewingAgent(true);
    setRenewError(null);
    setRenewSuccessMsg(null);

    try {
      const isCustomPlan = renewPkgId === 0;
      const res = await api.post(`/sellers/me/agents/${selectedAgent.id}/renew`, {
        package_id: isCustomPlan ? undefined : renewPkgId,
        custom_price: isCustomPlan ? (selectedAgent.plan_price || 50.0) : undefined,
        selected_aged_months: renewAgedMonths > 0 ? renewAgedMonths : undefined,
        selected_aged_price: renewAgedPrice > 0 ? renewAgedPrice : undefined,
        selected_extra_searches: renewExtraSearches > 0 ? renewExtraSearches : undefined,
        selected_extra_searches_price: renewExtraSearchesPrice > 0 ? renewExtraSearchesPrice : undefined,
        selected_image_requests: renewImageRequests > 0 ? renewImageRequests : undefined,
        selected_image_price: renewImagePrice > 0 ? renewImagePrice : undefined
      });

      setRenewSuccessMsg(res.data.message || 'Abunə uğurla yeniləndi!');
      reloadAll();
      // Refresh current detail
      const detailRes = await api.get(`/sellers/me/agents/${selectedAgent.id}`);
      setSelectedAgent(detailRes.data);
    } catch (err: any) {
      setRenewError(err.response?.data?.detail || 'Abunəni yeniləyərkən xəta baş verdi.');
    } finally {
      setRenewingAgent(false);
    }
  };

  const handleSavePackage = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingPkg(true);
    try {
      const payload = {
        name: pkgName,
        price: pkgPrice,
        description: pkgDescription || undefined,
        period: pkgPeriod,
        duration_days: pkgDuration,
        max_searches: pkgMaxSearches,
        max_locations: pkgMaxLocations,
        feature_makler_detector: pkgMakler,
        feature_avm_bargain_finder: pkgAvm,
        feature_social_brochure: pkgSocialBrochure,
        feature_multi_location: pkgMultiLocation,
        feature_client_intake_bot: pkgIntakeBot,
        feature_backup_service: pkgBackup,
        feature_aged_listings: pkgAgedListings,
        addon_aged_listings_price: pkgAgedPrice,
        addon_aged_max_months: pkgAgedMonths,
        addon_aged_tiers: pkgAgedTiers,
        addon_saved_searches: pkgAddonSearches,
        addon_saved_searches_price: pkgAddonSearchesPrice,
        addon_search_tiers: pkgSearchTiers,
        feature_watermark_free_images: pkgWatermarkImages,
        included_image_requests: pkgIncludedImages,
        addon_image_requests_price: pkgAddonImagesPrice,
        addon_image_tiers: pkgImageTiers,
        sale_enabled: pkgSaleEnabled,
        sale_price: pkgSaleEnabled ? pkgSalePrice : undefined,
        sale_discount_percent: pkgSaleEnabled ? pkgSaleDiscountPercent : undefined,
        sale_type: pkgSaleType,
        sale_expires_at: pkgSaleExpiresAt ? new Date(pkgSaleExpiresAt).toISOString() : undefined,
        sale_badge_label: pkgSaleBadgeLabel || undefined
      };

      if (editingPkg) {
        await api.put(`/sellers/me/packages/${editingPkg.id}`, payload);
      } else {
        await api.post('/sellers/me/packages', payload);
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
    setPkgPrice(Math.max(49, dashboard?.min_package_price || 29));
    setPkgDescription('');
    setPkgPeriod('monthly');
    setPkgDuration(30);
    setPkgMaxSearches(10);
    setPkgMaxLocations(5);
    setPkgMakler(true);
    setPkgAvm(true);
    setPkgSocialBrochure(true);
    setPkgMultiLocation(true);
    setPkgIntakeBot(false);
    setPkgBackup(false);
    setPkgAgedListings(false);
    setPkgAgedPrice(15);
    setPkgAgedMonths(12);
    setPkgAddonSearches(0);
    setPkgAddonSearchesPrice(10);
    setPkgAgedTiers([{ months: 3, price: 15 }, { months: 6, price: 25 }, { months: 12, price: 40 }]);
    setPkgSearchTiers([{ searches: 5, price: 10 }, { searches: 10, price: 18 }, { searches: 20, price: 30 }]);
    setPkgWatermarkImages(false);
    setPkgIncludedImages(0);
    setPkgAddonImagesPrice(10);
    setPkgImageTiers([{ requests: 25, price: 10 }, { requests: 50, price: 18 }, { requests: 100, price: 30 }]);
    setPkgSaleEnabled(false);
    setPkgSalePrice(undefined);
    setPkgSaleDiscountPercent(undefined);
    setPkgSaleType('permanent');
    setPkgSaleExpiresAt('');
    setPkgSaleBadgeLabel('');
    setIsAddPkgOpen(true);
  };

  const openEditPkgModal = (pkg: SellerPackageItem) => {
    setEditingPkg(pkg);
    setPkgName(pkg.name);
    setPkgPrice(pkg.price);
    setPkgDescription(pkg.description || '');
    setPkgPeriod(pkg.period);
    setPkgDuration(pkg.duration_days);
    setPkgMaxSearches(pkg.max_searches || 10);
    setPkgMaxLocations(pkg.max_locations || 5);
    setPkgMakler(pkg.feature_makler_detector);
    setPkgAvm(pkg.feature_avm_bargain_finder);
    setPkgSocialBrochure(pkg.feature_social_brochure ?? true);
    setPkgMultiLocation(pkg.feature_multi_location ?? true);
    setPkgIntakeBot(pkg.feature_client_intake_bot ?? false);
    setPkgBackup(pkg.feature_backup_service ?? false);
    setPkgAgedListings(pkg.feature_aged_listings ?? false);
    setPkgAgedPrice(pkg.addon_aged_listings_price ?? 15);
    setPkgAgedMonths(pkg.addon_aged_max_months ?? 12);
    setPkgAddonSearches(pkg.addon_saved_searches ?? 0);
    setPkgAddonSearchesPrice(pkg.addon_saved_searches_price ?? 10);
    setPkgAgedTiers(pkg.addon_aged_tiers || []);
    setPkgSearchTiers(pkg.addon_search_tiers || []);
    setPkgWatermarkImages(pkg.feature_watermark_free_images ?? false);
    setPkgIncludedImages(pkg.included_image_requests ?? 0);
    setPkgAddonImagesPrice(pkg.addon_image_requests_price ?? 10);
    setPkgImageTiers(pkg.addon_image_tiers && pkg.addon_image_tiers.length > 0 ? pkg.addon_image_tiers : [
      { requests: 25, price: 10 },
      { requests: 50, price: 18 },
      { requests: 100, price: 30 }
    ]);
    setPkgSaleEnabled(pkg.sale_enabled ?? false);
    setPkgSalePrice(pkg.sale_price);
    setPkgSaleDiscountPercent(pkg.sale_discount_percent);
    setPkgSaleType(pkg.sale_type || 'permanent');
    setPkgSaleExpiresAt(pkg.sale_expires_at ? pkg.sale_expires_at.split('T')[0] : '');
    setPkgSaleBadgeLabel(pkg.sale_badge_label || '');
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
      {/* Welcome Banner & Rank Progression */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 p-6 rounded-3xl border border-slate-800 backdrop-blur-md shadow-2xl relative overflow-hidden space-y-5">
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

        {/* Rank Progression Bar & Perks Banner */}
        {dashboard && (
          <div className="pt-3 border-t border-slate-800/80 relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-950/40 p-4 rounded-2xl border border-slate-800/50">
            <div className="space-y-1.5 flex-1 max-w-xl">
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-slate-300 flex items-center gap-1.5">
                  <span>{dashboard.rank_emoji || '🥉'}</span>
                  <span>Dərəcəniz: <strong>{dashboard.rank_label || dashboard.rank}</strong></span>
                  {dashboard.bonus_commission ? (
                    <span className="text-amber-400 font-bold bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
                      +{dashboard.bonus_commission}% Bonus Komissiya
                    </span>
                  ) : null}
                </span>
                {dashboard.next_rank && dashboard.next_sales_target ? (
                  <span className="text-cyan-400">
                    Hədəf: {dashboard.total_sales_volume.toLocaleString()} / {dashboard.next_sales_target.toLocaleString()} AZN ({dashboard.next_rank})
                  </span>
                ) : (
                  <span className="text-emerald-400 font-bold">Maksimum Səviyyə 💎</span>
                )}
              </div>

              {dashboard.next_rank && dashboard.next_sales_target ? (
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-blue-500 to-cyan-400 h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.min(100, Math.max(5, (dashboard.total_sales_volume / dashboard.next_sales_target) * 100))}%`
                    }}
                  />
                </div>
              ) : null}
            </div>

            <div className="flex items-center gap-3 text-xs text-slate-300 shrink-0">
              <div className="px-3 py-1.5 bg-slate-900 rounded-xl border border-slate-800">
                <span className="text-slate-500 mr-1">Paket Limiti:</span>
                <span className="font-bold text-white">{dashboard.rank_max_packages || 5} ədəd</span>
              </div>
              <div className="px-3 py-1.5 bg-slate-900 rounded-xl border border-slate-800">
                <span className="text-slate-500 mr-1">Fərdi Domen:</span>
                <span className={`font-bold ${dashboard.rank_custom_domain_allowed ? 'text-emerald-400' : 'text-slate-500'}`}>
                  {dashboard.rank_custom_domain_allowed ? 'Aktiv (İcazəli)' : 'Gold+ ilə açılır'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800/80">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Məcmu Nağd Satış</span>
            <div className="p-2 bg-emerald-500/10 rounded-xl text-emerald-400 border border-emerald-500/20">
              <DollarSign className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-black text-white">
            {dashboard?.total_sales_volume?.toLocaleString() || 0} <span className="text-sm font-bold text-slate-400">AZN</span>
          </p>
          <span className="text-[10px] text-slate-500 mt-0.5 block">Agentlərdən toplanan nağd məbləğ</span>
        </div>

        <div className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800/80">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Xalis Qazancınız</span>
            <div className="p-2 bg-blue-500/10 rounded-xl text-blue-400 border border-blue-500/20">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-black text-emerald-400">
            {dashboard?.total_earnings?.toLocaleString() || 0} <span className="text-sm font-bold text-emerald-500/70">AZN</span>
          </p>
          <span className="text-[10px] text-slate-500 mt-0.5 block">Sizdə qalan xalis gəlir payı</span>
        </div>

        <div className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800/80">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Komissiya Faiziniz</span>
            <div className="p-2 bg-indigo-500/10 rounded-xl text-indigo-400 border border-indigo-500/20">
              <Award className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-black text-indigo-400 flex items-center gap-1.5">
            <span>%{dashboard?.effective_commission_rate ?? dashboard?.commission_rate ?? 70}</span>
            {dashboard?.bonus_commission ? (
              <span className="text-[11px] font-bold text-amber-400">
                (+%{dashboard.bonus_commission})
              </span>
            ) : null}
          </p>
          <span className="text-[10px] text-slate-500 mt-0.5 block">Satışdan satıcıya qalan %</span>
        </div>

        <div className="bg-slate-900/60 p-5 rounded-2xl border border-cyan-500/30 shadow-lg shadow-cyan-500/5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-cyan-300 uppercase tracking-wider">Adminə Qalan Pay</span>
            <div className="p-2 bg-cyan-500/10 rounded-xl text-cyan-400 border border-cyan-500/20">
              <Shield className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-black text-rose-400">
            {(dashboard?.pending_platform_debt || 0) > 0 ? `${dashboard?.pending_platform_debt?.toLocaleString()} AZN` : '0 AZN (Təhvil verildi)'}
          </p>
          <span className="text-[10px] text-slate-500 mt-0.5 block">Adminə nağd təhvil verilməli</span>
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
          <span className="text-[10px] text-slate-500 mt-0.5 block">Paket sayı: {packages.length}</span>
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
          <span>Paketlərim ({packages.length + 1})</span>
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

        <button
          onClick={() => setActiveTab('domain')}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm transition ${
            activeTab === 'domain'
              ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-500/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
          }`}
        >
          <Globe className="w-4 h-4" />
          <span>Fərdi Domenim (White-label)</span>
        </button>

        <button
          onClick={() => setActiveTab('security')}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm transition ${
            activeTab === 'security'
              ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-500/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
          }`}
        >
          <ShieldCheck className="w-4 h-4" />
          <span>Təhlükəsizlik & 2FA</span>
          {totpStatus?.enabled && (
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          )}
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
                    <th className="py-3.5 px-4">Paket & Addon</th>
                    <th className="py-3.5 px-4">Status</th>
                    <th className="py-3.5 px-4">Bitmə Vaxtı</th>
                    <th className="py-3.5 px-4 text-right">Əməliyyatlar</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {agents.map((a) => {
                    const isExp = a.is_expired;
                    return (
                      <tr 
                        key={a.id} 
                        onClick={() => openAgentDetail(a, 'overview')}
                        className="hover:bg-slate-800/40 transition cursor-pointer group"
                      >
                        <td className="py-3.5 px-4">
                          <div className="font-bold text-white group-hover:text-blue-400 transition flex items-center gap-2">
                            <span>{a.name}</span>
                            <span className="text-[10px] text-slate-500 font-mono">#{a.id}</span>
                          </div>
                          <div className="text-[11px] text-slate-400">{a.phone}</div>
                        </td>
                        <td className="py-3.5 px-4 text-xs">
                          {a.telegram_handle ? (
                            <div className="text-blue-400 font-mono">@{a.telegram_handle}</div>
                          ) : a.whatsapp_number ? (
                            <div className="text-emerald-400 font-mono">{a.whatsapp_number}</div>
                          ) : (
                            <span className="text-slate-500">—</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4">
                          <span className={`capitalize text-xs font-semibold px-2 py-0.5 rounded-md ${
                            a.preferred_channel === 'telegram'
                              ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                              : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          }`}>
                            {a.preferred_channel}
                          </span>
                        </td>
                        <td className="py-3.5 px-4">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="font-semibold text-emerald-400 text-xs">{a.plan}</span>
                            {a.plan_price !== undefined && a.plan_price > 0 && (
                              <span className="text-[10px] text-slate-400 font-mono">({a.plan_price} ₼)</span>
                            )}
                            {a.is_transferred && (
                              <span className="text-[9px] px-1.5 py-0.2 rounded bg-purple-500/15 text-purple-300 border border-purple-500/25 font-semibold">
                                Köçürülmüş
                              </span>
                            )}
                          </div>
                          <div className="flex flex-wrap gap-1 mt-0.5">
                            {a.feature_aged_listings && (
                              <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                                📦 Arxiv ({a.addon_aged_max_months || 12}ay)
                              </span>
                            )}
                            {(a.addon_saved_searches ?? 0) > 0 && (
                              <span className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                                ⚡ +{a.addon_saved_searches} axtarış
                              </span>
                            )}
                            {a.feature_watermark_free_images && (
                              <span className="text-[9px] px-1.5 py-0.5 rounded bg-teal-500/10 text-teal-400 border border-teal-500/20">
                                🖼️ {a.addon_image_requests_used || 0}/{a.addon_image_requests_limit || 0} foto
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-3.5 px-4">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                            isExp
                              ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                              : a.status === 'active'
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                              : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                          }`}>
                            {isExp ? 'Bitib' : a.status === 'active' ? 'Aktiv' : a.status}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-xs text-slate-400">
                          {a.plan_expires_at ? (
                            <div>
                              <div className={isExp ? 'text-rose-400 font-semibold' : 'text-slate-300'}>
                                {new Date(a.plan_expires_at).toLocaleDateString('az-AZ')}
                              </div>
                              <div className="text-[10px] text-slate-500">
                                {isExp ? 'Müddət bitib' : 'Aktiv abunə'}
                              </div>
                            </div>
                          ) : (
                            <span className="text-slate-500">Limitsiz</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              type="button"
                              onClick={() => openAgentDetail(a, 'qr')}
                              className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 border border-indigo-500/20 transition text-xs flex items-center gap-1 font-semibold"
                              title="QR Kod & Bot Linki"
                            >
                              <QrCode className="w-3.5 h-3.5" />
                              <span className="hidden sm:inline">QR</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => openAgentDetail(a, 'renew')}
                              className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 border border-emerald-500/20 transition text-xs flex items-center gap-1 font-semibold"
                              title="Abunəni Yenilə"
                            >
                              <RefreshCw className="w-3.5 h-3.5" />
                              <span className="hidden sm:inline">Yenilə</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => openAgentDetail(a, 'edit')}
                              className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 transition text-xs flex items-center gap-1 font-semibold"
                              title="Redaktə Et"
                            >
                              <Edit3 className="w-3.5 h-3.5" />
                              <span className="hidden sm:inline">Redaktə</span>
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: PACKAGES */}
      {activeTab === 'packages' && (
        <div className="space-y-6">
          {trialSavedMsg && (
            <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-bold flex items-center gap-2 animate-in fade-in">
              <CheckCircle className="w-4 h-4 shrink-0" />
              <span>Pulsuz sınaq parametrləri uğurla yadda saxlanıldı!</span>
            </div>
          )}

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold text-white">Paketlərim və Sınaq Təklifim</h2>
              <p className="text-xs text-slate-400">Agentləriniz üçün pulsuz sınaq şərtləri və fərdi ödənişli abunə paketləri qurun.</p>
            </div>
            <button
              onClick={openAddPkgModal}
              className="flex items-center gap-1.5 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-bold shadow-lg shadow-blue-500/25 transition self-start sm:self-auto"
            >
              <Plus className="w-4 h-4" />
              <span>Yeni Paket Yarat</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* CARD 1: DEDICATED FREE TRIAL CARD */}
            <div className="bg-gradient-to-b from-indigo-950/40 via-slate-900/80 to-slate-900/70 border border-indigo-500/30 rounded-3xl p-6 shadow-xl relative overflow-hidden flex flex-col justify-between hover:border-indigo-400/50 transition">
              <div className="space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 mb-2">
                      <Gift className="w-3 h-3 text-indigo-400" />
                      <span>Pulsuz Sınaq Paketi</span>
                    </span>
                    <h3 className="text-xl font-bold text-white">Pulsuz Sınaq (Free Trial)</h3>
                    <p className="text-xs text-slate-400 mt-0.5">Yeni agentlər üçün başlanğıc test paketi</p>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      trialEnabled ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-400'
                    }`}>
                      {trialEnabled ? 'Aktiv' : 'Deaktiv'}
                    </span>
                    <button
                      onClick={() => setIsTrialModalOpen(true)}
                      className="p-1.5 text-slate-400 hover:text-white bg-slate-800/80 rounded-lg transition"
                      title="Sınaq parametrlərini dəyiş"
                    >
                      <Edit3 className="w-4 h-4 text-indigo-400" />
                    </button>
                  </div>
                </div>

                <div className="pt-2">
                  <span className="text-3xl font-black text-white">0 AZN</span>
                  <span className="text-xs text-indigo-300 ml-1.5 font-medium">/ {trialDays} gün sınaq</span>
                </div>

                <div className="space-y-2 text-xs text-slate-300 pt-2 border-t border-indigo-500/20">
                  <div className="flex items-center gap-2">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>{trialSearches} Paralel Axtarış Limiti</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>{trialDays} Gün Aktivlik Müddəti</span>
                  </div>
                  {trialMultiLocation && (
                    <div className="flex items-center gap-2">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>Çoxsaylı Məkan & Metro Axtarışı (max {trialLocations})</span>
                    </div>
                  )}
                  {trialMakler && (
                    <div className="flex items-center gap-2">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>AI Makler & Vasitəçi Detektoru</span>
                    </div>
                  )}
                  {trialAvm && (
                    <div className="flex items-center gap-2">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>AVM Bazar Qiyməti & Fürsət Bildirişi</span>
                    </div>
                  )}
                  {trialBrochure && (
                    <div className="flex items-center gap-2">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>PDF & Sosial Şəbəkə Buklet Generatoru</span>
                    </div>
                  )}
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-indigo-500/20 flex items-center justify-between">
                <button
                  onClick={() => setIsTrialModalOpen(true)}
                  className="w-full py-2 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 hover:text-white border border-indigo-500/30 rounded-xl text-xs font-bold transition flex items-center justify-center gap-1.5"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                  <span>Sınaq Parametrlərini Düzəliş Et</span>
                </button>
              </div>
            </div>

            {/* PAID PACKAGES */}
            {packages.map((pkg) => (
              <div key={pkg.id} className="bg-slate-900/70 border border-slate-800 rounded-3xl p-6 shadow-xl relative overflow-hidden flex flex-col justify-between hover:border-slate-700 transition">
                <div className="space-y-4">
                  <div className="flex items-start justify-between">
                    <div>
                      {pkg.sale_enabled && (
                        <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/15 text-rose-300 border border-rose-500/30">
                            <Sparkles className="w-3 h-3 text-rose-400" />
                            <span>{pkg.sale_badge_label || `🔥 ${pkg.sale_discount_percent ? `${pkg.sale_discount_percent}% ENDİRİM` : 'XÜSUSİ TƏKLİF'}`}</span>
                          </span>
                          {pkg.sale_type === 'first_month' && (
                            <span className="text-[9px] px-2 py-0.2 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/25 font-semibold">
                              İlk 1 ay
                            </span>
                          )}
                          {pkg.sale_type === 'first_3_months' && (
                            <span className="text-[9px] px-2 py-0.2 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/25 font-semibold">
                              İlk 3 ay
                            </span>
                          )}
                          {pkg.sale_type === 'first_6_months' && (
                            <span className="text-[9px] px-2 py-0.2 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/25 font-semibold">
                              İlk 6 ay
                            </span>
                          )}
                        </div>
                      )}
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
                    {pkg.sale_enabled && pkg.sale_price !== undefined ? (
                      <div>
                        <div className="flex items-baseline gap-2">
                          <span className="text-3xl font-black text-emerald-400">{pkg.sale_price} AZN</span>
                          <span className="text-sm font-bold text-slate-500 line-through">{pkg.price} AZN</span>
                          <span className="text-xs text-slate-400 ml-1">/ {pkg.period === 'monthly' ? 'aylıq' : pkg.period}</span>
                        </div>
                        <span className="text-[10px] text-emerald-400/80 font-medium block mt-0.5">
                          {pkg.sale_type === 'first_month' && '⚡ İlk 1 ay endirimlə, sonrakı aylar standart qiymət'}
                          {pkg.sale_type === 'first_3_months' && '⚡ İlk 3 ay endirimlə, sonrakı aylar standart qiymət'}
                          {pkg.sale_type === 'first_6_months' && '⚡ İlk 6 ay endirimlə, sonrakı aylar standart qiymət'}
                          {pkg.sale_type === 'limited_time' && pkg.sale_expires_at && `⚡ Kampaniya bitmə tarixi: ${new Date(pkg.sale_expires_at).toLocaleDateString('az-AZ')}`}
                          {pkg.sale_type === 'permanent' && '⚡ Bütün abunəlik müddəti üçün daimi endirim'}
                        </span>
                      </div>
                    ) : (
                      <div>
                        <span className="text-3xl font-black text-white">{pkg.price} AZN</span>
                        <span className="text-xs text-slate-400 ml-1.5">/ {pkg.period === 'monthly' ? 'aylıq' : pkg.period}</span>
                      </div>
                    )}
                  </div>

                  <div className="space-y-2 text-xs text-slate-300 pt-2 border-t border-slate-800">
                    <div className="flex items-center gap-2">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>{pkg.max_searches} Paralel Axtarış Limiti</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>{pkg.duration_days} Gün Aktivlik Müddəti</span>
                    </div>
                    {pkg.feature_multi_location && (
                      <div className="flex items-center gap-2">
                        <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                        <span>Çoxsaylı Məkan & Metro Axtarışı (max {pkg.max_locations || 5})</span>
                      </div>
                    )}
                    {pkg.feature_makler_detector && (
                      <div className="flex items-center gap-2">
                        <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                        <span>AI Makler & Vasitəçi Detektoru</span>
                      </div>
                    )}
                    {pkg.feature_avm_bargain_finder && (
                      <div className="flex items-center gap-2">
                        <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                        <span>AVM Bazar Qiyməti & Fırsət Bildirişi</span>
                      </div>
                    )}
                    {pkg.feature_social_brochure && (
                      <div className="flex items-center gap-2">
                        <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                        <span>PDF & Sosial Şəbəkə Buklet Generatoru</span>
                      </div>
                    )}
                    {pkg.feature_client_intake_bot && (
                      <div className="flex items-center gap-2">
                        <Check className="w-4 h-4 text-indigo-400 shrink-0" />
                        <span className="text-indigo-300">Brendli Müştəri Qəbul Botu</span>
                      </div>
                    )}
                    {pkg.feature_backup_service && (
                      <div className="flex items-center gap-2">
                        <Check className="w-4 h-4 text-purple-400 shrink-0" />
                        <span className="text-purple-300">Avtomatik BaaS Data Backup</span>
                      </div>
                    )}
                    {pkg.addon_saved_searches > 0 && (
                      <div className="flex items-center gap-2 text-cyan-400 font-semibold bg-cyan-500/10 px-2 py-1 rounded-lg border border-cyan-500/20">
                        <span>⚡ +{pkg.addon_saved_searches} Əlavə Axtarış (+{pkg.addon_saved_searches_price} AZN)</span>
                      </div>
                    )}
                    {pkg.feature_aged_listings && (
                      <div className="flex items-center gap-2 text-amber-400 font-semibold bg-amber-500/10 px-2 py-1 rounded-lg border border-amber-500/20">
                        <span>📦 Köhnə Elanlar Arxivi ({pkg.addon_aged_max_months || 12} ay) (+{pkg.addon_aged_listings_price} AZN)</span>
                      </div>
                    )}
                    {pkg.feature_watermark_free_images && (
                      <div className="flex items-center gap-2 text-teal-400 font-semibold bg-teal-500/10 px-2 py-1 rounded-lg border border-teal-500/20">
                        <span>🖼️ Su Nişansız Foto ({pkg.included_image_requests || 0} daxildir)</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-800/80 space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">Qazancınız (%{dashboard?.effective_commission_rate ?? dashboard?.commission_rate ?? 70}):</span>
                    <span className="font-bold text-emerald-400">+{((pkg.price * (dashboard?.effective_commission_rate ?? dashboard?.commission_rate ?? 70)) / 100).toFixed(1)} AZN</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => openEditPkgModal(pkg)}
                      className="flex-1 py-2 bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 hover:text-white border border-blue-500/30 rounded-xl text-xs font-bold transition flex items-center justify-center gap-1.5"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      <span>Paketi Redaktə Et</span>
                    </button>
                    <button
                      onClick={() => handleDeletePackage(pkg)}
                      className="p-2 text-rose-400 hover:text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 rounded-xl transition"
                      title="Paketi sil"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: EARNINGS & TRANSACTIONS */}
      {activeTab === 'earnings' && (
        <div className="space-y-6">
          {/* Cash Settlement Summary Card */}
          <div className="bg-slate-900/80 rounded-3xl border border-cyan-500/30 p-6 backdrop-blur-md shadow-xl relative overflow-hidden">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-cyan-400 font-bold text-sm">
                  <span>💵</span>
                  <span>Nağd Yığım və Platforma Hesablaşması (Cash Settlement)</span>
                </div>
                <h3 className="text-xl font-black text-white">
                  Agentlərdən Nağd Yığılan Məbləğ və Admin Payı
                </h3>
                <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
                  Siz agentlərinizdən paket ödənişlərini <strong>birbaşa nağd</strong> qəbul edirsiniz. Komissiya payınız (<strong>%{dashboard?.effective_commission_rate ?? dashboard?.commission_rate ?? 70}</strong>) birbaşa sizin xalis qazancınız olaraq qalır, platforma haqqı (<strong>%{100 - (dashboard?.effective_commission_rate ?? dashboard?.commission_rate ?? 70)}</strong>) isə sistem admininə nağd təhvil verilir.
                </p>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 shrink-0">
                <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-400 block">Cəmi Nağd Satış</span>
                  <span className="text-base font-bold text-white">{dashboard?.total_sales_volume?.toLocaleString() || 0} AZN</span>
                </div>
                <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-400 block">Sizin Xalis Qazancınız</span>
                  <span className="text-base font-black text-emerald-400">+{dashboard?.total_earnings?.toLocaleString() || 0} AZN</span>
                </div>
                <div className="p-3 bg-slate-950/60 rounded-xl border border-cyan-500/30 col-span-2 sm:col-span-1">
                  <span className="text-[10px] text-cyan-300 block">Adminə Təhvil Verilməli Pay</span>
                  <span className="text-base font-black text-rose-400">
                    {(dashboard?.pending_platform_debt || 0) > 0 ? `${dashboard?.pending_platform_debt?.toLocaleString()} AZN` : '0 AZN (Tam Təhvil)'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-slate-900/60 rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
            <div className="p-5 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-white">Satış və Komissiya Əməliyyatları</h2>
                <p className="text-xs text-slate-400">Agentlərinizin paket satışları və qeydə alınan hesablaşmalar.</p>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <span className="text-xs text-slate-400 block">Gələcək Onlayn Çıxarış</span>
                  <span className="text-xl font-black text-emerald-400">{dashboard?.balance.toLocaleString()} AZN</span>
                </div>
                <button
                  onClick={() => {
                    setWithdrawError(null);
                    setWithdrawAmount(dashboard?.balance || 0);
                    setIsWithdrawOpen(true);
                  }}
                  disabled={!dashboard?.balance || dashboard.balance <= 0}
                  className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold rounded-xl text-xs border border-slate-700 transition disabled:opacity-40"
                  title="Gələcək onlayn bank çıxarışı üçün"
                >
                  🏧 Bank Kartına Çıxar (Beta)
                </button>
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
                        <td className={`py-4 px-4 font-black ${t.amount < 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                          {t.amount < 0 ? `${t.seller_profit} AZN` : `+${t.seller_profit} AZN`}
                        </td>
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

          {/* Payout History Sub-Table */}
          <div className="bg-slate-900/60 rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
            <div className="p-5 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <span>🏧</span> <span>Çıxarış Tələblərim (Payout Requests)</span>
                </h3>
                <p className="text-xs text-slate-400">Bank kartınıza göndərilən balans çıxarışlarının cari statusu.</p>
              </div>
            </div>

            {payouts.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-xs">Hələ heç bir çıxarış tələbi göndərilməyib.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-950/40 text-slate-400 text-xs uppercase font-semibold">
                      <th className="py-3 px-4">Məbləğ</th>
                      <th className="py-3 px-4">Bank Kartı</th>
                      <th className="py-3 px-4">Kart Sahibi</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Admin Qeydi</th>
                      <th className="py-3 px-4">Tarix</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300 text-xs">
                    {payouts.map((p) => (
                      <tr key={p.id} className="hover:bg-slate-800/30 transition">
                        <td className="py-3.5 px-4 font-black text-white text-sm">{p.amount.toLocaleString()} AZN</td>
                        <td className="py-3.5 px-4 font-mono text-cyan-400 font-semibold">{p.card_number}</td>
                        <td className="py-3.5 px-4">{p.card_holder_name}</td>
                        <td className="py-3.5 px-4">
                          {p.status === 'paid' && (
                            <span className="px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
                              🟢 Ödənildi
                            </span>
                          )}
                          {p.status === 'pending' && (
                            <span className="px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 font-semibold">
                              🟡 Gözləmədə
                            </span>
                          )}
                          {p.status === 'rejected' && (
                            <span className="px-2.5 py-1 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 font-semibold">
                              🔴 İmtina edildi
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-slate-400">{p.admin_notes || '-'}</td>
                        <td className="py-3.5 px-4 text-slate-500">{new Date(p.created_at).toLocaleString('az-AZ')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 4: CUSTOM DOMAIN & BRANDING */}
      {activeTab === 'domain' && (
        <div className="space-y-6">
          {/* Domain Status Banner */}
          <div className="bg-slate-900/60 rounded-3xl border border-slate-800 p-6 backdrop-blur-md shadow-xl">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <div className="p-2.5 bg-cyan-500/10 rounded-xl text-cyan-400 border border-cyan-500/20">
                    <Globe className="w-6 h-6" />
                  </div>
                  <h2 className="text-xl font-bold text-white tracking-tight">Fərdi Domen və White-label Brend Tənzimləmələri</h2>
                </div>
                <p className="text-xs text-slate-400 max-w-2xl">
                  Agentləriniz üçün öz brendinizlə xüsusi giriş və qeydiyyat domeni təyin edin.
                </p>
              </div>

              <div>
                {dashboard?.rank_custom_domain_allowed ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    <CheckCircle className="w-4 h-4" />
                    <span>Domen Funksiyası Aktivdir</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                    <Lock className="w-4 h-4" />
                    <span>Gold+ və ya Admin İcazəsi Lazımdır</span>
                  </span>
                )}
              </div>
            </div>

            {!dashboard?.rank_custom_domain_allowed ? (
              <div className="pt-6 text-center py-10 space-y-4 max-w-lg mx-auto">
                <div className="w-16 h-16 bg-amber-500/10 rounded-2xl border border-amber-500/20 flex items-center justify-center mx-auto text-amber-400">
                  <Lock className="w-8 h-8" />
                </div>
                <h3 className="text-lg font-bold text-white">Fərdi Domen Səviyyənizə görə Kilidlidir</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Fərdi domen və brendinizi aktivləşdirmək üçün satış həcminizi <strong>2,000 AZN (Gold Dərəcəsi)</strong> səviyyəsinə çatdırın və ya platforma administratoru ilə əlaqə saxlayın.
                </p>
                <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800 text-xs text-slate-300">
                  Hazırki dövriyyəniz: <span className="text-white font-bold">{dashboard?.total_sales_volume || 0} AZN</span> / Hədəf: 2,000 AZN
                </div>
              </div>
            ) : (
              <div className="pt-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Form column */}
                <div className="lg:col-span-7 space-y-5">
                  <form onSubmit={handleSaveDomain} className="space-y-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                        Fərdi Domen Adınız *
                      </label>
                      <div className="relative">
                        <input
                          type="text"
                          required
                          value={domainHost}
                          onChange={(e) => setDomainHost(e.target.value)}
                          placeholder="agent.bakuemlak.az və ya emlak.brendiniz.com"
                          className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-3.5 pr-10 py-2.5 text-white text-sm font-mono focus:outline-none focus:border-cyan-500"
                        />
                        <Globe className="w-4 h-4 text-slate-500 absolute right-3.5 top-3" />
                      </div>
                      <span className="text-[11px] text-slate-500 mt-1 block">
                        https:// yazmadan yalnız subdomain və ya domeninizi daxil edin.
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                          Fərdi Brend Başlığı
                        </label>
                        <input
                          type="text"
                          value={brandTitle}
                          onChange={(e) => setBrandTitle(e.target.value)}
                          placeholder="Məs: Baku Emlak Portalı"
                          className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-cyan-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                          Fərdi Loqo URL
                        </label>
                        <input
                          type="text"
                          value={brandLogo}
                          onChange={(e) => setBrandLogo(e.target.value)}
                          placeholder="https://yourbrand.az/logo.png"
                          className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-cyan-500"
                        />
                      </div>
                    </div>

                    <div className="flex gap-3 pt-2">
                      <button
                        type="submit"
                        disabled={savingDomain}
                        className="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-cyan-500/20 transition disabled:opacity-50"
                      >
                        {savingDomain ? 'Saxlanılır...' : 'Domeni Yadda Saxla'}
                      </button>
                    </div>
                  </form>
                </div>

                {/* DNS Instructions Column */}
                <div className="lg:col-span-5 space-y-4 bg-slate-950/60 p-5 rounded-2xl border border-slate-800/80">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-cyan-400" />
                      <span>DNS Qoşulma Təlimatı (Real Məlumatlar)</span>
                    </h3>
                    <span className="text-[10px] text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded-full border border-cyan-500/20 font-bold">
                      Canlı Server
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Domen provayderinizin (məs: Cloudflare, GoDaddy, Namecheap, cPanel) DNS idarəetmə panelinə daxil olaraq aşağıdakı qeydlərdən birini əlavə edin:
                  </p>

                  {/* Option 1: CNAME (Recommended for subdomains) */}
                  <div className="space-y-2 bg-slate-900/90 p-3.5 rounded-xl border border-slate-800 text-xs font-mono">
                    <div className="flex items-center justify-between border-b border-slate-800/80 pb-1.5 font-sans">
                      <span className="text-xs font-bold text-cyan-400">1. Subdomen üçün (Tövsiyə olunur)</span>
                      <span className="text-[10px] text-slate-400 font-mono">Məs: emlak.brendiniz.az</span>
                    </div>

                    <div className="flex justify-between items-center py-1">
                      <span className="text-slate-500">Record Type:</span>
                      <span className="text-cyan-400 font-bold">CNAME</span>
                    </div>

                    <div className="flex justify-between items-center py-1">
                      <span className="text-slate-500">Host / Ad:</span>
                      <div className="flex items-center gap-1.5">
                        <span className="text-white font-bold">{domainHost.split('.')[0] || 'subdomain'}</span>
                        <button
                          type="button"
                          onClick={() => handleCopy(domainHost.split('.')[0] || 'subdomain', 'cname_host')}
                          className="p-1 text-slate-400 hover:text-white bg-slate-800 rounded transition"
                          title="Kopyala"
                        >
                          <Copy className="w-3 h-3" />
                        </button>
                        {copiedKey === 'cname_host' && <span className="text-[10px] text-emerald-400">Kopyalandı!</span>}
                      </div>
                    </div>

                    <div className="flex justify-between items-center py-1">
                      <span className="text-slate-500">Hədəf (Target):</span>
                      <div className="flex items-center gap-1.5">
                        <span className="text-emerald-400 font-bold">{domainSettings?.dns_instructions?.target || 'realtor.erma.shop'}</span>
                        <button
                          type="button"
                          onClick={() => handleCopy(domainSettings?.dns_instructions?.target || 'realtor.erma.shop', 'cname_target')}
                          className="p-1 text-slate-400 hover:text-white bg-slate-800 rounded transition"
                          title="Kopyala"
                        >
                          <Copy className="w-3 h-3" />
                        </button>
                        {copiedKey === 'cname_target' && <span className="text-[10px] text-emerald-400">Kopyalandı!</span>}
                      </div>
                    </div>

                    <div className="flex justify-between items-center py-0.5">
                      <span className="text-slate-500">TTL:</span>
                      <span className="text-slate-400">300 və ya Auto</span>
                    </div>
                  </div>

                  {/* Option 2: A Record (For Apex / Root Domain) */}
                  <div className="space-y-2 bg-slate-900/90 p-3.5 rounded-xl border border-slate-800 text-xs font-mono">
                    <div className="flex items-center justify-between border-b border-slate-800/80 pb-1.5 font-sans">
                      <span className="text-xs font-bold text-indigo-400">2. Əsas Kök Domen üçün (Apex Domain)</span>
                      <span className="text-[10px] text-slate-400 font-mono">Məs: brendiniz.az</span>
                    </div>

                    <div className="flex justify-between items-center py-1">
                      <span className="text-slate-500">Record Type:</span>
                      <span className="text-indigo-400 font-bold">A</span>
                    </div>

                    <div className="flex justify-between items-center py-1">
                      <span className="text-slate-500">Host / Ad:</span>
                      <div className="flex items-center gap-1.5">
                        <span className="text-white font-bold">@</span>
                        <button
                          type="button"
                          onClick={() => handleCopy('@', 'a_host')}
                          className="p-1 text-slate-400 hover:text-white bg-slate-800 rounded transition"
                          title="Kopyala"
                        >
                          <Copy className="w-3 h-3" />
                        </button>
                        {copiedKey === 'a_host' && <span className="text-[10px] text-emerald-400">Kopyalandı!</span>}
                      </div>
                    </div>

                    <div className="flex justify-between items-center py-1">
                      <span className="text-slate-500">IP Ünvanı (Server IP):</span>
                      <div className="flex items-center gap-1.5">
                        <span className="text-emerald-400 font-bold">{domainSettings?.dns_instructions?.server_ip || '185.196.21.159'}</span>
                        <button
                          type="button"
                          onClick={() => handleCopy(domainSettings?.dns_instructions?.server_ip || '185.196.21.159', 'a_ip')}
                          className="p-1 text-slate-400 hover:text-white bg-slate-800 rounded transition"
                          title="Kopyala"
                        >
                          <Copy className="w-3 h-3" />
                        </button>
                        {copiedKey === 'a_ip' && <span className="text-[10px] text-emerald-400">Kopyalandı!</span>}
                      </div>
                    </div>
                  </div>

                  <div className="pt-2">
                    <button
                      type="button"
                      onClick={handleVerifyDns}
                      disabled={verifyingDns || !domainHost}
                      className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-cyan-500/30 rounded-xl text-xs font-bold transition flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                      <RefreshCw className={`w-4 h-4 ${verifyingDns ? 'animate-spin' : ''}`} />
                      <span>{verifyingDns ? 'DNS Yoxlanılır...' : 'DNS Yoxla və Təsdiqlə'}</span>
                    </button>
                  </div>

                  {dnsResult && (
                    <div className={`p-3 rounded-xl text-xs flex items-start gap-2 ${
                      dnsResult.success
                        ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400'
                        : 'bg-amber-500/10 border border-amber-500/30 text-amber-400'
                    }`}>
                      {dnsResult.success ? <CheckCircle className="w-4 h-4 shrink-0 mt-0.5" /> : <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />}
                      <span>{dnsResult.message}</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 5: SECURITY & 2FA (TWO-FACTOR AUTHENTICATOR) */}
      {activeTab === 'security' && (
        <div className="space-y-6">
          {/* Status Alerts */}
          {totpError && (
            <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between gap-3 shadow-lg">
              <div className="flex items-center gap-2.5">
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{totpError}</span>
              </div>
              <button onClick={() => setTotpError(null)} className="text-rose-400 hover:text-white p-1">
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {totpSuccess && (
            <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center justify-between gap-3 shadow-lg">
              <div className="flex items-center gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{totpSuccess}</span>
              </div>
              <button onClick={() => setTotpSuccess(null)} className="text-emerald-400 hover:text-white p-1">
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* 2FA Main Status & Configuration Card */}
          <div className="bg-slate-900/80 p-6 rounded-3xl border border-slate-800 shadow-2xl space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
              <div className="flex items-center gap-3.5">
                <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shadow-inner">
                  <Smartphone className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    İki Mərhələli Doğrulama (2FA Authenticator)
                    {totpStatus?.enabled ? (
                      <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 font-semibold flex items-center gap-1">
                        <CheckCircle className="w-3 h-3" /> Aktivdir
                      </span>
                    ) : (
                      <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30 font-semibold flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3" /> Deaktivdir
                      </span>
                    )}
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Google Authenticator, Apple Passwords və ya 1Password ilə satıcı hesabınızı 100% qoruyun.
                  </p>
                </div>
              </div>

              <div>
                {totpStatus?.enabled ? (
                  <button
                    type="button"
                    onClick={() => setShowDisableModal(true)}
                    className="px-4 py-2.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded-xl text-xs font-bold transition flex items-center gap-2"
                  >
                    <Lock className="w-3.5 h-3.5" />
                    <span>2FA Deaktiv Et</span>
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={handleStartTotpSetup}
                    disabled={totpLoading}
                    className="px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white rounded-xl text-xs font-bold transition flex items-center gap-2 shadow-lg shadow-emerald-500/20 disabled:opacity-50"
                  >
                    <ShieldCheck className="w-4 h-4" />
                    <span>{totpLoading ? 'Yüklənir...' : '2FA Quraşdır və Aktivləşdir'}</span>
                  </button>
                )}
              </div>
            </div>

            {/* 2FA Setup Flow with QR Code & Secret */}
            {showTotpSetup && !totpStatus?.enabled && (
              <div className="bg-slate-950/70 p-6 rounded-2xl border border-emerald-500/30 space-y-6 animate-in fade-in zoom-in duration-200">
                <div className="border-b border-slate-800 pb-4 flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-bold text-emerald-400 flex items-center gap-2">
                      <QrCode className="w-4 h-4" />
                      Addım 1: QR Kodu Skan Edin
                    </h4>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Telefonunuzun kamerası və ya Google Authenticator tətbiqi ilə aşağıdakı QR kodu oxudun.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowTotpSetup(false)}
                    className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
                  {/* QR Code Container */}
                  <div className="flex flex-col items-center justify-center p-5 bg-white rounded-2xl border border-slate-700 shadow-xl self-center max-w-[220px] mx-auto">
                    {otpauthUrl && <QRCodeSVG value={otpauthUrl} size={180} />}
                    <span className="text-[10px] text-slate-700 font-mono font-bold mt-2">RealEstate AI Authenticator</span>
                  </div>

                  {/* Secret Key & 6-digit Code Input Form */}
                  <div className="space-y-4 text-xs">
                    <div>
                      <label className="text-slate-400 block mb-1 font-semibold">Və ya Gizli Açarı Manual Daxil Edin:</label>
                      <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 px-3 py-2 rounded-xl">
                        <span className="font-mono text-emerald-400 text-xs font-bold tracking-wider select-all truncate flex-1">
                          {totpSecret}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleCopy(totpSecret, 'totp_secret')}
                          className="p-1.5 text-slate-400 hover:text-white bg-slate-800 rounded-lg transition"
                          title="Açarı Kopyala"
                        >
                          <Copy className="w-3.5 h-3.5" />
                        </button>
                      </div>
                      {copiedKey === 'totp_secret' && (
                        <span className="text-[10px] text-emerald-400 font-semibold mt-1 block">Açar kopyalandı!</span>
                      )}
                    </div>

                    <form onSubmit={handleEnableTotp} className="space-y-3 pt-2">
                      <div>
                        <label className="text-slate-300 font-semibold block mb-1">
                          Addım 2: Tətbiqdəki 6 Rəqəmli Kodu Daxil Edin:
                        </label>
                        <input
                          type="text"
                          required
                          maxLength={6}
                          placeholder="Məs: 123456"
                          value={totpCode}
                          onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                          className="w-full bg-slate-900 border border-emerald-500/50 px-4 py-3 rounded-xl text-center text-lg font-mono tracking-widest text-emerald-400 font-bold placeholder-slate-600 focus:outline-none focus:border-emerald-400 shadow-inner"
                        />
                      </div>

                      <button
                        type="submit"
                        disabled={totpLoading || totpCode.length < 6}
                        className="w-full py-3 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white rounded-xl font-bold transition shadow-lg shadow-emerald-500/20 disabled:opacity-50"
                      >
                        {totpLoading ? 'Təsdiqlənir...' : 'Təsdiqlə və 2FA-nı Aktivləşdir'}
                      </button>
                    </form>
                  </div>
                </div>
              </div>
            )}

            {/* Backup Codes Display */}
            {backupCodes.length > 0 && (
              <div className="bg-slate-950/80 p-5 rounded-2xl border border-amber-500/30 space-y-3">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <div className="flex items-center gap-2">
                    <Key className="w-4 h-4 text-amber-400" />
                    <h5 className="text-xs font-bold text-amber-300">Ehtiyat Bərpa Kodları (Birdəfəlik)</h5>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleCopy(backupCodes.join('\n'), 'backup_codes')}
                    className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white bg-slate-800 px-3 py-1.5 rounded-lg transition"
                  >
                    <Copy className="w-3.5 h-3.5" />
                    <span>{copiedKey === 'backup_codes' ? 'Kopyalandı!' : 'Hamısını Kopyala'}</span>
                  </button>
                </div>
                <p className="text-[11px] text-slate-400">
                  Telefonunuzu itirdikdə və ya Authenticator tətbiqinə giriş olmadıqda hesabınıza daxil olmaq üçün bu kodları təhlükəsiz yerdə qeyd edin:
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-xs text-amber-400 bg-slate-900 p-3 rounded-xl border border-slate-800 text-center font-bold">
                  {backupCodes.map((code, idx) => (
                    <span key={idx} className="p-1 bg-slate-950 rounded select-all">{code}</span>
                  ))}
                </div>
              </div>
            )}

            {/* 2FA Informational Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
              <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800/80 space-y-2">
                <div className="w-8 h-8 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                  <span>📱</span>
                </div>
                <h5 className="text-xs font-bold text-white">Google Authenticator</h5>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Android və iOS üçün rəsmi pulsuz Google Authenticator ilə kodları hər 30 saniyədən bir sinxronlaşdırın.
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800/80 space-y-2">
                <div className="w-8 h-8 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                  <span>🍎</span>
                </div>
                <h5 className="text-xs font-bold text-white">Apple Passwords / iCloud</h5>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  iPhone və Mac cihazlarında daxili Şifrələr bölməsində 2FA QR kodunu birbaşa skan edərək avtomatik doldurmadan istifadə edin.
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800/80 space-y-2">
                <div className="w-8 h-8 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                  <span>🛡️</span>
                </div>
                <h5 className="text-xs font-bold text-white">100% Hesab Qoruması</h5>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Şifrəniz ifşa olsa belə, 2FA aktiv olduqda heç kim hesabınıza və balansınıza icazəsiz daxil ola bilməz.
                </p>
              </div>
            </div>
          </div>

          {/* Password Change Card */}
          <form onSubmit={handleUpdatePassword} className="bg-slate-900/80 p-6 rounded-3xl border border-slate-800 shadow-xl space-y-5">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <KeyRound className="w-5 h-5 text-indigo-400" />
                Satıcı Hesab Şifrəsini Yenilə
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Dashboard giriş təhlükəsizliyi üçün mütəmadi olaraq şifrənizi gücləndirin.
              </p>
            </div>

            {passwordError && (
              <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
                <span>{passwordError}</span>
              </div>
            )}

            {passwordSuccess && (
              <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
                <CheckCircle className="w-4 h-4 shrink-0 text-emerald-400" />
                <span>{passwordSuccess}</span>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div>
                <label className="text-slate-300 font-semibold block mb-1">Cari Şifrəniz</label>
                <div className="relative">
                  <Lock className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-500" />
                  <input
                    type="password"
                    required
                    placeholder="Hazırkı şifrə"
                    value={currPassword}
                    onChange={(e) => setCurrPassword(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 pl-9 pr-3.5 py-2.5 rounded-xl text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-300 font-semibold block mb-1">Yeni Güclü Şifrə</label>
                <div className="relative">
                  <Lock className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-500" />
                  <input
                    type="password"
                    required
                    placeholder="Məs: SafePass2026!"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 pl-9 pr-3.5 py-2.5 rounded-xl text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800 flex justify-end">
              <button
                type="submit"
                disabled={savingPassword || !currPassword || !newPassword}
                className="px-5 py-2.5 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-400 hover:to-purple-500 text-white rounded-xl text-xs font-bold transition shadow-lg shadow-indigo-500/20 disabled:opacity-50"
              >
                {savingPassword ? 'Yenilənir...' : 'Şifrəni Yenilə'}
              </button>
            </div>
          </form>

          {/* Disable 2FA Password Modal */}
          {showDisableModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
              <div className="bg-slate-900 border border-slate-800 w-full max-w-md rounded-2xl p-6 shadow-2xl space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h4 className="text-sm font-bold text-white flex items-center gap-2">
                    <Lock className="w-4 h-4 text-rose-400" />
                    2FA-nı Deaktiv Etmək
                  </h4>
                  <button onClick={() => setShowDisableModal(false)} className="text-slate-400 hover:text-white p-1">
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <p className="text-xs text-slate-400 leading-relaxed">
                  2FA-nı söndürmək üçün cari hesab şifrənizi daxil edərək təsdiqləyin:
                </p>

                <form onSubmit={handleDisableTotp} className="space-y-3 text-xs">
                  <div>
                    <label className="text-slate-300 font-semibold block mb-1">Cari Hesab Şifrəsi</label>
                    <input
                      type="password"
                      required
                      placeholder="Şifrəniz"
                      value={totpPassword}
                      onChange={(e) => setTotpPassword(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 px-3.5 py-2.5 rounded-xl text-white focus:outline-none focus:border-rose-500"
                    />
                  </div>

                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowDisableModal(false)}
                      className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-semibold"
                    >
                      Ləğv et
                    </button>
                    <button
                      type="submit"
                      disabled={totpLoading || !totpPassword}
                      className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-xl font-bold transition disabled:opacity-50"
                    >
                      {totpLoading ? 'Deaktiv edilir...' : '2FA-nı Söndür'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}

      {/* AGENT DETAIL & MANAGEMENT MODAL (OVERVIEW, QR CONNECT, RENEW, EDIT) */}
      {isAgentDetailOpen && selectedAgent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 w-full max-w-2xl rounded-3xl p-6 shadow-2xl space-y-5 max-h-[92vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-2xl bg-blue-600/10 border border-blue-500/30 flex items-center justify-center text-blue-400 font-bold text-lg">
                  {selectedAgent.name.charAt(0).toUpperCase()}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-bold text-white">{selectedAgent.name}</h3>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                      selectedAgent.is_expired
                        ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                        : selectedAgent.status === 'active'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    }`}>
                      {selectedAgent.is_expired ? 'Müddət Bitib' : selectedAgent.status === 'active' ? 'Aktiv' : selectedAgent.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 font-mono">
                    {selectedAgent.phone} {selectedAgent.telegram_handle && `• @${selectedAgent.telegram_handle}`}
                  </p>
                </div>
              </div>
              <button onClick={() => setIsAgentDetailOpen(false)} className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Navigation Tabs */}
            <div className="flex bg-slate-950/70 p-1.5 rounded-2xl border border-slate-800 gap-1 text-xs font-bold">
              <button
                type="button"
                onClick={() => setAgentModalTab('overview')}
                className={`flex-1 py-2 rounded-xl transition flex items-center justify-center gap-1.5 ${
                  agentModalTab === 'overview' ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20' : 'text-slate-400 hover:text-white'
                }`}
              >
                <Info className="w-3.5 h-3.5" />
                <span>Ümumi Baxış</span>
              </button>
              <button
                type="button"
                onClick={() => setAgentModalTab('qr')}
                className={`flex-1 py-2 rounded-xl transition flex items-center justify-center gap-1.5 ${
                  agentModalTab === 'qr' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20' : 'text-slate-400 hover:text-white'
                }`}
              >
                <QrCode className="w-3.5 h-3.5" />
                <span>QR Kod & Qoşulma</span>
              </button>
              <button
                type="button"
                onClick={() => setAgentModalTab('renew')}
                className={`flex-1 py-2 rounded-xl transition flex items-center justify-center gap-1.5 ${
                  agentModalTab === 'renew' ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-500/20' : 'text-slate-400 hover:text-white'
                }`}
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Abunəni Yenilə</span>
              </button>
              <button
                type="button"
                onClick={() => setAgentModalTab('edit')}
                className={`flex-1 py-2 rounded-xl transition flex items-center justify-center gap-1.5 ${
                  agentModalTab === 'edit' ? 'bg-amber-600 text-white shadow-lg shadow-amber-500/20' : 'text-slate-400 hover:text-white'
                }`}
              >
                <Edit3 className="w-3.5 h-3.5" />
                <span>Redaktə Et</span>
              </button>
            </div>

            {/* TAB 1: OVERVIEW */}
            {agentModalTab === 'overview' && (
              <div className="space-y-4">
                {/* Stats cards */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-2xl">
                    <span className="text-[10px] text-slate-500 block">Cari Paket</span>
                    <span className="text-sm font-bold text-emerald-400 block mt-0.5">{selectedAgent.plan}</span>
                  </div>
                  <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-2xl">
                    <span className="text-[10px] text-slate-500 block">Aktiv Axtarışlar</span>
                    <span className="text-sm font-bold text-cyan-400 block mt-0.5">{selectedAgent.saved_searches_count ?? 0}</span>
                  </div>
                  <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-2xl">
                    <span className="text-[10px] text-slate-500 block">Tapılan Uyğun Elanlar</span>
                    <span className="text-sm font-bold text-purple-400 block mt-0.5">{selectedAgent.matches_count ?? 0}</span>
                  </div>
                </div>

                {/* Details Grid */}
                <div className="bg-slate-950/40 border border-slate-800 rounded-2xl p-4 space-y-2.5 text-xs">
                  <div className="flex justify-between py-1 border-b border-slate-800/60">
                    <span className="text-slate-400">Agent ID:</span>
                    <span className="font-mono text-white font-bold">#{selectedAgent.id}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800/60">
                    <span className="text-slate-400">Telefon:</span>
                    <span className="font-mono text-white">{selectedAgent.phone}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800/60">
                    <span className="text-slate-400">Telegram / WhatsApp:</span>
                    <span className="text-white">
                      {selectedAgent.telegram_handle ? `@${selectedAgent.telegram_handle}` : (selectedAgent.whatsapp_number || '—')}
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800/60">
                    <span className="text-slate-400">Əsas Bildiriş Kanalı:</span>
                    <span className="capitalize font-bold text-blue-400">{selectedAgent.preferred_channel}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800/60">
                    <span className="text-slate-400">Qeydiyyat Tarixi:</span>
                    <span className="text-slate-300">
                      {new Date(selectedAgent.created_at).toLocaleDateString('az-AZ')}
                    </span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-slate-400">Abunə Bitmə Tarixi:</span>
                    <span className={selectedAgent.is_expired ? 'text-rose-400 font-bold' : 'text-emerald-400 font-bold'}>
                      {selectedAgent.plan_expires_at ? new Date(selectedAgent.plan_expires_at).toLocaleDateString('az-AZ') : 'Limitsiz'}
                      {selectedAgent.is_expired && ' (Müddəti bitib)'}
                    </span>
                  </div>
                </div>

                {/* Enabled Features List */}
                <div className="p-4 bg-slate-950/40 border border-slate-800 rounded-2xl space-y-2">
                  <span className="text-xs font-bold text-slate-300 block uppercase tracking-wider">Aktiv İmkanlar & Funksiyalar</span>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="flex items-center gap-2 text-slate-300">
                      <span className={selectedAgent.feature_makler_detector ? 'text-emerald-400 font-bold' : 'text-slate-600'}>
                        {selectedAgent.feature_makler_detector ? '✓' : '✗'}
                      </span>
                      <span>Makler Detektoru</span>
                    </div>
                    <div className="flex items-center gap-2 text-slate-300">
                      <span className={selectedAgent.feature_avm_bargain_finder ? 'text-emerald-400 font-bold' : 'text-slate-600'}>
                        {selectedAgent.feature_avm_bargain_finder ? '✓' : '✗'}
                      </span>
                      <span>AVM Bazar Qiyməti</span>
                    </div>
                    <div className="flex items-center gap-2 text-slate-300">
                      <span className={selectedAgent.feature_social_brochure ? 'text-emerald-400 font-bold' : 'text-slate-600'}>
                        {selectedAgent.feature_social_brochure ? '✓' : '✗'}
                      </span>
                      <span>Sosial Bukletlər</span>
                    </div>
                    <div className="flex items-center gap-2 text-slate-300">
                      <span className={selectedAgent.feature_multi_location ? 'text-emerald-400 font-bold' : 'text-slate-600'}>
                        {selectedAgent.feature_multi_location ? '✓' : '✗'}
                      </span>
                      <span>Çoxsaylı Məkan ({selectedAgent.max_locations_per_search || 5})</span>
                    </div>
                    <div className="flex items-center gap-2 text-slate-300">
                      <span className={selectedAgent.feature_client_intake_bot ? 'text-emerald-400 font-bold' : 'text-slate-600'}>
                        {selectedAgent.feature_client_intake_bot ? '✓' : '✗'}
                      </span>
                      <span>Müştəri Qəbul Botu</span>
                    </div>
                    <div className="flex items-center gap-2 text-slate-300">
                      <span className={selectedAgent.backup_enabled ? 'text-emerald-400 font-bold' : 'text-slate-600'}>
                        {selectedAgent.backup_enabled ? '✓' : '✗'}
                      </span>
                      <span>BaaS Data Backup</span>
                    </div>
                    {selectedAgent.feature_aged_listings && (
                      <div className="flex items-center gap-2 text-amber-400 col-span-2 font-medium">
                        <span>✓</span>
                        <span>Köhnə Arxiv Elanlar ({selectedAgent.addon_aged_max_months || 12} ay)</span>
                      </div>
                    )}
                    {selectedAgent.feature_watermark_free_images && (
                      <div className="flex items-center gap-2 text-teal-400 col-span-2 font-medium">
                        <span>✓</span>
                        <span>Su Nişansız Şəkillər ({selectedAgent.addon_image_requests_used || 0} / {selectedAgent.addon_image_requests_limit || 0} foto istifadə edilib)</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex gap-2.5 pt-1">
                  <button
                    type="button"
                    onClick={() => setAgentModalTab('qr')}
                    className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition flex items-center justify-center gap-2 shadow-lg shadow-indigo-500/20"
                  >
                    <QrCode className="w-4 h-4" />
                    <span>QR Kodu Göstər</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setAgentModalTab('renew')}
                    className="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold transition flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20"
                  >
                    <RefreshCw className="w-4 h-4" />
                    <span>Abunəni Yenilə</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setAgentModalTab('edit')}
                    className="py-2.5 px-4 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5"
                  >
                    <Edit3 className="w-4 h-4" />
                    <span>Redaktə</span>
                  </button>
                </div>
              </div>
            )}

            {/* TAB 2: QR & CONNECT */}
            {agentModalTab === 'qr' && (
              <div className="space-y-5 text-center">
                <div className="p-5 bg-slate-950/60 border border-slate-800 rounded-3xl space-y-4 max-w-sm mx-auto">
                  <div className="bg-white p-4 rounded-2xl inline-block shadow-2xl">
                    <QRCodeSVG
                      value={selectedAgent.invite_url || `https://t.me/${selectedAgent.telegram_bot_username || 'baku_realestate_ai_bot'}?start=agent_${selectedAgent.id}`}
                      size={200}
                      level="H"
                      includeMargin={false}
                    />
                  </div>
                  <div>
                    <h4 className="font-bold text-white text-sm">Agent Bot Qoşulma QR Kodu</h4>
                    <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                      Agent bu QR kodu telefon kamerası və ya Telegram ilə skan edərək anında bot-a qoşula və bildirişləri ala bilər.
                    </p>
                  </div>
                </div>

                {/* Direct Link & Copy */}
                <div className="space-y-2 max-w-md mx-auto text-left">
                  <label className="text-[11px] font-semibold text-slate-400 block">Birbaşa Dəvət Linki</label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      readOnly
                      value={selectedAgent.invite_url || `https://t.me/${selectedAgent.telegram_bot_username || 'baku_realestate_ai_bot'}?start=agent_${selectedAgent.id}`}
                      className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-cyan-300 focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={() => handleCopy(selectedAgent.invite_url || `https://t.me/${selectedAgent.telegram_bot_username || 'baku_realestate_ai_bot'}?start=agent_${selectedAgent.id}`, 'agent_invite')}
                      className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition"
                    >
                      <Copy className="w-3.5 h-3.5" />
                      <span>{copiedKey === 'agent_invite' ? 'Kopyalandı!' : 'Kopyala'}</span>
                    </button>
                  </div>

                  <a
                    href={selectedAgent.invite_url || `https://t.me/${selectedAgent.telegram_bot_username || 'baku_realestate_ai_bot'}?start=agent_${selectedAgent.id}`}
                    target="_blank"
                    rel="noreferrer"
                    className="w-full py-2.5 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/30 rounded-xl text-xs font-bold transition flex items-center justify-center gap-2 mt-3"
                  >
                    <ExternalLink className="w-4 h-4" />
                    <span>Bot-u Brauzerdə Aç ↗</span>
                  </a>
                </div>
              </div>
            )}

            {/* TAB 3: RENEW SUBSCRIPTION */}
            {agentModalTab === 'renew' && (
              <form onSubmit={handleRenewAgent} className="space-y-4">
                {renewSuccessMsg && (
                  <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-xs text-emerald-400 flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 shrink-0" />
                    <span>{renewSuccessMsg}</span>
                  </div>
                )}
                {renewError && (
                  <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-400 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    <span>{renewError}</span>
                  </div>
                )}

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Yenilənəcək Paket *</label>
                  <select
                    value={renewPkgId}
                    onChange={(e) => setRenewPkgId(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white text-sm focus:outline-none focus:border-emerald-500"
                  >
                    <option value={0}>
                      ✨ Cari Planı Qoru: {selectedAgent.plan} ({(selectedAgent.plan_price ?? 50).toFixed(2)} AZN / 30 Gün) — Bütün funksiyalar saxlanılır
                    </option>
                    {packages.map((p) => (
                      <option key={p.id} value={p.id}>
                        💳 {p.name} ({p.price} AZN / {p.duration_days || 30} Gün)
                      </option>
                    ))}
                  </select>
                </div>

                {/* Addon Tier Selectors for Renewal */}
                {(() => {
                  const isCustomPlan = renewPkgId === 0;
                  const currentPkg = isCustomPlan ? null : (packages.find(p => p.id === renewPkgId) || null);
                  const hasAgedTiers = currentPkg && currentPkg.addon_aged_tiers && currentPkg.addon_aged_tiers.length > 0;
                  const hasSearchTiers = currentPkg && currentPkg.addon_search_tiers && currentPkg.addon_search_tiers.length > 0;
                  const hasImageTiers = currentPkg && currentPkg.feature_watermark_free_images && currentPkg.addon_image_tiers && currentPkg.addon_image_tiers.length > 0;

                  const basePrice = isCustomPlan ? (selectedAgent.plan_price ?? 50.0) : (currentPkg?.price ?? 0);
                  const totalGross = basePrice + renewAgedPrice + renewExtraSearchesPrice + renewImagePrice;
                  const commRate = dashboard?.effective_commission_rate ?? dashboard?.commission_rate ?? 70;
                  const sellerProfit = (totalGross * commRate) / 100;

                  return (
                    <div className="space-y-3 pt-2 border-t border-slate-800">
                      {isCustomPlan && (
                        <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-xs text-indigo-300">
                          ℹ️ <strong>Mövcud/Köçürülmüş Plan qorunur:</strong> Agentin bütün aktiv imkanları və real ödəniş qiyməti ({basePrice.toFixed(2)} AZN) toxunulmaz saxlanılaraq abunəliyi 30 gün müddətinə yenilənir.
                        </div>
                      )}

                      {hasAgedTiers && (
                        <div>
                          <label className="block text-xs font-semibold text-amber-300 mb-1">📦 Arxiv Elanlar Müddəti</label>
                          <select
                            value={renewAgedMonths}
                            onChange={(e) => {
                              const val = Number(e.target.value);
                              if (val === 0) {
                                setRenewAgedMonths(0);
                                setRenewAgedPrice(0);
                              } else {
                                const tier = currentPkg?.addon_aged_tiers?.find(t => t.months === val);
                                setRenewAgedMonths(val);
                                setRenewAgedPrice(tier?.price ?? 0);
                              }
                            }}
                            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-xs focus:outline-none focus:border-amber-500"
                          >
                            <option value={0}>Yoxdur (Arxiv seçilməyib)</option>
                            {currentPkg?.addon_aged_tiers?.map((t, i) => (
                              <option key={i} value={t.months}>
                                {t.months} ay arxiv — +{t.price} AZN
                              </option>
                            ))}
                          </select>
                        </div>
                      )}

                      {hasSearchTiers && (
                        <div>
                          <label className="block text-xs font-semibold text-cyan-300 mb-1">⚡ Əlavə Axtarış Limiti</label>
                          <select
                            value={renewExtraSearches}
                            onChange={(e) => {
                              const val = Number(e.target.value);
                              if (val === 0) {
                                setRenewExtraSearches(0);
                                setRenewExtraSearchesPrice(0);
                              } else {
                                const tier = currentPkg?.addon_search_tiers?.find(t => t.searches === val);
                                setRenewExtraSearches(val);
                                setRenewExtraSearchesPrice(tier?.price ?? 0);
                              }
                            }}
                            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-xs focus:outline-none focus:border-cyan-500"
                          >
                            <option value={0}>Yoxdur (Əlavə axtarış seçilməyib)</option>
                            {currentPkg?.addon_search_tiers?.map((t, i) => (
                              <option key={i} value={t.searches}>
                                +{t.searches} axtarış — +{t.price} AZN
                              </option>
                            ))}
                          </select>
                        </div>
                      )}

                      {hasImageTiers && (
                        <div>
                          <label className="block text-xs font-semibold text-teal-300 mb-1">🖼️ Su Nişansız Foto Paketi</label>
                          <select
                            value={renewImageRequests}
                            onChange={(e) => {
                              const val = Number(e.target.value);
                              if (val === 0) {
                                setRenewImageRequests(0);
                                setRenewImagePrice(0);
                              } else {
                                const tier = currentPkg?.addon_image_tiers?.find(t => t.requests === val);
                                setRenewImageRequests(val);
                                setRenewImagePrice(tier?.price ?? 0);
                              }
                            }}
                            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-xs focus:outline-none focus:border-teal-500"
                          >
                            <option value={0}>Yoxdur (Əlavə foto paketi seçilməyib)</option>
                            {currentPkg?.addon_image_tiers?.map((t, i) => (
                              <option key={i} value={t.requests}>
                                +{t.requests} foto — +{t.price} AZN
                              </option>
                            ))}
                          </select>
                        </div>
                      )}

                      {/* Renewal Price Summary */}
                      <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl space-y-1.5">
                        <div className="flex justify-between text-xs text-slate-300">
                          <span>{isCustomPlan ? 'Cari Plan Qiyməti:' : 'Paket qiyməti:'}</span>
                          <span className="font-medium">{basePrice.toFixed(2)} AZN</span>
                        </div>
                        {renewAgedPrice > 0 && (
                          <div className="flex justify-between text-xs text-amber-300">
                            <span>Arxiv ({renewAgedMonths} ay):</span>
                            <span>+{renewAgedPrice.toFixed(2)} AZN</span>
                          </div>
                        )}
                        {renewExtraSearchesPrice > 0 && (
                          <div className="flex justify-between text-xs text-cyan-300">
                            <span>+{renewExtraSearches} axtarış:</span>
                            <span>+{renewExtraSearchesPrice.toFixed(2)} AZN</span>
                          </div>
                        )}
                        {renewImagePrice > 0 && (
                          <div className="flex justify-between text-xs text-teal-300">
                            <span>+{renewImageRequests} foto:</span>
                            <span>+{renewImagePrice.toFixed(2)} AZN</span>
                          </div>
                        )}
                        <div className="border-t border-emerald-500/30 pt-1.5 flex justify-between text-sm font-bold">
                          <span className="text-white">Ümumi Satış Məbləği:</span>
                          <span className="text-emerald-400">{totalGross.toFixed(2)} AZN</span>
                        </div>
                        <div className="flex justify-between text-xs">
                          <span className="text-slate-400">Sizin Qazancınız (%{commRate}):</span>
                          <span className="text-emerald-300 font-bold">+{sellerProfit.toFixed(2)} AZN</span>
                        </div>
                      </div>
                    </div>
                  );
                })()}

                <button
                  type="submit"
                  disabled={renewingAgent}
                  className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl shadow-lg shadow-emerald-500/25 transition disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  <RefreshCw className={`w-4 h-4 ${renewingAgent ? 'animate-spin' : ''}`} />
                  <span>{renewingAgent ? 'Yenilənir...' : 'Abunəni Təsdiqlə və Yenilə'}</span>
                </button>
              </form>
            )}

            {/* TAB 4: EDIT AGENT */}
            {agentModalTab === 'edit' && (
              <form onSubmit={handleSaveAgentEdit} className="space-y-4">
                {agentEditSuccessMsg && (
                  <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-xs text-emerald-400 flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 shrink-0" />
                    <span>{agentEditSuccessMsg}</span>
                  </div>
                )}
                {agentEditError && (
                  <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-400 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    <span>{agentEditError}</span>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Agentin Adı *</label>
                    <input
                      type="text"
                      required
                      value={editAgentName}
                      onChange={(e) => setEditAgentName(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-xs focus:outline-none focus:border-amber-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Telefon Nömrəsi *</label>
                    <input
                      type="text"
                      required
                      value={editAgentPhone}
                      onChange={(e) => setEditAgentPhone(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-xs focus:outline-none focus:border-amber-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Telegram İstifadəçi Adı</label>
                    <input
                      type="text"
                      value={editAgentTg}
                      onChange={(e) => setEditAgentTg(e.target.value)}
                      placeholder="@username"
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-xs focus:outline-none focus:border-amber-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">WhatsApp Nömrəsi</label>
                    <input
                      type="text"
                      value={editAgentWa}
                      onChange={(e) => setEditAgentWa(e.target.value)}
                      placeholder="+99450..."
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-xs focus:outline-none focus:border-amber-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Kanal & Status</label>
                    <div className="flex gap-1.5">
                      <select
                        value={editAgentChannel}
                        onChange={(e) => setEditAgentChannel(e.target.value)}
                        className="w-1/2 bg-slate-950 border border-slate-800 rounded-xl px-2 py-2 text-white text-xs"
                      >
                        <option value="telegram">TG</option>
                        <option value="whatsapp">WA</option>
                      </select>
                      <select
                        value={editAgentStatus}
                        onChange={(e) => setEditAgentStatus(e.target.value)}
                        className="w-1/2 bg-slate-950 border border-slate-800 rounded-xl px-2 py-2 text-white text-xs"
                      >
                        <option value="active">Aktiv</option>
                        <option value="suspended">Dayandır</option>
                        <option value="expired">Bitib</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* Feature Toggles */}
                <div className="pt-2 border-t border-slate-800 space-y-2">
                  <label className="text-xs font-bold text-white uppercase tracking-wider block">
                    İmkan və Funksiya İcazələri
                  </label>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <label className="flex items-center gap-2 p-2 bg-slate-950/60 border border-slate-800 rounded-xl cursor-pointer">
                      <input
                        type="checkbox"
                        checked={editAgentMakler}
                        onChange={(e) => setEditAgentMakler(e.target.checked)}
                        className="rounded bg-slate-900 border-slate-700 text-blue-600"
                      />
                      <span className="text-slate-200">Makler Detektoru</span>
                    </label>
                    <label className="flex items-center gap-2 p-2 bg-slate-950/60 border border-slate-800 rounded-xl cursor-pointer">
                      <input
                        type="checkbox"
                        checked={editAgentAvm}
                        onChange={(e) => setEditAgentAvm(e.target.checked)}
                        className="rounded bg-slate-900 border-slate-700 text-blue-600"
                      />
                      <span className="text-slate-200">AVM Bazar Qiyməti</span>
                    </label>
                    <label className="flex items-center gap-2 p-2 bg-slate-950/60 border border-slate-800 rounded-xl cursor-pointer">
                      <input
                        type="checkbox"
                        checked={editAgentBrochure}
                        onChange={(e) => setEditAgentBrochure(e.target.checked)}
                        className="rounded bg-slate-900 border-slate-700 text-blue-600"
                      />
                      <span className="text-slate-200">Sosial Bukletlər</span>
                    </label>
                    <label className="flex items-center gap-2 p-2 bg-slate-950/60 border border-slate-800 rounded-xl cursor-pointer">
                      <input
                        type="checkbox"
                        checked={editAgentMultiLoc}
                        onChange={(e) => setEditAgentMultiLoc(e.target.checked)}
                        className="rounded bg-slate-900 border-slate-700 text-blue-600"
                      />
                      <span className="text-slate-200">Çoxsaylı Məkan</span>
                    </label>
                    <label className="flex items-center gap-2 p-2 bg-slate-950/60 border border-slate-800 rounded-xl cursor-pointer">
                      <input
                        type="checkbox"
                        checked={editAgentBot}
                        onChange={(e) => setEditAgentBot(e.target.checked)}
                        className="rounded bg-slate-900 border-slate-700 text-indigo-600"
                      />
                      <span className="text-indigo-300 font-medium">Müştəri Qəbul Botu</span>
                    </label>
                    <label className="flex items-center gap-2 p-2 bg-slate-950/60 border border-slate-800 rounded-xl cursor-pointer">
                      <input
                        type="checkbox"
                        checked={editAgentBackup}
                        onChange={(e) => setEditAgentBackup(e.target.checked)}
                        className="rounded bg-slate-900 border-slate-700 text-purple-600"
                      />
                      <span className="text-purple-300 font-medium">BaaS Data Backup</span>
                    </label>
                  </div>

                  {/* Watermark-Free Photos Toggle & Limit in Edit Tab */}
                  <div className="p-2.5 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                    <label className="flex items-center justify-between cursor-pointer text-xs">
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={editAgentWatermarkImages}
                          onChange={(e) => setEditAgentWatermarkImages(e.target.checked)}
                          className="rounded bg-slate-900 border-slate-700 text-teal-500"
                        />
                        <span className="text-teal-300 font-semibold">🖼️ Su Nişansız Şəkillər Add-on</span>
                      </div>
                    </label>
                    {editAgentWatermarkImages && (
                      <div className="grid grid-cols-2 gap-2 pt-1 border-t border-slate-800 text-xs">
                        <div>
                          <label className="text-slate-400 text-[11px] block mb-0.5">Top-up Limit (Foto)</label>
                          <input
                            type="number"
                            min="0"
                            value={editAgentImageLimit}
                            onChange={(e) => setEditAgentImageLimit(Number(e.target.value))}
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-white text-xs font-bold"
                          />
                        </div>
                        <div>
                          <label className="text-slate-400 text-[11px] block mb-0.5">İstifadə Edilən</label>
                          <input
                            type="number"
                            min="0"
                            value={editAgentImageUsed}
                            onChange={(e) => setEditAgentImageUsed(Number(e.target.value))}
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-white text-xs font-bold"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="pt-2 flex gap-3">
                  <button
                    type="button"
                    onClick={() => setIsAgentDetailOpen(false)}
                    className="w-1/2 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium rounded-xl transition"
                  >
                    Bağla
                  </button>
                  <button
                    type="submit"
                    disabled={savingAgentEdit}
                    className="w-1/2 py-2.5 bg-amber-600 hover:bg-amber-500 text-white font-semibold rounded-xl shadow-lg shadow-amber-500/25 transition disabled:opacity-50"
                  >
                    {savingAgentEdit ? 'Yadda saxlanılır...' : 'Dəyişiklikləri Saxla'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

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
                <label className="block text-xs font-semibold text-slate-400 mb-1">Təyin Ediləcək Plan / Paket *</label>
                <select
                  value={agentPkgId !== undefined ? agentPkgId : (trialEnabled ? -1 : (packages[0]?.id || 0))}
                  onChange={(e) => setAgentPkgId(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                >
                  {trialEnabled && (
                    <option value={-1}>
                      🎁 Pulsuz Sınaq Təklifi ({trialDays} Günlük Aktivlik)
                    </option>
                  )}
                  {packages.map((p) => (
                    <option key={p.id} value={p.id}>
                      💳 {p.name} ({p.price} AZN / {p.period === 'monthly' ? 'aylıq' : p.period})
                    </option>
                  ))}
                </select>
                {agentPkgId === -1 && (
                  <span className="text-[11px] text-indigo-400 mt-1.5 block bg-indigo-500/10 p-2 rounded-lg border border-indigo-500/20">
                    Agent {trialDays} gün müddətində pulsuz sınaqdan ({trialSearches} axtarış, {trialLocations} məkan) yararlanacaq.
                  </span>
                )}
              </div>

              {/* Addon Tier Selectors — only for paid packages */}
              {agentPkgId !== undefined && agentPkgId !== -1 && (() => {
                const selectedPkg = packages.find(p => p.id === agentPkgId);
                if (!selectedPkg) return null;
                const hasAgedTiers = selectedPkg.addon_aged_tiers && selectedPkg.addon_aged_tiers.length > 0;
                const hasSearchTiers = selectedPkg.addon_search_tiers && selectedPkg.addon_search_tiers.length > 0;
                const hasImageTiers = selectedPkg.feature_watermark_free_images && selectedPkg.addon_image_tiers && selectedPkg.addon_image_tiers.length > 0;
                if (!hasAgedTiers && !hasSearchTiers && !hasImageTiers) return null;

                const basePrice = selectedPkg.price;
                const totalGross = basePrice + agentSelectedAgedPrice + agentSelectedExtraSearchesPrice + agentSelectedImagePrice;
                const commRate = dashboard?.effective_commission_rate ?? dashboard?.commission_rate ?? 70;
                const sellerProfit = (totalGross * commRate) / 100;

                return (
                  <div className="space-y-3 pt-2 border-t border-slate-800">
                    <label className="text-[11px] font-bold text-cyan-400 uppercase tracking-wider block">
                      Əlavə Xidmətlər (Addon Seçimi)
                    </label>

                    {/* Aged Listings Tier Selector */}
                    {hasAgedTiers && (
                      <div>
                        <label className="block text-xs font-semibold text-amber-300 mb-1">📦 Arxiv Elanlar Müddəti</label>
                        <select
                          value={agentSelectedAgedMonths}
                          onChange={(e) => {
                            const val = Number(e.target.value);
                            if (val === 0) {
                              setAgentSelectedAgedMonths(0);
                              setAgentSelectedAgedPrice(0);
                            } else {
                              const tier = selectedPkg.addon_aged_tiers.find(t => t.months === val);
                              setAgentSelectedAgedMonths(val);
                              setAgentSelectedAgedPrice(tier?.price ?? 0);
                            }
                          }}
                          className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-amber-500"
                        >
                          <option value={0}>Yoxdur (Arxiv seçilməyib)</option>
                          {selectedPkg.addon_aged_tiers.map((t, i) => (
                            <option key={i} value={t.months}>
                              {t.months} ay arxiv — +{t.price} AZN
                            </option>
                          ))}
                        </select>
                      </div>
                    )}

                    {/* Extra Search Tier Selector */}
                    {hasSearchTiers && (
                      <div>
                        <label className="block text-xs font-semibold text-cyan-300 mb-1">⚡ Əlavə Axtarış Limiti</label>
                        <select
                          value={agentSelectedExtraSearches}
                          onChange={(e) => {
                            const val = Number(e.target.value);
                            if (val === 0) {
                              setAgentSelectedExtraSearches(0);
                              setAgentSelectedExtraSearchesPrice(0);
                            } else {
                              const tier = selectedPkg.addon_search_tiers.find(t => t.searches === val);
                              setAgentSelectedExtraSearches(val);
                              setAgentSelectedExtraSearchesPrice(tier?.price ?? 0);
                            }
                          }}
                          className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-cyan-500"
                        >
                          <option value={0}>Yoxdur (Əlavə axtarış seçilməyib)</option>
                          {selectedPkg.addon_search_tiers.map((t, i) => (
                            <option key={i} value={t.searches}>
                              +{t.searches} axtarış — +{t.price} AZN
                            </option>
                          ))}
                        </select>
                      </div>
                    )}

                    {/* Watermark-Free Photos Tier Selector */}
                    {hasImageTiers && (
                      <div>
                        <label className="block text-xs font-semibold text-teal-300 mb-1">🖼️ Su Nişansız Foto Paketi</label>
                        <select
                          value={agentSelectedImageRequests}
                          onChange={(e) => {
                            const val = Number(e.target.value);
                            if (val === 0) {
                              setAgentSelectedImageRequests(0);
                              setAgentSelectedImagePrice(0);
                            } else {
                              const tier = selectedPkg.addon_image_tiers?.find(t => t.requests === val);
                              setAgentSelectedImageRequests(val);
                              setAgentSelectedImagePrice(tier?.price ?? 0);
                            }
                          }}
                          className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-teal-500"
                        >
                          <option value={0}>Yoxdur (Əlavə foto paketi seçilməyib)</option>
                          {selectedPkg.addon_image_tiers?.map((t, i) => (
                            <option key={i} value={t.requests}>
                              +{t.requests} foto sorğusu — +{t.price} AZN
                            </option>
                          ))}
                        </select>
                      </div>
                    )}

                    {/* Real-time Price Summary */}
                    <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl space-y-1.5">
                      <div className="flex justify-between text-xs text-slate-300">
                        <span>Paket bazası:</span>
                        <span className="font-medium">{basePrice.toFixed(2)} AZN</span>
                      </div>
                      {agentSelectedAgedPrice > 0 && (
                        <div className="flex justify-between text-xs text-amber-300">
                          <span>📦 Arxiv ({agentSelectedAgedMonths} ay):</span>
                          <span className="font-medium">+{agentSelectedAgedPrice.toFixed(2)} AZN</span>
                        </div>
                      )}
                      {agentSelectedExtraSearchesPrice > 0 && (
                        <div className="flex justify-between text-xs text-cyan-300">
                          <span>⚡ +{agentSelectedExtraSearches} axtarış:</span>
                          <span className="font-medium">+{agentSelectedExtraSearchesPrice.toFixed(2)} AZN</span>
                        </div>
                      )}
                      {agentSelectedImagePrice > 0 && (
                        <div className="flex justify-between text-xs text-teal-300">
                          <span>🖼️ +{agentSelectedImageRequests} foto:</span>
                          <span className="font-medium">+{agentSelectedImagePrice.toFixed(2)} AZN</span>
                        </div>
                      )}
                      <div className="border-t border-emerald-500/30 pt-1.5 flex justify-between text-sm font-bold">
                        <span className="text-white">Ümumi Məbləğ:</span>
                        <span className="text-emerald-400">{totalGross.toFixed(2)} AZN</span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-400">Sizin qazanc (%{commRate}):</span>
                        <span className="text-emerald-300 font-semibold">+{sellerProfit.toFixed(2)} AZN</span>
                      </div>
                    </div>
                  </div>
                );
              })()}

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

      {/* FREE TRIAL CONFIGURATION MODAL */}
      {isTrialModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 w-full max-w-xl rounded-3xl p-6 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Gift className="w-5 h-5 text-indigo-400" />
                  <span>Pulsuz Sınaq (Free Trial) Tənzimləmələri</span>
                </h3>
                <p className="text-xs text-slate-400">Agentləriniz üçün pulsuz sınaq müddəti və imkanlarını konfiqurasiya edin.</p>
              </div>
              <button onClick={() => setIsTrialModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveTrialSettings} className="space-y-5">
              {/* Status Switch */}
              <div className="p-3.5 bg-indigo-950/30 border border-indigo-500/20 rounded-2xl flex items-center justify-between">
                <div>
                  <span className="text-xs font-bold text-white block">Sınaq Təklifinin Statusu</span>
                  <span className="text-[11px] text-slate-400">
                    {trialEnabled ? 'Agentlər qeydiyyat zamanı pulsuz sınaqdan yararlana bilər' : 'Sınaq təklifi hazırda deaktivdir'}
                  </span>
                </div>
                <label className="flex items-center gap-2 text-xs font-bold text-indigo-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={trialEnabled}
                    onChange={(e) => setTrialEnabled(e.target.checked)}
                    className="rounded bg-slate-950 border-slate-800 text-indigo-600 focus:ring-0 w-4 h-4"
                  />
                  <span>{trialEnabled ? 'Aktivdir' : 'Deaktiv'}</span>
                </label>
              </div>

              {/* Numerical settings */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Sınaq Müddəti (Gün) *</label>
                  <input
                    type="number"
                    min="1"
                    max={dashboard?.max_trial_days || 14}
                    required
                    value={trialDays}
                    onChange={(e) => setTrialDays(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white text-xs font-semibold focus:outline-none focus:border-indigo-500"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">
                    Admin limiti: max {dashboard?.max_trial_days || 14} gün
                  </span>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-semibold text-slate-300">Axtarış Slotu</label>
                    <button
                      type="button"
                      onClick={() => setActiveTooltip(activeTooltip === 'trial_searches' ? null : 'trial_searches')}
                      className="text-[11px] text-indigo-400 hover:text-indigo-300 font-mono"
                    >
                      ℹ️
                    </button>
                  </div>
                  <input
                    type="number"
                    min="1"
                    max="20"
                    required
                    value={trialSearches}
                    onChange={(e) => setTrialSearches(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white text-xs font-semibold focus:outline-none focus:border-indigo-500"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">
                    Sınaq paralel axtarış sayı
                  </span>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-semibold text-slate-300">Məkan Limiti</label>
                    <button
                      type="button"
                      onClick={() => setActiveTooltip(activeTooltip === 'trial_locations' ? null : 'trial_locations')}
                      className="text-[11px] text-indigo-400 hover:text-indigo-300 font-mono"
                    >
                      ℹ️
                    </button>
                  </div>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    required
                    value={trialLocations}
                    onChange={(e) => setTrialLocations(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white text-xs font-semibold focus:outline-none focus:border-indigo-500"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">
                    Rayon/metro seçimi limiti
                  </span>
                </div>
              </div>

              {activeTooltip === 'trial_searches' && (
                <p className="text-[11px] text-slate-400 bg-slate-950 p-2.5 rounded-xl border border-slate-800 leading-relaxed">
                  Agentin sınaq müddətində eyni anda aktiv saxlaya biləcəyi daşınmaz əmlak filtri və axtarış tapşırığı sayı (Məs: 3).
                </p>
              )}
              {activeTooltip === 'trial_locations' && (
                <p className="text-[11px] text-slate-400 bg-slate-950 p-2.5 rounded-xl border border-slate-800 leading-relaxed">
                  Agentin hər bir axtarış daxilində eyni anda seçə biləcəyi rayon və ya metro stansiyası sayı (Məs: 3).
                </p>
              )}

              {/* Feature Toggles */}
              <div className="space-y-3 pt-3 border-t border-slate-800">
                <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
                  Sınaq Dövründə Aktiv Olan Funksiyalar
                </label>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {/* Makler Detector */}
                  <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1.5">
                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-2 text-xs font-semibold text-slate-200 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={trialMakler}
                          onChange={(e) => setTrialMakler(e.target.checked)}
                          className="rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-0"
                        />
                        <span>AI Makler Detektoru</span>
                      </label>
                      <button
                        type="button"
                        onClick={() => setActiveTooltip(activeTooltip === 'trial_makler' ? null : 'trial_makler')}
                        className="text-xs text-blue-400 hover:text-blue-300 px-1.5 py-0.5 rounded bg-blue-500/10 border border-blue-500/20"
                      >
                        ℹ️ İzah
                      </button>
                    </div>
                    {activeTooltip === 'trial_makler' && (
                      <p className="text-[11px] text-slate-400 bg-slate-900/90 p-2 rounded-lg border border-slate-800 leading-relaxed">
                        Elanın sahibindən və ya maklerdən olduğunu 95% dəqiqliklə təyin edən süni intellekt aləti.
                      </p>
                    )}
                  </div>

                  {/* AVM */}
                  <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1.5">
                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-2 text-xs font-semibold text-slate-200 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={trialAvm}
                          onChange={(e) => setTrialAvm(e.target.checked)}
                          className="rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-0"
                        />
                        <span>AVM Bazar Qiymətləndirmə</span>
                      </label>
                      <button
                        type="button"
                        onClick={() => setActiveTooltip(activeTooltip === 'trial_avm' ? null : 'trial_avm')}
                        className="text-xs text-emerald-400 hover:text-emerald-300 px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20"
                      >
                        ℹ️ İzah
                      </button>
                    </div>
                    {activeTooltip === 'trial_avm' && (
                      <p className="text-[11px] text-slate-400 bg-slate-900/90 p-2 rounded-lg border border-slate-800 leading-relaxed">
                        Mənzilin real bazar dəyərini (AVM) hesablayır və bazardan aşağı düşən fürsət elanları bildirir.
                      </p>
                    )}
                  </div>

                  {/* Brochure */}
                  <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1.5">
                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-2 text-xs font-semibold text-slate-200 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={trialBrochure}
                          onChange={(e) => setTrialBrochure(e.target.checked)}
                          className="rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-0"
                        />
                        <span>PDF & Sosial Buklet</span>
                      </label>
                      <button
                        type="button"
                        onClick={() => setActiveTooltip(activeTooltip === 'trial_brochure' ? null : 'trial_brochure')}
                        className="text-xs text-indigo-400 hover:text-indigo-300 px-1.5 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20"
                      >
                        ℹ️ İzah
                      </button>
                    </div>
                    {activeTooltip === 'trial_brochure' && (
                      <p className="text-[11px] text-slate-400 bg-slate-900/90 p-2 rounded-lg border border-slate-800 leading-relaxed">
                        Elan üçün bir kliklə agentin nömrəsi və brendi ilə peşəkar PDF və Instagram hekayə bukletləri hazırlayır.
                      </p>
                    )}
                  </div>

                  {/* Multi Location */}
                  <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1.5">
                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-2 text-xs font-semibold text-slate-200 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={trialMultiLocation}
                          onChange={(e) => setTrialMultiLocation(e.target.checked)}
                          className="rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-0"
                        />
                        <span>Çoxsaylı Məkan Axtarışı</span>
                      </label>
                      <button
                        type="button"
                        onClick={() => setActiveTooltip(activeTooltip === 'trial_multi' ? null : 'trial_multi')}
                        className="text-xs text-amber-400 hover:text-amber-300 px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/20"
                      >
                        ℹ️ İzah
                      </button>
                    </div>
                    {activeTooltip === 'trial_multi' && (
                      <p className="text-[11px] text-slate-400 bg-slate-900/90 p-2 rounded-lg border border-slate-800 leading-relaxed">
                        Agentə eyni axtarış tapşırığı daxilində birdən çox rayon və ya metro seçməyə imkan verir.
                      </p>
                    )}
                  </div>

                  {/* Watermark-Free Photos */}
                  <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1.5 col-span-1 sm:col-span-2">
                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-2 text-xs font-semibold text-teal-300 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={trialWatermarkImages}
                          onChange={(e) => setTrialWatermarkImages(e.target.checked)}
                          className="rounded bg-slate-900 border-slate-700 text-teal-500 focus:ring-0"
                        />
                        <span>🖼️ Su Nişansız Şəkillər Add-on</span>
                      </label>
                      {trialWatermarkImages && (
                        <div className="flex items-center gap-1.5">
                          <span className="text-[11px] text-slate-400">Sınaq Foto Limiti:</span>
                          <input
                            type="number"
                            min="0"
                            max="50"
                            value={trialImageRequests}
                            onChange={(e) => setTrialImageRequests(Number(e.target.value))}
                            className="w-16 bg-slate-900 border border-slate-700 rounded-lg px-2 py-0.5 text-white text-xs text-center font-bold"
                          />
                        </div>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      Sınaq müddətində agentlərə portal su nişanı silinmiş orijinal şəkilləri (/foto elan_id) əldə etmək üçün pulsuz limit verir.
                    </p>
                  </div>
                </div>
              </div>

              <div className="pt-3 flex gap-3">
                <button
                  type="button"
                  onClick={() => setIsTrialModalOpen(false)}
                  className="w-1/2 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium rounded-xl transition text-xs"
                >
                  Ləğv et
                </button>
                <button
                  type="submit"
                  disabled={savingTrial}
                  className="w-1/2 py-2.5 bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white font-semibold rounded-xl shadow-lg shadow-indigo-500/25 transition disabled:opacity-50 text-xs"
                >
                  {savingTrial ? 'Saxlanılır...' : 'Sınaq Parametrlərini Yadda Saxla'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CREATE / EDIT PACKAGE MODAL */}
      {isAddPkgOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 w-full max-w-xl rounded-3xl p-6 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Package className="w-5 h-5 text-blue-400" />
                  <span>{editingPkg ? 'Paketi Redaktə Et' : 'Yeni Fərdi Agent Paketi'}</span>
                </h3>
                <p className="text-xs text-slate-400">Agentləriniz üçün fərdi qiymət və imkanları konfiqurasiya edin.</p>
              </div>
              <button onClick={() => setIsAddPkgOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSavePackage} className="space-y-5">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Paketin Adı *</label>
                <input
                  type="text"
                  required
                  value={pkgName}
                  onChange={(e) => setPkgName(e.target.value)}
                  placeholder="Məs: Standart Agent, VIP Broker Paketi"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Paket Qiyməti (AZN) *</label>
                  <input
                    type="number"
                    min={dashboard?.min_package_price || 29}
                    step="1"
                    required
                    value={pkgPrice}
                    onChange={(e) => setPkgPrice(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">
                    Admin minimum limiti: {dashboard?.min_package_price || 29} AZN
                  </span>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Müddət (Gün)</label>
                  <input
                    type="number"
                    min="1"
                    max="365"
                    required
                    value={pkgDuration}
                    onChange={(e) => setPkgDuration(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">
                    Standart aylıq abunə: 30 gün
                  </span>
                </div>

                <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-xs flex justify-between items-center col-span-2">
                  <span className="text-slate-300 font-medium">
                    Sizin Komissiya Payınız (%{dashboard?.effective_commission_rate ?? dashboard?.commission_rate ?? 70}):
                  </span>
                  <span className="font-bold text-emerald-400 text-sm">
                    +{((((pkgSaleEnabled && pkgSalePrice) ? pkgSalePrice : pkgPrice) * (dashboard?.effective_commission_rate ?? dashboard?.commission_rate ?? 70)) / 100).toFixed(1)} AZN
                  </span>
                </div>
              </div>

              {/* Promotional Sale & Discount Settings */}
              <div className="p-4 bg-gradient-to-br from-rose-950/30 via-slate-950/60 to-slate-950/40 border border-rose-500/30 rounded-2xl space-y-4">
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
                      checked={pkgSaleEnabled}
                      onChange={(e) => {
                        const enabled = e.target.checked;
                        setPkgSaleEnabled(enabled);
                        if (enabled && !pkgSalePrice && !pkgSaleDiscountPercent) {
                          const defPercent = 20;
                          setPkgSaleDiscountPercent(defPercent);
                          setPkgSalePrice(Math.round(pkgPrice * (1 - defPercent / 100)));
                        }
                      }}
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-rose-600"></div>
                  </label>
                </div>

                {pkgSaleEnabled && (
                  <div className="space-y-3 pt-2 border-t border-rose-500/20 text-xs">
                    <div>
                      <label className="block text-slate-300 font-semibold mb-1">Endirim Növü (Kampaniya Şərti)</label>
                      <select
                        value={pkgSaleType}
                        onChange={(e) => setPkgSaleType(e.target.value)}
                        className="w-full bg-slate-900 border border-rose-500/40 rounded-xl px-3 py-2 text-white font-medium focus:outline-none focus:border-rose-400"
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
                          value={pkgSaleDiscountPercent || ''}
                          onChange={(e) => {
                            const pct = Number(e.target.value);
                            setPkgSaleDiscountPercent(pct);
                            if (pct > 0 && pkgPrice > 0) {
                              setPkgSalePrice(Math.round(pkgPrice * (1 - pct / 100)));
                            }
                          }}
                          className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-rose-400"
                        />
                      </div>

                      <div>
                        <label className="block text-slate-300 font-semibold mb-1">Endirimli Qiymət (AZN)</label>
                        <input
                          type="number"
                          min="1"
                          step="1"
                          placeholder="Məs: 39 AZN"
                          value={pkgSalePrice || ''}
                          onChange={(e) => {
                            const pr = Number(e.target.value);
                            setPkgSalePrice(pr);
                            if (pr > 0 && pkgPrice > 0) {
                              setPkgSaleDiscountPercent(Math.round(((pkgPrice - pr) / pkgPrice) * 100));
                            }
                          }}
                          className="w-full bg-slate-900 border border-emerald-500/50 rounded-xl px-3 py-2 text-emerald-400 font-bold focus:outline-none focus:border-emerald-400"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-slate-300 font-semibold mb-1">Xüsusi Nişan Mətni (Könüllü)</label>
                        <input
                          type="text"
                          placeholder="Məs: 🔥 YAZ ENDİRİMİ"
                          value={pkgSaleBadgeLabel}
                          onChange={(e) => setPkgSaleBadgeLabel(e.target.value)}
                          className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-rose-400"
                        />
                      </div>

                      {pkgSaleType === 'limited_time' ? (
                        <div>
                          <label className="block text-slate-300 font-semibold mb-1">Kampaniya Bitmə Tarixi</label>
                          <input
                            type="date"
                            value={pkgSaleExpiresAt}
                            onChange={(e) => setPkgSaleExpiresAt(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-rose-400"
                          />
                        </div>
                      ) : (
                        <div className="flex flex-col justify-center">
                          <span className="text-[11px] text-slate-400">Endirimli Xalis Qazanc:</span>
                          <span className="text-emerald-400 font-bold text-sm">
                            +{(((pkgSalePrice || pkgPrice) * (dashboard?.effective_commission_rate ?? dashboard?.commission_rate ?? 70)) / 100).toFixed(1)} AZN
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-semibold text-slate-300">Axtarış Slotu Limiti</label>
                    <button
                      type="button"
                      onClick={() => setActiveTooltip(activeTooltip === 'searches' ? null : 'searches')}
                      className="text-[11px] text-blue-400 hover:text-blue-300 font-mono"
                      title="Məlumat"
                    >
                      ℹ️
                    </button>
                  </div>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    required
                    value={pkgMaxSearches}
                    onChange={(e) => setPkgMaxSearches(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                  {activeTooltip === 'searches' && (
                    <div className="mt-1 p-2 bg-slate-950 rounded-lg text-[11px] text-slate-300 border border-blue-500/30">
                      Agentin sistemdə eyni vaxtda aktiv saxlaya biləcəyi daimi axtarış filtrlərinin sayı (Məs: 10 Axtarış).
                    </div>
                  )}
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-semibold text-slate-300">Max Məkan / Metro Limiti</label>
                    <button
                      type="button"
                      onClick={() => setActiveTooltip(activeTooltip === 'locations' ? null : 'locations')}
                      className="text-[11px] text-blue-400 hover:text-blue-300 font-mono"
                      title="Məlumat"
                    >
                      ℹ️
                    </button>
                  </div>
                  <input
                    type="number"
                    min="1"
                    max="20"
                    required
                    value={pkgMaxLocations}
                    onChange={(e) => setPkgMaxLocations(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                  {activeTooltip === 'locations' && (
                    <div className="mt-1 p-2 bg-slate-950 rounded-lg text-[11px] text-slate-300 border border-blue-500/30">
                      Bir axtarış sorğusunda eyni vaxtda birləşdirilə bilən fərqli rayon və ya metro stansiyalarının sayı (max 5 məkan).
                    </div>
                  )}
                </div>
              </div>

              {/* Main Feature Flags with "i" Explanation Popups */}
              <div className="space-y-3 pt-3 border-t border-slate-800">
                <label className="text-xs font-bold text-white uppercase tracking-wider block">
                  Paketə Daxil Olan Əsas İmkanlar
                </label>

                <div className="space-y-2">
                  {/* Feature 1: Makler Detector */}
                  <div className="p-2.5 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-2 text-xs text-slate-200 cursor-pointer font-medium">
                        <input
                          type="checkbox"
                          checked={pkgMakler}
                          onChange={(e) => setPkgMakler(e.target.checked)}
                          className="rounded bg-slate-900 border-slate-700 text-blue-600 focus:ring-0"
                        />
                        <span>AI Makler & Vasitəçi Detektoru</span>
                      </label>
                      <button
                        type="button"
                        onClick={() => setActiveTooltip(activeTooltip === 'makler' ? null : 'makler')}
                        className="text-xs text-blue-400 hover:text-blue-300 px-1.5 py-0.5 rounded bg-blue-500/10 border border-blue-500/20"
                      >
                        ℹ️ İzah
                      </button>
                    </div>
                    {activeTooltip === 'makler' && (
                      <p className="text-[11px] text-slate-400 bg-slate-900/90 p-2 rounded-lg border border-slate-800 leading-relaxed">
                        Elan mətni və telefon tarixçəsini AI ilə analiz edərək maklerləri/vasitəçiləri aşkarlayır və birbaşa sahibindən olan elanları filtirləyir.
                      </p>
                    )}
                  </div>

                  {/* Feature 2: AVM Bargain Finder */}
                  <div className="p-2.5 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-2 text-xs text-slate-200 cursor-pointer font-medium">
                        <input
                          type="checkbox"
                          checked={pkgAvm}
                          onChange={(e) => setPkgAvm(e.target.checked)}
                          className="rounded bg-slate-900 border-slate-700 text-blue-600 focus:ring-0"
                        />
                        <span>AVM Bazar Qiyməti & Fırsət Bildirişi</span>
                      </label>
                      <button
                        type="button"
                        onClick={() => setActiveTooltip(activeTooltip === 'avm' ? null : 'avm')}
                        className="text-xs text-blue-400 hover:text-blue-300 px-1.5 py-0.5 rounded bg-blue-500/10 border border-blue-500/20"
                      >
                        ℹ️ İzah
                      </button>
                    </div>
                    {activeTooltip === 'avm' && (
                      <p className="text-[11px] text-slate-400 bg-slate-900/90 p-2 rounded-lg border border-slate-800 leading-relaxed">
                        Məhəllə və bina üzrə orta bazar qiymətini (AZN/m²) avtomatik hesablayır və bazar qiymətindən 15%+ aşağı olan fürsət elanlarını xüsusi işarə ilə bildirir.
                      </p>
                    )}
                  </div>

                  {/* Feature 3: Social Brochure Generator */}
                  <div className="p-2.5 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-2 text-xs text-slate-200 cursor-pointer font-medium">
                        <input
                          type="checkbox"
                          checked={pkgSocialBrochure}
                          onChange={(e) => setPkgSocialBrochure(e.target.checked)}
                          className="rounded bg-slate-900 border-slate-700 text-blue-600 focus:ring-0"
                        />
                        <span>PDF & Sosial Şəbəkə Buklet Generatoru</span>
                      </label>
                      <button
                        type="button"
                        onClick={() => setActiveTooltip(activeTooltip === 'brochure' ? null : 'brochure')}
                        className="text-xs text-blue-400 hover:text-blue-300 px-1.5 py-0.5 rounded bg-blue-500/10 border border-blue-500/20"
                      >
                        ℹ️ İzah
                      </button>
                    </div>
                    {activeTooltip === 'brochure' && (
                      <p className="text-[11px] text-slate-400 bg-slate-900/90 p-2 rounded-lg border border-slate-800 leading-relaxed">
                        Agentlər üçün elanlardan 1 kliklə WhatsApp və Instagram üçün fərdi brend loqolu PDF və foto bukletlər hazırlayır.
                      </p>
                    )}
                  </div>

                  {/* Feature 4: Multi-Location Search */}
                  <div className="p-2.5 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-2 text-xs text-slate-200 cursor-pointer font-medium">
                        <input
                          type="checkbox"
                          checked={pkgMultiLocation}
                          onChange={(e) => setPkgMultiLocation(e.target.checked)}
                          className="rounded bg-slate-900 border-slate-700 text-blue-600 focus:ring-0"
                        />
                        <span>Çoxsaylı Məkan & Qonşu Metro Axtarışı</span>
                      </label>
                      <button
                        type="button"
                        onClick={() => setActiveTooltip(activeTooltip === 'multiloc' ? null : 'multiloc')}
                        className="text-xs text-blue-400 hover:text-blue-300 px-1.5 py-0.5 rounded bg-blue-500/10 border border-blue-500/20"
                      >
                        ℹ️ İzah
                      </button>
                    </div>
                    {activeTooltip === 'multiloc' && (
                      <p className="text-[11px] text-slate-400 bg-slate-900/90 p-2 rounded-lg border border-slate-800 leading-relaxed">
                        Agentə eyni axtarışda bir neçə qonşu metro (məs: Elmlər + Nizami + 28 May) və rayonları eyni vaxtda izləməyə icazə verir.
                      </p>
                    )}
                  </div>

                  {/* Feature 5: Branded Intake Bot */}
                  <div className="p-2.5 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-2 text-xs text-slate-200 cursor-pointer font-medium">
                        <input
                          type="checkbox"
                          checked={pkgIntakeBot}
                          onChange={(e) => setPkgIntakeBot(e.target.checked)}
                          className="rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-0"
                        />
                        <span className="text-indigo-300 font-semibold">Brendli Müştəri Qəbul Botu</span>
                      </label>
                      <button
                        type="button"
                        onClick={() => setActiveTooltip(activeTooltip === 'bot' ? null : 'bot')}
                        className="text-xs text-indigo-400 hover:text-indigo-300 px-1.5 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20"
                      >
                        ℹ️ İzah
                      </button>
                    </div>
                    {activeTooltip === 'bot' && (
                      <p className="text-[11px] text-slate-400 bg-slate-900/90 p-2 rounded-lg border border-slate-800 leading-relaxed">
                        Agentin müştəriləri üçün Telegram/WhatsApp üzərindən avtomatlaşdırılmış sorğu-sual və mülk tələblərinin toplanması botu.
                      </p>
                    )}
                  </div>

                  {/* Feature 6: Backup Service */}
                  <div className="p-2.5 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-2 text-xs text-slate-200 cursor-pointer font-medium">
                        <input
                          type="checkbox"
                          checked={pkgBackup}
                          onChange={(e) => setPkgBackup(e.target.checked)}
                          className="rounded bg-slate-900 border-slate-700 text-purple-600 focus:ring-0"
                        />
                        <span className="text-purple-300 font-semibold">Avtomatik BaaS Data Backup</span>
                      </label>
                      <button
                        type="button"
                        onClick={() => setActiveTooltip(activeTooltip === 'backup' ? null : 'backup')}
                        className="text-xs text-purple-400 hover:text-purple-300 px-1.5 py-0.5 rounded bg-purple-500/10 border border-purple-500/20"
                      >
                        ℹ️ İzah
                      </button>
                    </div>
                    {activeTooltip === 'backup' && (
                      <p className="text-[11px] text-slate-400 bg-slate-900/90 p-2 rounded-lg border border-slate-800 leading-relaxed">
                        Agentin bütün axtarışları, bəyəndiyi elanları və müştəri siyahısını həftəlik arxivləşdirir və təhlükəsiz e-poçtuna göndərir.
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* Add-on Features & Pricing with Dynamic Tiers */}
              <div className="space-y-3 pt-3 border-t border-slate-800">
                <label className="text-xs font-bold text-cyan-400 uppercase tracking-wider block">
                  Əlavə Xidmətlər (Add-ons) — Çoxpilləli Qiymət
                </label>

                {/* Add-on 1: Extra Search Tiers */}
                <div className="p-3 bg-cyan-950/20 border border-cyan-500/20 rounded-xl space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-cyan-300">
                      ⚡ Əlavə Axtarış Limitləri
                    </span>
                    <button
                      type="button"
                      onClick={() => setPkgSearchTiers([...pkgSearchTiers, { searches: 5, price: 10 }])}
                      className="text-[11px] text-cyan-400 hover:text-cyan-300 px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/20"
                    >
                      + Sətr əlavə et
                    </button>
                  </div>
                  <p className="text-[10px] text-slate-500">Hər sətr üçün əlavə axtarış sayı və qiyməti təyin edin. Agent qeydiyyatı zamanı müştəri bunlardan birini seçə biləcək.</p>
                  {pkgSearchTiers.map((tier, idx) => (
                    <div key={idx} className="grid grid-cols-[1fr_1fr_auto] gap-2 items-end">
                      <div>
                        <label className="text-[10px] text-slate-400 block mb-0.5">+Axtarış Sayı</label>
                        <input
                          type="number"
                          min="1"
                          max="100"
                          value={tier.searches}
                          onChange={(e) => {
                            const copy = [...pkgSearchTiers];
                            copy[idx] = { ...copy[idx], searches: Number(e.target.value) };
                            setPkgSearchTiers(copy);
                          }}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-white text-xs"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-slate-400 block mb-0.5">Qiymət (AZN)</label>
                        <input
                          type="number"
                          min="0"
                          step="0.5"
                          value={tier.price}
                          onChange={(e) => {
                            const copy = [...pkgSearchTiers];
                            copy[idx] = { ...copy[idx], price: Number(e.target.value) };
                            setPkgSearchTiers(copy);
                          }}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-white text-xs font-bold text-cyan-400"
                        />
                      </div>
                      <button
                        type="button"
                        onClick={() => setPkgSearchTiers(pkgSearchTiers.filter((_, i) => i !== idx))}
                        className="text-rose-400 hover:text-rose-300 p-1.5 rounded-lg hover:bg-rose-500/10"
                        title="Sil"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                  {pkgSearchTiers.length === 0 && (
                    <p className="text-[10px] text-slate-600 italic py-1">Heç bir əlavə axtarış pilləsi yoxdur.</p>
                  )}
                </div>

                {/* Add-on 2: Aged Inventory Archive Tiers */}
                <div className="p-3 bg-amber-950/20 border border-amber-500/20 rounded-xl space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 text-xs font-semibold text-amber-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={pkgAgedListings}
                        onChange={(e) => setPkgAgedListings(e.target.checked)}
                        className="rounded bg-slate-900 border-slate-700 text-amber-600 focus:ring-0"
                      />
                      <span>📦 Köhnə Elanlar Arxivi</span>
                    </label>
                    {pkgAgedListings && (
                      <button
                        type="button"
                        onClick={() => setPkgAgedTiers([...pkgAgedTiers, { months: 3, price: 15 }])}
                        className="text-[11px] text-amber-400 hover:text-amber-300 px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/20"
                      >
                        + Sətr əlavə et
                      </button>
                    )}
                  </div>
                  {pkgAgedListings && (
                    <>
                      <p className="text-[10px] text-slate-500">Hər sətr üçün arxiv müddəti (ay) və qiymət təyin edin. Agent qeydiyyatı zamanı müştəri bunlardan birini seçə biləcək.</p>
                      {pkgAgedTiers.map((tier, idx) => (
                        <div key={idx} className="grid grid-cols-[1fr_1fr_auto] gap-2 items-end">
                          <div>
                            <label className="text-[10px] text-slate-400 block mb-0.5">Müddət (Ay)</label>
                            <input
                              type="number"
                              min="1"
                              max="48"
                              value={tier.months}
                              onChange={(e) => {
                                const copy = [...pkgAgedTiers];
                                copy[idx] = { ...copy[idx], months: Number(e.target.value) };
                                setPkgAgedTiers(copy);
                              }}
                              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-white text-xs"
                            />
                          </div>
                          <div>
                            <label className="text-[10px] text-slate-400 block mb-0.5">Qiymət (AZN)</label>
                            <input
                              type="number"
                              min="0"
                              step="0.5"
                              value={tier.price}
                              onChange={(e) => {
                                const copy = [...pkgAgedTiers];
                                copy[idx] = { ...copy[idx], price: Number(e.target.value) };
                                setPkgAgedTiers(copy);
                              }}
                              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-white text-xs font-bold text-amber-400"
                            />
                          </div>
                          <button
                            type="button"
                            onClick={() => setPkgAgedTiers(pkgAgedTiers.filter((_, i) => i !== idx))}
                            className="text-rose-400 hover:text-rose-300 p-1.5 rounded-lg hover:bg-rose-500/10"
                            title="Sil"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))}
                      {pkgAgedTiers.length === 0 && (
                        <p className="text-[10px] text-slate-600 italic py-1">Heç bir arxiv pilləsi yoxdur.</p>
                      )}
                    </>
                  )}
                </div>

                {/* Add-on 3: Watermark-Free Image Requests Tiers */}
                <div className="p-3 bg-teal-950/20 border border-teal-500/20 rounded-xl space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 text-xs font-semibold text-teal-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={pkgWatermarkImages}
                        onChange={(e) => setPkgWatermarkImages(e.target.checked)}
                        className="rounded bg-slate-900 border-slate-700 text-teal-500 focus:ring-0"
                      />
                      <span>🖼️ Su Nişansız Şəkillər Add-on</span>
                    </label>
                    {pkgWatermarkImages && (
                      <button
                        type="button"
                        onClick={() => setPkgImageTiers([...pkgImageTiers, { requests: 25, price: 10 }])}
                        className="text-[11px] text-teal-400 hover:text-teal-300 px-2 py-0.5 rounded bg-teal-500/10 border border-teal-500/20"
                      >
                        + Sətr əlavə et
                      </button>
                    )}
                  </div>
                  {pkgWatermarkImages && (
                    <>
                      <div className="flex items-center justify-between text-xs text-slate-300 pt-1 pb-1">
                        <span>Paketə Daxil Olan Foto Sorğu Sayı:</span>
                        <div className="flex items-center gap-1.5">
                          <input
                            type="number"
                            min="0"
                            value={pkgIncludedImages}
                            onChange={(e) => setPkgIncludedImages(Number(e.target.value))}
                            className="w-20 bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-white text-xs text-center font-bold"
                            placeholder="Məs: 25"
                          />
                          <span className="text-[11px] text-slate-500">foto</span>
                        </div>
                      </div>
                      <p className="text-[10px] text-slate-500">Əlavə foto paketləri (Top-up) üçün foto sayı və qiymət təyin edin.</p>
                      {pkgImageTiers.map((tier, idx) => (
                        <div key={idx} className="grid grid-cols-[1fr_1fr_auto] gap-2 items-end">
                          <div>
                            <label className="text-[10px] text-slate-400 block mb-0.5">+Foto Sayı</label>
                            <input
                              type="number"
                              min="1"
                              value={tier.requests}
                              onChange={(e) => {
                                const copy = [...pkgImageTiers];
                                copy[idx] = { ...copy[idx], requests: Number(e.target.value) };
                                setPkgImageTiers(copy);
                              }}
                              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-white text-xs font-bold"
                            />
                          </div>
                          <div>
                            <label className="text-[10px] text-slate-400 block mb-0.5">Qiymət (AZN)</label>
                            <input
                              type="number"
                              min="0"
                              step="0.5"
                              value={tier.price}
                              onChange={(e) => {
                                const copy = [...pkgImageTiers];
                                copy[idx] = { ...copy[idx], price: Number(e.target.value) };
                                setPkgImageTiers(copy);
                              }}
                              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-white text-xs font-bold text-teal-400"
                            />
                          </div>
                          <button
                            type="button"
                            onClick={() => setPkgImageTiers(pkgImageTiers.filter((_, i) => i !== idx))}
                            className="text-rose-400 hover:text-rose-300 p-1.5 rounded-lg hover:bg-rose-500/10"
                            title="Sil"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))}
                      {pkgImageTiers.length === 0 && (
                        <p className="text-[10px] text-slate-600 italic py-1">Heç bir əlavə foto paketi pilləsi yoxdur.</p>
                      )}
                    </>
                  )}
                </div>
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
                  {submittingPkg ? 'Saxlanılır...' : (editingPkg ? 'Dəyişiklikləri Yadda Saxla' : 'Paket Yarat')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* WITHDRAWAL / PAYOUT REQUEST MODAL */}
      {isWithdrawOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-md p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <span>💸</span> <span>Balansı Bank Kartına Çıxar</span>
              </h3>
              <button onClick={() => setIsWithdrawOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {withdrawError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400">
                {withdrawError}
              </div>
            )}

            <form onSubmit={handleRequestPayout} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">
                  Çıxarış Məbləği (AZN) <span className="text-emerald-400 font-normal">(Mövcud balans: {dashboard?.balance.toLocaleString()} AZN)</span>
                </label>
                <input
                  type="number"
                  min="1"
                  max={dashboard?.balance || 0}
                  step="0.01"
                  required
                  value={withdrawAmount || ''}
                  onChange={(e) => setWithdrawAmount(parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Bank Kart Nömrəsi (16 rəqəm)</label>
                <input
                  type="text"
                  required
                  placeholder="4169 7388 1234 5678"
                  value={withdrawCard}
                  onChange={(e) => setWithdrawCard(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm font-mono text-cyan-300 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Kart Sahibinin Adı və Soyadı</label>
                <input
                  type="text"
                  required
                  placeholder="AD SOYAD (Məs: ELMİR MƏMMƏDOV)"
                  value={withdrawName}
                  onChange={(e) => setWithdrawName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white uppercase focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">IBAN / Hesab Nömrəsi (İstəyə bağlı)</label>
                <input
                  type="text"
                  placeholder="AZ00AAAA00000000000000000000"
                  value={withdrawIban}
                  onChange={(e) => setWithdrawIban(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs font-mono text-slate-300 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Əlavə Qeyd (İstəyə bağlı)</label>
                <textarea
                  rows={2}
                  placeholder="Məs: BirBank kartı"
                  value={withdrawNotes}
                  onChange={(e) => setWithdrawNotes(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="pt-2 flex gap-3">
                <button
                  type="button"
                  onClick={() => setIsWithdrawOpen(false)}
                  className="w-1/2 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium rounded-xl text-xs transition"
                >
                  Ləğv et
                </button>
                <button
                  type="submit"
                  disabled={submittingWithdraw || !withdrawAmount || withdrawAmount <= 0}
                  className="w-1/2 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold rounded-xl text-xs shadow-lg shadow-emerald-600/25 transition disabled:opacity-50"
                >
                  {submittingWithdraw ? 'Göndərilir...' : 'Təsdiqlə və Göndər'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
