import React, { useEffect, useState } from 'react';
import {
  Briefcase, Users, CheckCircle, Clock, Search, Plus, Filter,
  Phone, MessageSquare, ExternalLink, Calendar, DollarSign,
  ChevronRight, X, AlertCircle, Edit3, Trash2, ArrowRight, Share2, Sparkles,
  Globe, Copy, Check, Eye, FolderPlus, Layers, Image as ImageIcon, MapPin, Tag, Home,
  Settings, ShieldCheck, CheckCircle2, Bell, CheckSquare, Square
} from 'lucide-react';
import api from '../api';
import { CrmDeal, CrmClient, CrmStats, PortfolioListingItem, PortfolioOverview, CrmReminderItem } from '../types';

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        ready: () => void;
        expand: () => void;
        close: () => void;
        initData: string;
        initDataUnsafe?: {
          user?: {
            id: number;
            first_name: string;
            last_name?: string;
            username?: string;
            language_code?: string;
          };
          start_param?: string;
        };
        themeParams?: {
          bg_color?: string;
          text_color?: string;
          button_color?: string;
          button_text_color?: string;
          secondary_bg_color?: string;
        };
        HapticFeedback?: {
          impactOccurred: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => void;
          notificationOccurred: (type: 'error' | 'success' | 'warning') => void;
        };
      };
    };
  }
}

const STAGES = [
  { key: 'new', label: 'Yeni', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  { key: 'offered', label: 'Təklif Edildi', color: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
  { key: 'viewing', label: 'Baxış Təyin Edildi', color: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
  { key: 'negotiation', label: 'Danışıqlar / Beh', color: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30' },
  { key: 'closed', label: 'Uğurla Bağlandı 🎉', color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' },
  { key: 'lost', label: 'İmtina Edildi', color: 'bg-rose-500/20 text-rose-400 border-rose-500/30' },
];

const REMINDER_TYPE_META: Record<string, { label: string; icon: string; bg: string; text: string; border: string }> = {
  viewing: { label: 'Baxış', icon: '🏠', bg: 'bg-purple-500/15', text: 'text-purple-400', border: 'border-purple-500/30' },
  call: { label: 'Zəng', icon: '📞', bg: 'bg-blue-500/15', text: 'text-blue-400', border: 'border-blue-500/30' },
  follow_up: { label: 'İzləmə', icon: '🔄', bg: 'bg-amber-500/15', text: 'text-amber-400', border: 'border-amber-500/30' },
  notary: { label: 'Notariat', icon: '🖋️', bg: 'bg-emerald-500/15', text: 'text-emerald-400', border: 'border-emerald-500/30' },
  other: { label: 'Tapşırıq', icon: '📌', bg: 'bg-slate-500/15', text: 'text-slate-300', border: 'border-slate-500/30' },
};

export function TmaCrm() {
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const [agentName, setAgentName] = useState<string>('Agent');
  const [agentPhone, setAgentPhone] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'deals' | 'clients' | 'reminders' | 'portfolio' | 'stats'>('deals');
  
  const [deals, setDeals] = useState<CrmDeal[]>([]);
  const [clients, setClients] = useState<CrmClient[]>([]);
  const [reminders, setReminders] = useState<CrmReminderItem[]>([]);
  const [stats, setStats] = useState<CrmStats | null>(null);

  // Portfolio State
  const [portfolioItems, setPortfolioItems] = useState<PortfolioListingItem[]>([]);
  const [portfolioOverview, setPortfolioOverview] = useState<PortfolioOverview | null>(null);
  const [portfolioSlug, setPortfolioSlug] = useState<string>('');
  const [portfolioLimit, setPortfolioLimit] = useState<number>(25);
  const [portfolioActiveCount, setPortfolioActiveCount] = useState<number>(0);
  const [portfolioSearch, setPortfolioSearch] = useState<string>('');
  const [portfolioFilter, setPortfolioFilter] = useState<'all' | 'active' | 'sold'>('all');

  // Portfolio Edit/Create Modal State
  const [selectedPortfolioItem, setSelectedPortfolioItem] = useState<PortfolioListingItem | null>(null);
  const [isNewPortfolioModal, setIsNewPortfolioModal] = useState(false);
  const [savingPortfolio, setSavingPortfolio] = useState(false);

  // Form fields for editing/creating portfolio listings
  const [editPortTitle, setEditPortTitle] = useState('');
  const [editPortPrice, setEditPortPrice] = useState('');
  const [editPortCurrency, setEditPortCurrency] = useState('AZN');
  const [editPortPriceUsd, setEditPortPriceUsd] = useState('');
  const [editPortDescription, setEditPortDescription] = useState('');
  const [editPortRooms, setEditPortRooms] = useState('');
  const [editPortArea, setEditPortArea] = useState('');
  const [editPortFloor, setEditPortFloor] = useState('');
  const [editPortTotalFloors, setEditPortTotalFloors] = useState('');
  const [editPortDistrict, setEditPortDistrict] = useState('');
  const [editPortMetro, setEditPortMetro] = useState('');
  const [editPortAddress, setEditPortAddress] = useState('');
  const [editPortOfferType, setEditPortOfferType] = useState('sale');
  const [editPortBuildingType, setEditPortBuildingType] = useState('new_building');
  const [editPortPropertyType, setEditPortPropertyType] = useState('apartment');
  const [editPortContactName, setEditPortContactName] = useState('');
  const [editPortContactPhone, setEditPortContactPhone] = useState('');
  const [editPortNotes, setEditPortNotes] = useState('');
  const [editPortStatus, setEditPortStatus] = useState('active');
  const [editPortIsActive, setEditPortIsActive] = useState(true);
  const [editPortPhotos, setEditPortPhotos] = useState<string[]>([]);
  const [newPhotoInput, setNewPhotoInput] = useState('');
  const [copiedToast, setCopiedToast] = useState<string | null>(null);

  // Domain Management Modal State
  const [showDomainModal, setShowDomainModal] = useState(false);
  const [domainInput, setDomainInput] = useState('');
  const [domainEnabled, setDomainEnabled] = useState(true);
  const [domainSaving, setDomainSaving] = useState(false);
  const [domainVerifying, setDomainVerifying] = useState(false);
  const [domainVerifyResult, setDomainVerifyResult] = useState<{ verified: boolean; message: string; dns_detected?: boolean } | null>(null);
  
  const [selectedStage, setSelectedStage] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  
  // Deal Edit/View Modal
  const [selectedDeal, setSelectedDeal] = useState<CrmDeal | null>(null);
  const [editStage, setEditStage] = useState<string>('new');
  const [editClientId, setEditClientId] = useState<number | ''>('');
  const [editOfferPrice, setEditOfferPrice] = useState<string>('');
  const [editCommission, setEditCommission] = useState<string>('');
  const [editNotes, setEditNotes] = useState<string>('');
  const [editViewingAt, setEditViewingAt] = useState<string>('');
  const [savingDeal, setSavingDeal] = useState(false);

  // New Client Modal
  const [showNewClientModal, setShowNewClientModal] = useState(false);
  const [newClientName, setNewClientName] = useState('');
  const [newClientPhone, setNewClientPhone] = useState('');
  const [newClientType, setNewClientType] = useState<'buyer' | 'renter'>('buyer');
  const [newClientBudget, setNewClientBudget] = useState('');
  const [newClientNotes, setNewClientNotes] = useState('');
  const [savingClient, setSavingClient] = useState(false);

  // Reminder Modal & Filter State
  const [reminderFilter, setReminderFilter] = useState<'pending' | 'all' | 'completed'>('pending');
  const [showReminderModal, setShowReminderModal] = useState(false);
  const [selectedReminder, setSelectedReminder] = useState<CrmReminderItem | null>(null);
  const [reminderTitle, setReminderTitle] = useState('');
  const [reminderType, setReminderType] = useState<'viewing' | 'call' | 'follow_up' | 'notary' | 'other'>('viewing');
  const [reminderDueAt, setReminderDueAt] = useState('');
  const [reminderLeadMinutes, setReminderLeadMinutes] = useState<number>(60);
  const [reminderClientId, setReminderClientId] = useState<number | ''>('');
  const [reminderDealId, setReminderDealId] = useState<number | ''>('');
  const [reminderNotes, setReminderNotes] = useState('');
  const [reminderStatus, setReminderStatus] = useState<'pending' | 'notified' | 'completed' | 'cancelled'>('pending');
  const [savingReminder, setSavingReminder] = useState(false);

  const vitrinUrl = portfolioOverview?.portfolio_vitrin_url || `${typeof window !== 'undefined' ? window.location.origin : ''}/v/${portfolioSlug || 'vitrin'}`;

  const haptic = (type: 'light' | 'medium' | 'heavy' | 'success' | 'warning' | 'error' = 'light') => {
    try {
      if (type === 'success' || type === 'warning' || type === 'error') {
        window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred(type);
      } else {
        window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(type);
      }
    } catch {
      // Ignored if not in TMA
    }
  };

  useEffect(() => {
    const initTma = async () => {
      try {
        if (window.Telegram?.WebApp) {
          window.Telegram.WebApp.ready();
          window.Telegram.WebApp.expand();
        }

        const tg = window.Telegram?.WebApp;
        let initData = tg?.initData || '';

        // Extract from URL hash or query if not populated on window yet
        if (!initData && window.location.hash.includes('tgWebAppData=')) {
          const hashParams = new URLSearchParams(window.location.hash.substring(1));
          initData = hashParams.get('tgWebAppData') || '';
        }
        if (!initData && window.location.search.includes('tgWebAppData=')) {
          const searchParams = new URLSearchParams(window.location.search);
          initData = searchParams.get('tgWebAppData') || '';
        }

        // Fallback for development browser testing
        if (!initData) {
          const urlParams = new URLSearchParams(window.location.search);
          const devMock = urlParams.get('mock_tg') || localStorage.getItem('mock_tg');
          if (devMock) {
            initData = `mock_telegram_${devMock}`;
          }
        }

        if (!initData) {
          // If already logged in to Dashboard via localStorage token, load CRM directly
          const existingToken = localStorage.getItem('token');
          if (existingToken) {
            const currentUserName = localStorage.getItem('user_name') || 'Agent / Admin';
            setAgentName(currentUserName);
            await fetchAllData();
            setLoading(false);
            return;
          }
          setAuthError('Zəhmət olmasa bu tətbiqi Telegram Bot menyusu daxilində və ya İdarəetmə Panelinə daxil olaraq açın.');
          setLoading(false);
          return;
        }

        // Authenticate with backend and check feature_crm access
        const res = await api.post('/auth/telegram-webapp', { init_data: initData });
        const authData = res.data;
        
        localStorage.setItem('token', authData.access_token);
        localStorage.setItem('user_name', authData.user_name);
        setAgentName(authData.tenant_name || authData.user_name);

        const loadedItems = await fetchAllData();

        // Check if opened with startapp param (e.g. deal_123 or port_456 or tab=portfolio)
        const currentUrlParams = new URLSearchParams(window.location.search);
        const currentHashParams = new URLSearchParams(window.location.hash.substring(1));
        const requestedTab = currentUrlParams.get('tab') || currentHashParams.get('tab');
        const startParam = tg?.initDataUnsafe?.start_param;

        if (requestedTab === 'portfolio' || startParam === 'portfolio') {
          setActiveTab('portfolio');
        } else if (requestedTab === 'reminders' || startParam === 'reminders') {
          setActiveTab('reminders');
        }

        const editParam = currentUrlParams.get('edit') || currentHashParams.get('edit');
        if (editParam) {
          setActiveTab('portfolio');
          const portId = parseInt(editParam);
          const found = loadedItems.find((p: any) => p.id === portId);
          if (found) {
            openEditPortfolioModal(found);
          }
        } else if (startParam && startParam.startsWith('port_')) {
          setActiveTab('portfolio');
          const portId = parseInt(startParam.replace('port_', ''));
          const found = loadedItems.find((p: any) => p.id === portId);
          if (found) {
            openEditPortfolioModal(found);
          }
        } else if (startParam && startParam.startsWith('deal_')) {
          const dealId = parseInt(startParam.replace('deal_', ''));
          if (dealId) {
            try {
              const dRes = await api.get(`/crm/deals/${dealId}`);
              if (dRes.data) {
                openDealModal(dRes.data);
              }
            } catch (err) {
              console.error('Failed to open deep-linked deal:', err);
            }
          }
        }
      } catch (err: any) {
        console.error('TMA Init error:', err);
        setAuthError(err.response?.data?.detail || 'Telegram ilə autentifikasiya xətası baş verdi.');
      } finally {
        setLoading(false);
      }
    };

    initTma();
  }, []);

  const fetchAllData = async (): Promise<PortfolioListingItem[]> => {
    try {
      const [dealsRes, clientsRes, statsRes, portRes, remindersRes] = await Promise.all([
        api.get('/crm/deals').catch(() => ({ data: [] })),
        api.get('/crm/clients').catch(() => ({ data: [] })),
        api.get('/crm/stats').catch(() => ({ data: null })),
        api.get('/portfolio').catch(() => ({ data: null })),
        api.get('/crm/reminders').catch(() => ({ data: [] })),
      ]);
      setDeals(dealsRes.data || []);
      setClients(clientsRes.data || []);
      setReminders(remindersRes.data || []);
      if (statsRes.data) setStats(statsRes.data);
      if (portRes.data) {
        setPortfolioOverview(portRes.data);
        const items = portRes.data.items || [];
        setPortfolioItems(items);
        setPortfolioLimit(portRes.data.portfolio_limit || 25);
        setPortfolioActiveCount(portRes.data.active_count || 0);
        if (portRes.data.portfolio_slug) {
          setPortfolioSlug(portRes.data.portfolio_slug);
        }
        return items;
      }
      return [];
    } catch (err) {
      console.error('Failed to fetch CRM data:', err);
      return [];
    }
  };

  const handleSaveDomain = async () => {
    if (!domainInput.trim()) return;
    setDomainSaving(true);
    try {
      await api.put('/portfolio/domain', {
        custom_domain: domainInput.trim(),
        custom_domain_enabled: domainEnabled,
        enabled: domainEnabled,
        activate_addon: true,
      });
      haptic('success');
      setCopiedToast('Domen qeydə alındı və ödəniş yaradıldı! 🌐');
      setTimeout(() => setCopiedToast(null), 3000);
      await fetchAllData();
      setShowDomainModal(false);
    } catch (err: any) {
      haptic('error');
      alert(err.response?.data?.detail || 'Domeni yadda saxlamaq mümkün olmadı');
    } finally {
      setDomainSaving(false);
    }
  };

  const handleVerifyDomain = async () => {
    setDomainVerifying(true);
    setDomainVerifyResult(null);
    try {
      const res = await api.post('/portfolio/domain/verify');
      const isVerified = Boolean(res.data?.verified ?? res.data?.success);
      haptic(isVerified ? 'success' : 'warning');
      setDomainVerifyResult({
        ...res.data,
        verified: isVerified,
      });
      if (isVerified) {
        await fetchAllData();
      }
    } catch (err: any) {
      haptic('error');
      setDomainVerifyResult({
        verified: false,
        message: err.response?.data?.detail || 'Yoxlama zamanı xəta baş verdi',
        dns_detected: false,
      });
    } finally {
      setDomainVerifying(false);
    }
  };

  const openEditPortfolioModal = (item: PortfolioListingItem) => {
    haptic('light');
    setSelectedPortfolioItem(item);
    setIsNewPortfolioModal(false);
    setEditPortTitle(item.title || '');
    setEditPortPrice(item.price ? String(item.price) : '');
    setEditPortCurrency(item.currency || 'AZN');
    setEditPortPriceUsd(item.price_usd ? String(item.price_usd) : '');
    setEditPortDescription(item.description || '');
    setEditPortRooms(item.rooms !== undefined && item.rooms !== null ? String(item.rooms) : '');
    setEditPortArea(item.area_sqm !== undefined && item.area_sqm !== null ? String(item.area_sqm) : '');
    setEditPortFloor(item.floor !== undefined && item.floor !== null ? String(item.floor) : '');
    setEditPortTotalFloors(item.total_floors !== undefined && item.total_floors !== null ? String(item.total_floors) : '');
    setEditPortDistrict(item.district || '');
    setEditPortMetro(item.metro_station || '');
    setEditPortAddress(item.address || '');
    setEditPortOfferType(item.offer_type || 'sale');
    setEditPortBuildingType(item.building_type || 'new_building');
    setEditPortPropertyType(item.property_type || 'apartment');
    setEditPortContactName(item.contact_name || '');
    setEditPortContactPhone(item.contact_phone || '');
    setEditPortNotes(item.notes || '');
    setEditPortStatus(item.status || 'active');
    setEditPortIsActive(item.is_active ?? true);
    setEditPortPhotos(Array.isArray(item.photos) ? [...item.photos] : []);
    setNewPhotoInput('');
  };

  const openNewPortfolioModal = () => {
    haptic('light');
    setSelectedPortfolioItem(null);
    setIsNewPortfolioModal(true);
    setEditPortTitle('');
    setEditPortPrice('');
    setEditPortCurrency('AZN');
    setEditPortPriceUsd('');
    setEditPortDescription('');
    setEditPortRooms('');
    setEditPortArea('');
    setEditPortFloor('');
    setEditPortTotalFloors('');
    setEditPortDistrict('');
    setEditPortMetro('');
    setEditPortAddress('');
    setEditPortOfferType('sale');
    setEditPortBuildingType('new_building');
    setEditPortPropertyType('apartment');
    setEditPortContactName(agentName || '');
    setEditPortContactPhone(agentPhone || '');
    setEditPortNotes('');
    setEditPortStatus('active');
    setEditPortIsActive(true);
    setEditPortPhotos([]);
    setNewPhotoInput('');
  };

  const closePortfolioModal = () => {
    setSelectedPortfolioItem(null);
    setIsNewPortfolioModal(false);
  };

  const handleAddPhoto = () => {
    const url = newPhotoInput.trim();
    if (url) {
      setEditPortPhotos(prev => [...prev, url]);
      setNewPhotoInput('');
    }
  };

  const handleRemovePhoto = (idx: number) => {
    setEditPortPhotos(prev => prev.filter((_, i) => i !== idx));
  };

  const handleSavePortfolio = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editPortTitle.trim()) {
      alert('Zəhmət olmasa elanın başlığını daxil edin.');
      return;
    }
    const priceNum = parseFloat(editPortPrice);
    if (isNaN(priceNum) || priceNum <= 0) {
      alert('Zəhmət olmasa düzgün qiymət daxil edin.');
      return;
    }

    setSavingPortfolio(true);
    haptic('medium');

    const payload = {
      title: editPortTitle.trim(),
      price: priceNum,
      currency: editPortCurrency,
      price_usd: editPortPriceUsd ? parseFloat(editPortPriceUsd) : undefined,
      description: editPortDescription.trim() || undefined,
      rooms: editPortRooms ? parseInt(editPortRooms) : undefined,
      area_sqm: editPortArea ? parseFloat(editPortArea) : undefined,
      floor: editPortFloor ? parseInt(editPortFloor) : undefined,
      total_floors: editPortTotalFloors ? parseInt(editPortTotalFloors) : undefined,
      district: editPortDistrict.trim() || undefined,
      metro_station: editPortMetro.trim() || undefined,
      address: editPortAddress.trim() || undefined,
      offer_type: editPortOfferType,
      building_type: editPortBuildingType,
      property_type: editPortPropertyType,
      contact_name: editPortContactName.trim() || undefined,
      contact_phone: editPortContactPhone.trim() || undefined,
      notes: editPortNotes.trim() || undefined,
      status: editPortStatus,
      is_active: editPortIsActive,
      photos: editPortPhotos,
    };

    try {
      if (selectedPortfolioItem) {
        const res = await api.put(`/portfolio/${selectedPortfolioItem.id}`, payload);
        setPortfolioItems(prev => prev.map(p => p.id === selectedPortfolioItem.id ? res.data : p));
      } else {
        const res = await api.post('/portfolio', payload);
        setPortfolioItems(prev => [res.data, ...prev]);
        setPortfolioActiveCount(c => c + 1);
      }
      closePortfolioModal();
      await fetchAllData();
      triggerToast('Elan uğurla yadda saxlanıldı! ✅');
    } catch (err: any) {
      console.error('Failed to save portfolio item:', err);
      alert(err.response?.data?.detail || 'Elan saxlanılarkən xəta baş verdi.');
    } finally {
      setSavingPortfolio(false);
    }
  };

  const handleDeletePortfolioItem = async (id: number) => {
    haptic('heavy');
    if (!window.confirm('Bu elanı portfelinizdən silmək istədiyinizə əminsiniz? (Portfel limiti dərhal boşalacaq)')) {
      return;
    }
    try {
      await api.delete(`/portfolio/${id}`);
      setPortfolioItems(prev => prev.filter(p => p.id !== id));
      setPortfolioActiveCount(c => Math.max(0, c - 1));
      if (selectedPortfolioItem?.id === id) {
        closePortfolioModal();
      }
      triggerToast('Elan portfeldən silindi və yuva azad olundu 🗑️');
    } catch (err) {
      console.error('Failed to delete portfolio item:', err);
      alert('Elan silinərkən xəta baş verdi.');
    }
  };

  const triggerToast = (msg: string) => {
    setCopiedToast(msg);
    setTimeout(() => setCopiedToast(null), 2500);
  };

  const copyToClipboard = (text: string, label: string = 'Link kopyalandı!') => {
    haptic('medium');
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text);
    } else {
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
    triggerToast(label);
  };

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

  const openDealModal = (deal: CrmDeal) => {
    haptic('light');
    setSelectedDeal(deal);
    setEditStage(deal.stage);
    setEditClientId(deal.client_id || '');
    setEditOfferPrice(deal.custom_offer_price ? String(deal.custom_offer_price) : '');
    setEditCommission(deal.commission_amount ? String(deal.commission_amount) : '');
    setEditNotes(deal.private_notes || '');
    setEditViewingAt(deal.scheduled_viewing_at ? deal.scheduled_viewing_at.slice(0, 16) : '');
  };

  const handleSaveDeal = async () => {
    if (!selectedDeal) return;
    setSavingDeal(true);
    haptic('medium');
    try {
      const payload: any = {
        stage: editStage,
        client_id: editClientId ? Number(editClientId) : null,
        custom_offer_price: editOfferPrice ? parseFloat(editOfferPrice) : null,
        commission_amount: editCommission ? parseFloat(editCommission) : null,
        private_notes: editNotes,
        scheduled_viewing_at: editViewingAt ? new Date(editViewingAt).toISOString() : null,
      };
      const res = await api.patch(`/crm/deals/${selectedDeal.id}`, payload);
      setDeals(prev => prev.map(d => d.id === selectedDeal.id ? res.data : d));
      setSelectedDeal(null);
      await fetchAllData();
    } catch (err) {
      console.error('Failed to save deal:', err);
      alert('Yadda saxlanılarkən xəta baş verdi.');
    } finally {
      setSavingDeal(false);
    }
  };

  const handleDeleteDeal = async (dealId: number) => {
    haptic('heavy');
    if (!window.confirm('Bu elanı CRM-dən silmək istədiyinizə əminsiniz?')) {
      return;
    }
    try {
      await api.delete(`/crm/deals/${dealId}`);
      setDeals(prev => prev.filter(d => d.id !== dealId));
      if (selectedDeal?.id === dealId) {
        setSelectedDeal(null);
      }
      setStats(prev => prev ? {
        ...prev,
        total_deals: Math.max(0, prev.total_deals - 1)
      } : null);
      await fetchAllData();
    } catch (err) {
      console.error('Failed to delete deal:', err);
      alert('Elan silinərkən xəta baş verdi.');
    }
  };

  const handleDeleteClient = async (clientId: number) => {
    haptic('heavy');
    if (!window.confirm('Bu müştərini silmək istədiyinizə əminsiniz?')) {
      return;
    }
    try {
      await api.delete(`/crm/clients/${clientId}`);
      setClients(prev => prev.filter(c => c.id !== clientId));
      await fetchAllData();
    } catch (err) {
      console.error('Failed to delete client:', err);
      alert('Müştəri silinərkən xəta baş verdi.');
    }
  };

  const handleCreateClient = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newClientName.trim()) return;
    setSavingClient(true);
    haptic('medium');
    try {
      const payload = {
        name: newClientName.trim(),
        phone: newClientPhone.trim() || undefined,
        whatsapp_number: newClientPhone.trim() || undefined,
        client_type: newClientType,
        budget_max: newClientBudget ? parseFloat(newClientBudget) : undefined,
        notes: newClientNotes.trim() || undefined,
      };
      const res = await api.post('/crm/clients', payload);
      setClients(prev => [res.data, ...prev]);
      setShowNewClientModal(false);
      setNewClientName('');
      setNewClientPhone('');
      setNewClientBudget('');
      setNewClientNotes('');
      if (selectedDeal) {
        setEditClientId(res.data.id);
      }
    } catch (err) {
      console.error('Failed to create client:', err);
      alert('Müştəri yaradılarkən xəta baş verdi.');
    } finally {
      setSavingClient(false);
    }
  };

  const shareToClientWhatsApp = (deal: CrmDeal) => {
    haptic('medium');
    const priceText = deal.custom_offer_price ? `${deal.custom_offer_price} AZN` : `${deal.listing_price} ${deal.listing_currency}`;
    const message = `Salam! Sizin üçün uyğun əmlak təklifi:\n\n🏠 *${deal.listing_title}*\n💰 *Qiymət:* ${priceText}\n📍 *Məkan:* ${deal.listing_location || 'Bakı'}\n\nƏtraflı məlumat və baxış təyin etmək üçün mənimlə əlaqə saxlaya bilərsiniz.`;
    
    let targetPhone = deal.client_phone || '';
    targetPhone = targetPhone.replace(/\D/g, '');
    if (targetPhone.startsWith('0')) {
      targetPhone = '994' + targetPhone.slice(1);
    } else if (!targetPhone.startsWith('994') && targetPhone.length === 9) {
      targetPhone = '994' + targetPhone;
    }

    const waUrl = targetPhone 
      ? `https://wa.me/${targetPhone}?text=${encodeURIComponent(message)}`
      : `https://wa.me/?text=${encodeURIComponent(message)}`;
    
    window.open(waUrl, '_blank');
  };

  // --- REMINDER HELPERS & HANDLERS ---
  const toLocalDatetimeInput = (isoOrDate?: string | Date | null): string => {
    const d = isoOrDate ? (typeof isoOrDate === 'string' ? new Date(isoOrDate) : isoOrDate) : new Date();
    if (isNaN(d.getTime())) return '';
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };

  const getPresetLocalDatetime = (dayOffset: number, hour: number, minute: number): string => {
    const d = new Date();
    d.setDate(d.getDate() + dayOffset);
    d.setHours(hour, minute, 0, 0);
    return toLocalDatetimeInput(d);
  };

  const formatAZTDate = (isoStr?: string | null): string => {
    if (!isoStr) return '';
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return isoStr;
      const months = ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'İyn', 'İyl', 'Avq', 'Sen', 'Okt', 'Noy', 'Dek'];
      const day = d.getDate();
      const month = months[d.getMonth()];
      const hour = String(d.getHours()).padStart(2, '0');
      const minute = String(d.getMinutes()).padStart(2, '0');
      return `${day} ${month}, ${hour}:${minute}`;
    } catch {
      return isoStr;
    }
  };

  const openNewReminderModal = (prefill?: {
    clientId?: number;
    dealId?: number;
    title?: string;
    type?: 'viewing' | 'call' | 'follow_up' | 'notary' | 'other';
  }) => {
    haptic('light');
    setSelectedReminder(null);
    setReminderTitle(prefill?.title || (prefill?.type === 'call' ? 'Müştəri ilə zəng' : 'Mənzilə baxış'));
    setReminderType(prefill?.type || 'viewing');
    const defaultTime = new Date();
    defaultTime.setHours(defaultTime.getHours() + 2, 0, 0, 0);
    setReminderDueAt(toLocalDatetimeInput(defaultTime));
    setReminderLeadMinutes(60);
    setReminderClientId(prefill?.clientId || '');
    setReminderDealId(prefill?.dealId || '');
    setReminderNotes('');
    setReminderStatus('pending');
    setShowReminderModal(true);
  };

  const openEditReminderModal = (reminder: CrmReminderItem) => {
    haptic('light');
    setSelectedReminder(reminder);
    setReminderTitle(reminder.title);
    setReminderType(reminder.reminder_type);
    setReminderDueAt(toLocalDatetimeInput(reminder.due_at));
    setReminderLeadMinutes(reminder.remind_before_minutes ?? 60);
    setReminderClientId(reminder.client_id || '');
    setReminderDealId(reminder.deal_id || '');
    setReminderNotes(reminder.notes || '');
    setReminderStatus(reminder.status || 'pending');
    setShowReminderModal(true);
  };

  const handleSaveReminder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reminderTitle.trim() || !reminderDueAt) {
      alert('Zəhmət olmasa xatırlatma başlığını və vaxtını qeyd edin.');
      return;
    }
    setSavingReminder(true);
    haptic('medium');
    try {
      const payload = {
        title: reminderTitle.trim(),
        reminder_type: reminderType,
        due_at: new Date(reminderDueAt).toISOString(),
        remind_before_minutes: Number(reminderLeadMinutes),
        client_id: reminderClientId ? Number(reminderClientId) : null,
        deal_id: reminderDealId ? Number(reminderDealId) : null,
        notes: reminderNotes.trim() || null,
        status: reminderStatus,
      };

      if (selectedReminder) {
        const res = await api.put(`/crm/reminders/${selectedReminder.id}`, payload);
        setReminders(prev => prev.map(r => r.id === selectedReminder.id ? res.data : r));
        setCopiedToast('Xatırlatma yeniləndi! ⏰');
      } else {
        const res = await api.post('/crm/reminders', payload);
        setReminders(prev => [res.data, ...prev]);
        setCopiedToast('Yeni xatırlatma təyin edildi! ⏰');
      }
      setTimeout(() => setCopiedToast(null), 3000);
      setShowReminderModal(false);
      await fetchAllData();
    } catch (err: any) {
      console.error('Failed to save reminder:', err);
      alert(err.response?.data?.detail || 'Xatırlatmanı yadda saxlamaq mümkün olmadı.');
    } finally {
      setSavingReminder(false);
    }
  };

  const handleToggleReminderStatus = async (reminder: CrmReminderItem) => {
    const newStatus = reminder.status === 'completed' ? 'pending' : 'completed';
    haptic(newStatus === 'completed' ? 'success' : 'light');
    try {
      const res = await api.put(`/crm/reminders/${reminder.id}`, {
        status: newStatus,
      });
      setReminders(prev => prev.map(r => r.id === reminder.id ? res.data : r));
      if (newStatus === 'completed') {
        setCopiedToast('Xatırlatma tamamlandı! ✅');
        setTimeout(() => setCopiedToast(null), 2500);
      }
    } catch (err) {
      console.error('Failed to toggle reminder status:', err);
    }
  };

  const handleDeleteReminder = async (reminderId: number) => {
    haptic('heavy');
    if (!window.confirm('Bu xatırlatmanı silmək istədiyinizə əminsiniz?')) {
      return;
    }
    try {
      await api.delete(`/crm/reminders/${reminderId}`);
      setReminders(prev => prev.filter(r => r.id !== reminderId));
      setCopiedToast('Xatırlatma silindi');
      setTimeout(() => setCopiedToast(null), 2000);
    } catch (err: any) {
      console.error('Failed to delete reminder:', err);
      alert(err.response?.data?.detail || 'Xatırlatmanı silmək mümkün olmadı.');
    }
  };

  const activeRemindersCount = reminders.filter(r => r.status === 'pending' || r.status === 'notified').length;

  const filteredReminders = reminders.filter(r => {
    if (reminderFilter === 'pending') return r.status === 'pending' || r.status === 'notified';
    if (reminderFilter === 'completed') return r.status === 'completed';
    return true;
  });

  const filteredDeals = deals.filter(d => {
    if (selectedStage !== 'all' && d.stage !== selectedStage) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        d.listing_title.toLowerCase().includes(q) ||
        (d.client_name && d.client_name.toLowerCase().includes(q)) ||
        (d.listing_location && d.listing_location.toLowerCase().includes(q))
      );
    }
    return true;
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-white flex flex-col items-center justify-center p-6">
        <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-slate-400 font-medium">CRM yüklənir...</p>
      </div>
    );
  }

  if (authError) {
    return (
      <div className="min-h-screen bg-slate-950 text-white flex flex-col items-center justify-center p-6 text-center">
        <div className="w-16 h-16 rounded-full bg-rose-500/20 border border-rose-500/30 flex items-center justify-center mb-4">
          <AlertCircle className="w-8 h-8 text-rose-400" />
        </div>
        <h2 className="text-xl font-bold text-slate-100 mb-2">Telegram Girişi Tapılmadı</h2>
        <p className="text-slate-400 text-sm max-w-xs mb-6">{authError}</p>
        <button
          onClick={() => window.Telegram?.WebApp?.close()}
          className="px-6 py-2.5 rounded-xl bg-slate-800 text-slate-200 text-sm font-semibold border border-slate-700 hover:bg-slate-700"
        >
          Bağla
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 pb-20 select-none">
      {/* Top Header */}
      <div className="sticky top-0 z-20 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center shadow-md shadow-blue-500/20">
              <Briefcase className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-sm text-white leading-tight">Əmlak CRM Mini App</h1>
              <p className="text-[11px] text-blue-400 font-medium">{agentName}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {activeTab === 'portfolio' ? (
              <button
                onClick={() => { haptic('light'); openNewPortfolioModal(); }}
                className="flex items-center gap-1 bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold px-3 py-1.5 rounded-lg shadow-sm shadow-purple-600/20"
              >
                <Plus className="w-3.5 h-3.5" />
                Yeni Elan
              </button>
            ) : activeTab === 'reminders' ? (
              <button
                onClick={() => { haptic('light'); openNewReminderModal(); }}
                className="flex items-center gap-1 bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold px-3 py-1.5 rounded-lg shadow-sm shadow-purple-600/20"
              >
                <Plus className="w-3.5 h-3.5" />
                Xatırlatma
              </button>
            ) : (
              <button
                onClick={() => { haptic('light'); setShowNewClientModal(true); }}
                className="flex items-center gap-1 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-3 py-1.5 rounded-lg shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" />
                Müştəri
              </button>
            )}
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="grid grid-cols-5 gap-1 bg-slate-950/80 p-1 rounded-xl mt-3 border border-slate-800/80">
          <button
            onClick={() => { haptic('light'); setActiveTab('deals'); }}
            className={`py-1.5 text-[10px] sm:text-[11px] font-semibold rounded-lg transition-all truncate px-1 ${
              activeTab === 'deals' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            📋 Sövdə ({deals.length})
          </button>
          <button
            onClick={() => { haptic('light'); setActiveTab('clients'); }}
            className={`py-1.5 text-[10px] sm:text-[11px] font-semibold rounded-lg transition-all truncate px-1 ${
              activeTab === 'clients' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            👥 Müştəri ({clients.length})
          </button>
          <button
            onClick={() => { haptic('light'); setActiveTab('reminders'); }}
            className={`py-1.5 text-[10px] sm:text-[11px] font-semibold rounded-lg transition-all truncate px-1 ${
              activeTab === 'reminders' ? 'bg-purple-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            ⏰ Xatırlatma ({activeRemindersCount})
          </button>
          <button
            onClick={() => { haptic('light'); setActiveTab('portfolio'); }}
            className={`py-1.5 text-[10px] sm:text-[11px] font-semibold rounded-lg transition-all truncate px-1 ${
              activeTab === 'portfolio' ? 'bg-purple-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            🗂️ Portfel ({portfolioItems.length})
          </button>
          <button
            onClick={() => { haptic('light'); setActiveTab('stats'); }}
            className={`py-1.5 text-[10px] sm:text-[11px] font-semibold rounded-lg transition-all truncate px-1 ${
              activeTab === 'stats' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            📊 Statistika
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="p-4">
        {/* --- DEALS / PIPELINE TAB --- */}
        {activeTab === 'deals' && (
          <div>
            {/* Search and Stage Filters */}
            <div className="space-y-2 mb-4">
              <div className="relative">
                <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Elan və ya müştəri axtar..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none">
                <button
                  onClick={() => { haptic('light'); setSelectedStage('all'); }}
                  className={`px-3 py-1 rounded-lg text-xs font-medium whitespace-nowrap transition-all border ${
                    selectedStage === 'all'
                      ? 'bg-slate-200 text-slate-900 border-slate-200 font-semibold'
                      : 'bg-slate-900 text-slate-400 border-slate-800'
                  }`}
                >
                  Hamısı ({deals.length})
                </button>
                {STAGES.map(s => {
                  const count = deals.filter(d => d.stage === s.key).length;
                  return (
                    <button
                      key={s.key}
                      onClick={() => { haptic('light'); setSelectedStage(s.key); }}
                      className={`px-3 py-1 rounded-lg text-xs font-medium whitespace-nowrap transition-all border ${
                        selectedStage === s.key
                          ? 'bg-blue-600 text-white border-blue-500 font-semibold'
                          : 'bg-slate-900 text-slate-400 border-slate-800'
                      }`}
                    >
                      {s.label} ({count})
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Deals List */}
            {filteredDeals.length === 0 ? (
              <div className="text-center py-12 bg-slate-900/50 rounded-2xl border border-slate-800/80 p-6">
                <Briefcase className="w-12 h-12 text-slate-600 mx-auto mb-3 opacity-50" />
                <h3 className="text-sm font-semibold text-slate-300 mb-1">Hələ heç bir elan əlavə edilməyib</h3>
                <p className="text-xs text-slate-500 max-w-xs mx-auto mb-4">
                  Botda və ya WhatsApp-da <code className="bg-slate-800 px-1 py-0.5 rounded text-blue-400">/crm &lt;elan_id&gt;</code> yazaraq istənilən elanı bura köçürə bilərsiniz.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center justify-between px-1 text-[11px] text-slate-500">
                  <span>💡 Elanı silmək üçün <b>sola sürüşdürün</b></span>
                  <span>{filteredDeals.length} elan</span>
                </div>

                {filteredDeals.map(deal => {
                  const stageObj = STAGES.find(s => s.key === deal.stage) || STAGES[0];
                  return (
                    <SwipeableDealCard
                      key={deal.id}
                      deal={deal}
                      stageObj={stageObj}
                      onOpen={openDealModal}
                      onDelete={handleDeleteDeal}
                      onShareWhatsApp={shareToClientWhatsApp}
                      onAddReminder={(d) => openNewReminderModal({
                        dealId: d.id,
                        clientId: d.client_id || undefined,
                        title: `Baxış: ${d.listing_title}`,
                        type: 'viewing'
                      })}
                      haptic={haptic}
                    />
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* --- CLIENTS TAB --- */}
        {activeTab === 'clients' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">Müştəri Bazası</h2>
              <button
                onClick={() => { haptic('light'); setShowNewClientModal(true); }}
                className="text-xs text-blue-400 font-semibold hover:text-blue-300 flex items-center gap-1"
              >
                <Plus className="w-3.5 h-3.5" /> Yeni Əlavə Et
              </button>
            </div>

            {clients.length === 0 ? (
              <div className="text-center py-12 bg-slate-900/50 rounded-2xl border border-slate-800 p-6">
                <Users className="w-12 h-12 text-slate-600 mx-auto mb-3 opacity-50" />
                <h3 className="text-sm font-semibold text-slate-300 mb-1">Müştəri tapılmadı</h3>
                <p className="text-xs text-slate-500 mb-4">Alıcı və ya icarəçi müştərilərinizi bura qeyd edin.</p>
                <button
                  onClick={() => setShowNewClientModal(true)}
                  className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-4 py-2 rounded-xl"
                >
                  + İlk Müştərini Yarat
                </button>
              </div>
            ) : (
              <div className="space-y-2.5">
                {clients.map(client => (
                  <div
                    key={client.id}
                    className="bg-slate-900 border border-slate-800 rounded-xl p-3.5 flex items-center justify-between"
                  >
                    <div>
                      <div className="flex items-center gap-2 mb-0.5">
                        <h4 className="font-bold text-xs text-slate-100">{client.name}</h4>
                        <span className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.2 rounded">
                          {client.client_type === 'buyer' ? 'Alıcı' : 'İcarəçi'}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 font-mono">{client.phone || 'Nömrəsiz'}</p>
                      {client.budget_max && (
                        <p className="text-[10px] text-emerald-400 font-semibold mt-0.5">
                          Büdcə: {intFormat(client.budget_max)} AZN-dək
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => openNewReminderModal({ clientId: client.id, title: `${client.name} ilə əlaqə`, type: 'call' })}
                        className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center hover:bg-purple-500/20"
                        title="Xatırlatma və ya zəng planla"
                      >
                        <Clock className="w-4 h-4" />
                      </button>
                      {client.phone && (
                        <a
                          href={`https://wa.me/${client.phone.replace(/\D/g, '')}`}
                          target="_blank"
                          rel="noreferrer"
                          onClick={() => haptic('medium')}
                          className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center hover:bg-emerald-500/20"
                        >
                          <MessageSquare className="w-4 h-4" />
                        </a>
                      )}
                      <button
                        type="button"
                        onClick={() => handleDeleteClient(client.id)}
                        className="w-8 h-8 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center hover:bg-rose-500/20"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* --- REMINDERS & VIEWINGS TAB --- */}
        {activeTab === 'reminders' && (
          <div className="space-y-3">
            {/* Header / Info card */}
            <div className="bg-gradient-to-br from-indigo-950/40 via-slate-900 to-slate-900 border border-indigo-500/20 rounded-2xl p-3.5 shadow-sm">
              <div className="flex items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-xl bg-purple-500/20 border border-purple-500/30 flex items-center justify-center text-purple-400 shrink-0">
                    <Clock className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-xs font-bold text-white flex items-center gap-1.5">
                      Baxış və Zəng Xatırlatmaları
                    </h3>
                    <p className="text-[10px] text-slate-400">
                      Təyin etdiyiniz vaxtdan qabaq bot sizə xəbərdarlıq göndərəcək.
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => openNewReminderModal()}
                  className="bg-purple-600 hover:bg-purple-500 active:scale-95 text-white text-[11px] font-bold px-3 py-1.5 rounded-xl shadow-md shadow-purple-600/20 flex items-center gap-1 shrink-0"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Yeni
                </button>
              </div>

              {/* Status Filters */}
              <div className="flex gap-1.5 pt-1">
                <button
                  onClick={() => { haptic('light'); setReminderFilter('pending'); }}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all border ${
                    reminderFilter === 'pending'
                      ? 'bg-purple-600 text-white border-purple-500 shadow-sm'
                      : 'bg-slate-950/80 text-slate-400 border-slate-800'
                  }`}
                >
                  Gözləyən ({reminders.filter(r => r.status === 'pending' || r.status === 'notified').length})
                </button>
                <button
                  onClick={() => { haptic('light'); setReminderFilter('all'); }}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all border ${
                    reminderFilter === 'all'
                      ? 'bg-purple-600 text-white border-purple-500 shadow-sm'
                      : 'bg-slate-950/80 text-slate-400 border-slate-800'
                  }`}
                >
                  Hamısı ({reminders.length})
                </button>
                <button
                  onClick={() => { haptic('light'); setReminderFilter('completed'); }}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all border ${
                    reminderFilter === 'completed'
                      ? 'bg-purple-600 text-white border-purple-500 shadow-sm'
                      : 'bg-slate-950/80 text-slate-400 border-slate-800'
                  }`}
                >
                  Tamamlanan ({reminders.filter(r => r.status === 'completed').length})
                </button>
              </div>
            </div>

            {/* List */}
            {filteredReminders.length === 0 ? (
              <div className="text-center py-12 bg-slate-900/50 rounded-2xl border border-slate-800/80 p-6">
                <Clock className="w-12 h-12 text-slate-600 mx-auto mb-3 opacity-50" />
                <h3 className="text-sm font-semibold text-slate-300 mb-1">
                  {reminderFilter === 'completed' ? 'Tamamlanmış xatırlatma yoxdur' : 'Aktiv xatırlatma yoxdur'}
                </h3>
                <p className="text-xs text-slate-500 max-w-xs mx-auto mb-4">
                  Ev baxışı, müştəri zəngi və ya görüş planlaşdırın, vaxtından qabaq Telegram bot xatırlatsın.
                </p>
                <button
                  onClick={() => openNewReminderModal()}
                  className="bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold px-4 py-2 rounded-xl shadow-md shadow-purple-600/20"
                >
                  + İlk Xatırlatmanı Yarat
                </button>
              </div>
            ) : (
              <div className="space-y-2.5">
                {filteredReminders.map(rem => {
                  const meta = REMINDER_TYPE_META[rem.reminder_type] || REMINDER_TYPE_META.other;
                  const isCompleted = rem.status === 'completed';
                  const isNotified = rem.status === 'notified';

                  return (
                    <div
                      key={rem.id}
                      className={`bg-slate-900 border rounded-2xl p-3.5 transition-all ${
                        isCompleted
                          ? 'border-slate-800/60 opacity-60 bg-slate-900/40'
                          : isNotified
                          ? 'border-amber-500/40 shadow-sm'
                          : 'border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        {/* Checkbox button */}
                        <button
                          type="button"
                          onClick={() => handleToggleReminderStatus(rem)}
                          className={`mt-0.5 w-6 h-6 rounded-lg flex items-center justify-center transition-colors shrink-0 ${
                            isCompleted
                              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                              : 'bg-slate-950 border border-slate-700 text-transparent hover:border-purple-500'
                          }`}
                          title={isCompleted ? 'Yenidən aktiv et' : 'Tamamla'}
                        >
                          <Check className={`w-3.5 h-3.5 ${isCompleted ? 'opacity-100 text-emerald-400' : 'opacity-0'}`} />
                        </button>

                        {/* Card body */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-1.5 mb-1 flex-wrap">
                            <div className="flex items-center gap-1.5">
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${meta.bg} ${meta.text} ${meta.border}`}>
                                {meta.icon} {meta.label}
                              </span>
                              {isNotified && (
                                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                                  <Bell className="w-2.5 h-2.5" /> Bildirildi
                                </span>
                              )}
                              {isCompleted && (
                                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                                  ✓ Tamamlandı
                                </span>
                              )}
                            </div>

                            <div className="flex items-center gap-1">
                              <button
                                type="button"
                                onClick={() => openEditReminderModal(rem)}
                                className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800"
                                title="Redaktə et"
                              >
                                <Edit3 className="w-3.5 h-3.5" />
                              </button>
                              <button
                                type="button"
                                onClick={() => handleDeleteReminder(rem.id)}
                                className="p-1 text-slate-500 hover:text-rose-400 rounded hover:bg-rose-500/10"
                                title="Sil"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </div>

                          <h4 className={`text-xs font-bold text-slate-100 mb-1.5 ${isCompleted ? 'line-through text-slate-400' : ''}`}>
                            {rem.title}
                          </h4>

                          {/* Time & Alert info */}
                          <div className="flex items-center gap-3 text-[11px] text-purple-300 mb-2 flex-wrap">
                            <span className="flex items-center gap-1 font-semibold">
                              <Calendar className="w-3 h-3 text-purple-400" />
                              {formatAZTDate(rem.due_at)}
                            </span>
                            <span className="flex items-center gap-1 text-[10px] text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                              <Bell className="w-2.5 h-2.5 text-slate-400" />
                              {rem.remind_before_minutes === 0 ? 'Vaxtında' : `${rem.remind_before_minutes} dəq əvvəl`}
                            </span>
                          </div>

                          {/* Linked Client */}
                          {rem.client_name && (
                            <div className="flex items-center justify-between gap-2 bg-slate-950/60 border border-slate-800/80 rounded-xl px-2.5 py-1.5 mb-1.5 text-[11px]">
                              <span className="text-slate-300 font-medium flex items-center gap-1 truncate">
                                <Users className="w-3 h-3 text-blue-400" />
                                {rem.client_name}
                              </span>
                              <div className="flex items-center gap-1.5 shrink-0">
                                {rem.client_phone && (
                                  <>
                                    <a
                                      href={`tel:${rem.client_phone}`}
                                      className="p-1 rounded bg-blue-500/10 text-blue-400 hover:bg-blue-500/20"
                                      title="Zəng et"
                                    >
                                      <Phone className="w-3 h-3" />
                                    </a>
                                    <a
                                      href={`https://wa.me/${rem.client_phone.replace(/\D/g, '')}`}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="p-1 rounded bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
                                      title="WhatsApp"
                                    >
                                      <MessageSquare className="w-3 h-3" />
                                    </a>
                                  </>
                                )}
                              </div>
                            </div>
                          )}

                          {/* Linked Deal */}
                          {rem.deal_title && (
                            <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl px-2.5 py-1.5 mb-1.5 text-[11px] flex items-center justify-between">
                              <span className="text-slate-300 font-medium flex items-center gap-1 truncate">
                                <Briefcase className="w-3 h-3 text-purple-400" />
                                {rem.deal_title}
                              </span>
                              {rem.deal_price && (
                                <span className="text-emerald-400 font-bold shrink-0 ml-2">
                                  {intFormat(rem.deal_price)} AZN
                                </span>
                              )}
                            </div>
                          )}

                          {/* Notes */}
                          {rem.notes && (
                            <p className="text-[10px] text-slate-400 italic bg-slate-950/40 p-2 rounded-lg border border-slate-800/50 mt-1">
                              💬 {rem.notes}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* --- PORTFOLIO TAB --- */}
        {activeTab === 'portfolio' && (
          <div className="space-y-3">
            {/* Header: Limit Quota & Vitrin URL Banner */}
            <div className="bg-gradient-to-br from-purple-950/50 via-slate-900 to-slate-900 border border-purple-500/30 rounded-2xl p-4 shadow-lg">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-2">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-xl bg-purple-500/20 border border-purple-500/30 flex items-center justify-center text-purple-400 shrink-0">
                    <Globe className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <h3 className="text-xs font-bold text-white">Rəqəmsal Vitrinim</h3>
                      {portfolioOverview?.custom_domain_info?.source === 'agent' && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-semibold border border-indigo-500/30">
                          🌐 Fərdi Domen
                        </span>
                      )}
                      {portfolioOverview?.custom_domain_info?.source === 'reseller' && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/30">
                          🏢 Reseller Domeni
                        </span>
                      )}
                    </div>
                    <p className="text-[10px] text-purple-300 font-mono truncate max-w-xs">
                      {vitrinUrl}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 self-end sm:self-center">
                  <button
                    onClick={() => {
                      setDomainInput(portfolioOverview?.custom_domain_info?.agent_custom_domain || '');
                      setDomainEnabled(portfolioOverview?.custom_domain_info?.agent_custom_domain_enabled ?? true);
                      setDomainVerifyResult(null);
                      setShowDomainModal(true);
                      haptic('light');
                    }}
                    className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/40 text-indigo-200 text-xs font-semibold transition-all"
                    title="Domen Tənzimləmələri"
                  >
                    <Settings className="w-3.5 h-3.5" />
                    <span>Domen</span>
                  </button>
                  <button
                    onClick={() => copyToClipboard(vitrinUrl, 'Vitrin linki kopyalandı! 📋')}
                    className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-purple-600/30 hover:bg-purple-600/50 border border-purple-500/40 text-purple-200 text-xs font-semibold transition-all"
                  >
                    <Copy className="w-3.5 h-3.5" />
                    Kopyala
                  </button>
                  <a
                    href={vitrinUrl}
                    target="_blank"
                    rel="noreferrer"
                    onClick={() => haptic('medium')}
                    className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-all"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    Aç
                  </a>
                </div>
              </div>

              {/* Limit Quota Progress */}
              <div className="mt-3 pt-3 border-t border-purple-500/20">
                <div className="flex justify-between items-center text-[11px] mb-1.5">
                  <span className="text-slate-400">Portfel Limiti:</span>
                  <span className="font-bold text-white font-mono">
                    {portfolioActiveCount} / {portfolioLimit} aktiv elan
                    <span className="text-purple-400 font-normal ml-1.5">
                      ({Math.max(0, portfolioLimit - portfolioActiveCount)} boş yuva)
                    </span>
                  </span>
                </div>
                <div className="w-full h-2 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                  <div
                    className={`h-full transition-all rounded-full ${
                      portfolioActiveCount >= portfolioLimit ? 'bg-rose-500' : 'bg-gradient-to-r from-purple-500 to-indigo-500'
                    }`}
                    style={{ width: `${Math.min(100, (portfolioActiveCount / Math.max(1, portfolioLimit)) * 100)}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Search & Filter Bar */}
            <div className="space-y-2">
              <div className="relative">
                <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Portfeldə elan axtar (başlıq, rayon, metro)..."
                  value={portfolioSearch}
                  onChange={e => setPortfolioSearch(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none">
                <button
                  onClick={() => { haptic('light'); setPortfolioFilter('all'); }}
                  className={`px-3 py-1 rounded-lg text-xs font-medium whitespace-nowrap transition-all border ${
                    portfolioFilter === 'all'
                      ? 'bg-purple-600 text-white border-purple-500 font-semibold'
                      : 'bg-slate-900 text-slate-400 border-slate-800'
                  }`}
                >
                  Hamısı ({portfolioItems.length})
                </button>
                <button
                  onClick={() => { haptic('light'); setPortfolioFilter('active'); }}
                  className={`px-3 py-1 rounded-lg text-xs font-medium whitespace-nowrap transition-all border ${
                    portfolioFilter === 'active'
                      ? 'bg-emerald-600 text-white border-emerald-500 font-semibold'
                      : 'bg-slate-900 text-slate-400 border-slate-800'
                  }`}
                >
                  Aktiv ({portfolioItems.filter(p => p.is_active && p.status !== 'sold').length})
                </button>
                <button
                  onClick={() => { haptic('light'); setPortfolioFilter('sold'); }}
                  className={`px-3 py-1 rounded-lg text-xs font-medium whitespace-nowrap transition-all border ${
                    portfolioFilter === 'sold'
                      ? 'bg-amber-600 text-white border-amber-500 font-semibold'
                      : 'bg-slate-900 text-slate-400 border-slate-800'
                  }`}
                >
                  Satıldı / Deaktiv ({portfolioItems.filter(p => !p.is_active || p.status === 'sold').length})
                </button>
              </div>
            </div>

            {/* Portfolio Listings List */}
            {(() => {
              const filtered = portfolioItems.filter(p => {
                if (portfolioFilter === 'active' && (!p.is_active || p.status === 'sold')) return false;
                if (portfolioFilter === 'sold' && (p.is_active && p.status !== 'sold')) return false;
                if (portfolioSearch.trim()) {
                  const q = portfolioSearch.toLowerCase();
                  return (
                    p.title.toLowerCase().includes(q) ||
                    (p.district && p.district.toLowerCase().includes(q)) ||
                    (p.metro_station && p.metro_station.toLowerCase().includes(q)) ||
                    String(p.id).includes(q)
                  );
                }
                return true;
              });

              if (filtered.length === 0) {
                return (
                  <div className="text-center py-12 bg-slate-900/50 rounded-2xl border border-slate-800 p-6">
                    <FolderPlus className="w-12 h-12 text-slate-600 mx-auto mb-3 opacity-50" />
                    <h3 className="text-sm font-semibold text-slate-300 mb-1">Portfel elanı tapılmadı</h3>
                    <p className="text-xs text-slate-500 mb-4 max-w-xs mx-auto">
                      Telegram botdan <code className="text-purple-400 bg-purple-950/50 px-1 py-0.5 rounded">/portfel &lt;id&gt;</code> göndərərək və ya birbaşa düymə ilə yeni elan əlavə edə bilərsiniz.
                    </p>
                    <button
                      onClick={() => openNewPortfolioModal()}
                      className="bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold px-4 py-2 rounded-xl shadow-md shadow-purple-600/20"
                    >
                      + Yeni Elan Əlavə Et
                    </button>
                  </div>
                );
              }

              return (
                <div className="space-y-3">
                  {filtered.map(item => {
                    const firstPhoto = Array.isArray(item.photos) && item.photos.length > 0 ? item.photos[0] : null;
                    const cleanLink = item.share_url || `${vitrinUrl}/${item.id}`;

                    return (
                      <div
                        key={item.id}
                        className="bg-slate-900 border border-slate-800 rounded-2xl p-3.5 space-y-3 hover:border-slate-700 transition-all shadow-md"
                      >
                        <div className="flex gap-3">
                          {/* Image or Placeholder */}
                          <div className="w-20 h-20 rounded-xl bg-slate-950 border border-slate-800 overflow-hidden flex-shrink-0 relative">
                            {firstPhoto ? (
                              <img
                                src={firstPhoto}
                                alt={item.title}
                                className="w-full h-full object-cover"
                                onError={(e) => { (e.target as any).style.display = 'none'; }}
                              />
                            ) : (
                              <div className="w-full h-full flex flex-col items-center justify-center text-slate-600">
                                <Home className="w-6 h-6" />
                              </div>
                            )}
                            {Array.isArray(item.photos) && item.photos.length > 1 && (
                              <span className="absolute bottom-1 right-1 bg-black/70 text-[9px] font-bold text-white px-1.5 py-0.5 rounded">
                                📷 {item.photos.length}
                              </span>
                            )}
                          </div>

                          {/* Info */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-1 mb-1">
                              <span className="text-[10px] font-mono text-purple-400 font-bold">#{item.id}</span>
                              <span
                                className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                                  item.status === 'sold'
                                    ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                                    : item.is_active
                                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                    : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                                }`}
                              >
                                {item.status === 'sold' ? 'Satıldı' : item.is_active ? 'Aktiv' : 'Deaktiv'}
                              </span>
                            </div>

                            <h4 className="text-xs font-bold text-white line-clamp-1 mb-1">{item.title}</h4>

                            <div className="flex items-center gap-1 text-sm font-black text-emerald-400">
                              {intFormat(item.price)} {item.currency || 'AZN'}
                              {item.price_usd && (
                                <span className="text-[10px] font-normal text-slate-400">(${intFormat(item.price_usd)})</span>
                              )}
                            </div>

                            <div className="flex items-center gap-2 text-[10px] text-slate-400 mt-1">
                              {item.rooms && <span>{item.rooms} otaq</span>}
                              {item.area_sqm && <span>• {item.area_sqm} m²</span>}
                              {item.district && <span>• {item.district}</span>}
                              {item.metro_station && <span>• 🚇 {item.metro_station}</span>}
                            </div>
                          </div>
                        </div>

                        {/* Card Action Buttons */}
                        <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between gap-2">
                          <button
                            type="button"
                            onClick={() => copyToClipboard(cleanLink, 'Təmiz elan linki kopyalandı! 🔗')}
                            className="flex items-center gap-1 bg-slate-950 hover:bg-slate-800 text-slate-300 text-[11px] font-semibold px-2.5 py-1.5 rounded-lg border border-slate-800 transition-all flex-1 justify-center"
                          >
                            <Share2 className="w-3.5 h-3.5 text-purple-400" />
                            Linki Kopyala
                          </button>

                          <button
                            type="button"
                            onClick={() => openEditPortfolioModal(item)}
                            className="flex items-center gap-1 bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 text-[11px] font-bold px-3 py-1.5 rounded-lg border border-purple-500/40 transition-all flex-1 justify-center"
                          >
                            <Edit3 className="w-3.5 h-3.5 text-purple-400" />
                            Redaktə Et
                          </button>

                          <button
                            type="button"
                            onClick={() => handleDeletePortfolioItem(item.id)}
                            className="w-8 h-8 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 flex items-center justify-center transition-all flex-shrink-0"
                            title="Portfeldən sil"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            })()}
          </div>
        )}

        {/* --- STATS TAB --- */}
        {activeTab === 'stats' && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
                <p className="text-[11px] text-slate-400 font-medium mb-1">Ümumi Sövdələr</p>
                <h3 className="text-2xl font-black text-white">{stats?.total_deals || 0}</h3>
              </div>
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
                <p className="text-[11px] text-slate-400 font-medium mb-1">Müştərilər</p>
                <h3 className="text-2xl font-black text-blue-400">{stats?.total_clients || 0}</h3>
              </div>
            </div>

            <div className="bg-gradient-to-tr from-emerald-950/40 to-slate-900 border border-emerald-500/30 rounded-2xl p-4">
              <p className="text-xs text-emerald-400 font-semibold mb-1">Qazanılmış Komissiya</p>
              <h2 className="text-3xl font-black text-emerald-300">
                {intFormat(stats?.total_won_commission || 0)} <span className="text-base font-bold text-emerald-500">AZN</span>
              </h2>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
              <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">Mərhələlər üzrə Bölgü</h3>
              <div className="space-y-2">
                {STAGES.map(s => {
                  const count = stats?.stage_counts?.[s.key] || 0;
                  return (
                    <div key={s.key} className="flex items-center justify-between text-xs py-1 border-b border-slate-800/60 last:border-0">
                      <span className="text-slate-400">{s.label}</span>
                      <span className="font-bold text-white bg-slate-800 px-2 py-0.5 rounded-full">{count}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* --- DEAL EDIT / VIEW MODAL --- */}
      {selectedDeal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-t-3xl sm:rounded-3xl w-full max-w-lg max-h-[90vh] flex flex-col shadow-2xl animate-in slide-in-from-bottom duration-200">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-slate-800">
              <div>
                <h3 className="text-sm font-bold text-white line-clamp-1">{selectedDeal.listing_title}</h3>
                <p className="text-[11px] text-emerald-400 font-bold">
                  Orijinal Qiymət: {intFormat(selectedDeal.listing_price)} {selectedDeal.listing_currency}
                </p>
              </div>
              <button
                onClick={() => { haptic('light'); setSelectedDeal(null); }}
                className="w-8 h-8 rounded-full bg-slate-800 text-slate-400 hover:text-white flex items-center justify-center"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-4 overflow-y-auto space-y-4 flex-1">
              {/* Stage Chips */}
              <div>
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
                  Status (Mərhələ)
                </label>
                <div className="grid grid-cols-3 gap-1.5">
                  {STAGES.map(s => (
                    <button
                      key={s.key}
                      type="button"
                      onClick={() => { haptic('light'); setEditStage(s.key); }}
                      className={`py-2 px-2 rounded-xl text-xs font-semibold border transition-all ${
                        editStage === s.key
                          ? 'bg-blue-600 text-white border-blue-500 shadow-md shadow-blue-500/20'
                          : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Client Selection */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    Müştəri
                  </label>
                  <button
                    type="button"
                    onClick={() => { haptic('light'); setShowNewClientModal(true); }}
                    className="text-[11px] text-blue-400 font-semibold"
                  >
                    + Yeni Müştəri
                  </button>
                </div>
                <select
                  value={editClientId}
                  onChange={e => setEditClientId(e.target.value ? Number(e.target.value) : '')}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-slate-100 focus:outline-none focus:border-blue-500"
                >
                  <option value="">-- Müştəri Seçilməyib --</option>
                  {clients.map(c => (
                    <option key={c.id} value={c.id}>
                      {c.name} {c.phone ? `(${c.phone})` : ''}
                    </option>
                  ))}
                </select>
              </div>

              {/* Pricing & Commission */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                    Təklif Qiyməti (AZN)
                  </label>
                  <input
                    type="number"
                    placeholder="Məs: 125000"
                    value={editOfferPrice}
                    onChange={e => setEditOfferPrice(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                    Komissiyam (AZN)
                  </label>
                  <input
                    type="number"
                    placeholder="Məs: 1500"
                    value={editCommission}
                    onChange={e => setEditCommission(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              {/* Viewing Date */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    Baxış Tarixi və Saatı
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      const dealCopy = selectedDeal;
                      setSelectedDeal(null);
                      openNewReminderModal({
                        dealId: dealCopy.id,
                        clientId: dealCopy.client_id || undefined,
                        title: `Baxış: ${dealCopy.listing_title}`,
                        type: 'viewing'
                      });
                    }}
                    className="text-[10px] font-bold text-purple-400 hover:text-purple-300 flex items-center gap-1"
                  >
                    <Clock className="w-3 h-3" /> Bot Xatırlatması Qur
                  </button>
                </div>
                <input
                  type="datetime-local"
                  value={editViewingAt}
                  onChange={e => setEditViewingAt(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-blue-500"
                />
              </div>

              {/* Private Notes */}
              <div>
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  Şəxsi Qeydlərim (Qapı kodu, Sahibin son qiyməti və s.)
                </label>
                <textarea
                  rows={3}
                  placeholder="Yalnız sizin görəcəyiniz gizli qeydlər..."
                  value={editNotes}
                  onChange={e => setEditNotes(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-100 focus:outline-none focus:border-blue-500 resize-none"
                />
              </div>

              {/* Action Buttons */}
              <div className="pt-2 flex flex-col gap-2">
                <button
                  type="button"
                  onClick={() => shareToClientWhatsApp(selectedDeal)}
                  className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-md shadow-emerald-600/20"
                >
                  <Share2 className="w-4 h-4" />
                  WhatsApp ilə Müştəriyə Təklif Göndər
                </button>

                {selectedDeal.listing_url && (
                  <a
                    href={selectedDeal.listing_url}
                    target="_blank"
                    rel="noreferrer"
                    className="w-full py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs flex items-center justify-center gap-1.5"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    Orijinal Elana Bax
                  </a>
                )}
              </div>
            </div>

            {/* Modal Footer with Delete & Save */}
            <div className="p-4 border-t border-slate-800 flex flex-col gap-2">
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setSelectedDeal(null)}
                  className="w-1/3 py-2.5 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold"
                >
                  Bağla
                </button>
                <button
                  type="button"
                  disabled={savingDeal}
                  onClick={handleSaveDeal}
                  className="w-2/3 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold shadow-md shadow-blue-600/20 flex items-center justify-center gap-1"
                >
                  {savingDeal ? 'Saxlanılır...' : 'Yadda Saxla'}
                </button>
              </div>

              <button
                type="button"
                onClick={() => handleDeleteDeal(selectedDeal.id)}
                className="w-full py-2.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-400 font-bold text-xs flex items-center justify-center gap-1.5 transition-all mt-1"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Elanı CRM-dən Sil
              </button>
            </div>
          </div>
        </div>
      )}

      {/* --- NEW CLIENT MODAL --- */}
      {showNewClientModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-4">
          <form
            onSubmit={handleCreateClient}
            className="bg-slate-900 border border-slate-800 rounded-t-3xl sm:rounded-3xl w-full max-w-md p-5 space-y-4 shadow-2xl animate-in slide-in-from-bottom duration-200"
          >
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <h3 className="text-sm font-bold text-white">Yeni Müştəri Əlavə Et</h3>
              <button
                type="button"
                onClick={() => setShowNewClientModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div>
              <label className="text-[11px] font-bold text-slate-400 block mb-1">Müştərinin Adı *</label>
              <input
                type="text"
                required
                placeholder="Məs: Cavid bəy"
                value={newClientName}
                onChange={e => setNewClientName(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="text-[11px] font-bold text-slate-400 block mb-1">Telefon / WhatsApp</label>
              <input
                type="text"
                placeholder="Məs: 050 123 45 67"
                value={newClientPhone}
                onChange={e => setNewClientPhone(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500 font-mono"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[11px] font-bold text-slate-400 block mb-1">Növ</label>
                <select
                  value={newClientType}
                  onChange={e => setNewClientType(e.target.value as any)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="buyer">Alıcı (Satış)</option>
                  <option value="renter">İcarəçi (Kirayə)</option>
                </select>
              </div>
              <div>
                <label className="text-[11px] font-bold text-slate-400 block mb-1">Maks. Büdcə (AZN)</label>
                <input
                  type="number"
                  placeholder="Məs: 150000"
                  value={newClientBudget}
                  onChange={e => setNewClientBudget(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="text-[11px] font-bold text-slate-400 block mb-1">Tələblər / Qeyd</label>
              <textarea
                rows={2}
                placeholder="Məs: Nərimanovda 2 otaq yeni tikili axtarır..."
                value={newClientNotes}
                onChange={e => setNewClientNotes(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-blue-500 resize-none"
              />
            </div>

            <div className="pt-2 flex gap-2">
              <button
                type="button"
                onClick={() => setShowNewClientModal(false)}
                className="w-1/3 py-2.5 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold"
              >
                İmtina
              </button>
              <button
                type="submit"
                disabled={savingClient}
                className="w-2/3 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold shadow-md shadow-blue-600/20"
              >
                {savingClient ? 'Yaradılır...' : 'Müştərini Saxla'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* --- REMINDER / VIEWING MODAL --- */}
      {showReminderModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-4">
          <form
            onSubmit={handleSaveReminder}
            className="bg-slate-900 border border-slate-800 rounded-t-3xl sm:rounded-3xl w-full max-w-md p-5 space-y-3.5 shadow-2xl animate-in slide-in-from-bottom duration-200 max-h-[90vh] overflow-y-auto"
          >
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-purple-500/20 text-purple-400 flex items-center justify-center">
                  <Clock className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-bold text-white">
                  {selectedReminder ? 'Xatırlatmanı Redaktə Et' : 'Yeni Xatırlatma / Baxış'}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowReminderModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Type selector buttons */}
            <div>
              <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1.5">
                Xatırlatma Növü
              </label>
              <div className="grid grid-cols-5 gap-1.5">
                {[
                  { key: 'viewing', label: 'Baxış', icon: '🏠' },
                  { key: 'call', label: 'Zəng', icon: '📞' },
                  { key: 'follow_up', label: 'İzləmə', icon: '🔄' },
                  { key: 'notary', label: 'Notariat', icon: '🖋️' },
                  { key: 'other', label: 'Digər', icon: '📌' },
                ].map(t => (
                  <button
                    key={t.key}
                    type="button"
                    onClick={() => {
                      haptic('light');
                      setReminderType(t.key as any);
                    }}
                    className={`py-2 px-1 rounded-xl text-[10px] font-bold flex flex-col items-center gap-1 border transition-all ${
                      reminderType === t.key
                        ? 'bg-purple-600 text-white border-purple-500 shadow-md shadow-purple-600/20'
                        : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-slate-200'
                    }`}
                  >
                    <span>{t.icon}</span>
                    <span className="truncate">{t.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Title */}
            <div>
              <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Başlıq *
              </label>
              <input
                type="text"
                required
                placeholder="Məs: 28 May 3 otaqlı mənzilə baxış"
                value={reminderTitle}
                onChange={e => setReminderTitle(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500"
              />
            </div>

            {/* Quick Presets for Date */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  Baxış / Görüş Vaxtı *
                </label>
                <span className="text-[10px] text-slate-500">Sürətli seçimlər</span>
              </div>
              <div className="flex gap-1.5 overflow-x-auto pb-1.5 scrollbar-none">
                {[
                  { label: 'Bugün 15:00', val: getPresetLocalDatetime(0, 15, 0) },
                  { label: 'Bugün 18:00', val: getPresetLocalDatetime(0, 18, 0) },
                  { label: 'Sabah 11:00', val: getPresetLocalDatetime(1, 11, 0) },
                  { label: 'Sabah 15:00', val: getPresetLocalDatetime(1, 15, 0) },
                  { label: 'Birigün 12:00', val: getPresetLocalDatetime(2, 12, 0) },
                ].map(p => (
                  <button
                    key={p.label}
                    type="button"
                    onClick={() => {
                      haptic('light');
                      setReminderDueAt(p.val);
                    }}
                    className={`px-2 py-1 text-[10px] font-semibold rounded-lg border whitespace-nowrap transition-all ${
                      reminderDueAt === p.val
                        ? 'bg-purple-600/30 text-purple-300 border-purple-500'
                        : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-slate-200'
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
              <input
                type="datetime-local"
                required
                value={reminderDueAt}
                onChange={e => setReminderDueAt(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500"
              />
            </div>

            {/* Notification Lead Time */}
            <div>
              <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1.5">
                Bot nə qədər əvvəl xəbər versin?
              </label>
              <div className="grid grid-cols-5 gap-1.5">
                {[
                  { min: 15, label: '15 dəq' },
                  { min: 30, label: '30 dəq' },
                  { min: 60, label: '1 saat' },
                  { min: 120, label: '2 saat' },
                  { min: 0, label: 'Vaxtında' },
                ].map(opt => (
                  <button
                    key={opt.min}
                    type="button"
                    onClick={() => {
                      haptic('light');
                      setReminderLeadMinutes(opt.min);
                    }}
                    className={`py-1.5 px-1 rounded-xl text-[10px] font-bold border transition-all ${
                      reminderLeadMinutes === opt.min
                        ? 'bg-purple-600 text-white border-purple-500 shadow-sm'
                        : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-slate-200'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Client and Deal pickers */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  Müştəri (İstəyə bağlı)
                </label>
                <select
                  value={reminderClientId}
                  onChange={e => setReminderClientId(e.target.value ? Number(e.target.value) : '')}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-2 text-xs text-white focus:outline-none focus:border-purple-500 truncate"
                >
                  <option value="">Seçilməyib</option>
                  {clients.map(c => (
                    <option key={c.id} value={c.id}>
                      {c.name} {c.phone ? `(${c.phone})` : ''}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  Elan / Sövdə (İstəyə bağlı)
                </label>
                <select
                  value={reminderDealId}
                  onChange={e => setReminderDealId(e.target.value ? Number(e.target.value) : '')}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-2 text-xs text-white focus:outline-none focus:border-purple-500 truncate"
                >
                  <option value="">Seçilməyib</option>
                  {deals.map(d => (
                    <option key={d.id} value={d.id}>
                      {d.listing_title}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Notes */}
            <div>
              <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Qeydlər (Qapı kodu, sahibinin nömrəsi və s.)
              </label>
              <textarea
                rows={2}
                placeholder="Əlavə məlumat..."
                value={reminderNotes}
                onChange={e => setReminderNotes(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-purple-500 resize-none"
              />
            </div>

            {/* Status (when editing) */}
            {selectedReminder && (
              <div>
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  Status
                </label>
                <select
                  value={reminderStatus}
                  onChange={e => setReminderStatus(e.target.value as any)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500"
                >
                  <option value="pending">Gözləyir</option>
                  <option value="notified">Xəbərdarlıq göndərilib</option>
                  <option value="completed">Tamamlandı</option>
                  <option value="cancelled">Ləğv edildi</option>
                </select>
              </div>
            )}

            <div className="pt-2 flex gap-2">
              <button
                type="button"
                onClick={() => setShowReminderModal(false)}
                className="w-1/3 py-2.5 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold"
              >
                İmtina
              </button>
              <button
                type="submit"
                disabled={savingReminder}
                className="w-2/3 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold shadow-md shadow-purple-600/20"
              >
                {savingReminder ? 'Yadda saxlanılır...' : (selectedReminder ? 'Yenilə' : 'Xatırlatma Təyin Et')}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* --- PORTFOLIO EDIT / CREATE MODAL --- */}
      {(selectedPortfolioItem || isNewPortfolioModal) && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-t-3xl sm:rounded-3xl w-full max-w-lg max-h-[92vh] flex flex-col shadow-2xl animate-in slide-in-from-bottom duration-200">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-slate-800 flex-shrink-0">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-xl bg-purple-500/20 text-purple-400 flex items-center justify-center">
                  <Edit3 className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">
                    {selectedPortfolioItem ? `Elanı Redaktə Et (#${selectedPortfolioItem.id})` : 'Yeni Elan Əlavə Et'}
                  </h3>
                  <p className="text-[10px] text-slate-400">Bütün sahələri fərdiləşdirə bilərsiniz</p>
                </div>
              </div>
              <button
                type="button"
                onClick={closePortfolioModal}
                className="w-8 h-8 rounded-full bg-slate-800 text-slate-400 hover:text-white flex items-center justify-center"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Scrollable Form Body */}
            <form onSubmit={handleSavePortfolio} id="portfolio-edit-form" className="p-4 space-y-4 overflow-y-auto flex-1 text-xs">
              {/* Title */}
              <div>
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  Elanın Başlığı *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Məs: Nərimanov metrosu yaxınlığında 3 otaqlı təmirli mənzil"
                  value={editPortTitle}
                  onChange={e => setEditPortTitle(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500"
                />
              </div>

              {/* Price & Currency */}
              <div className="grid grid-cols-3 gap-2">
                <div className="col-span-2">
                  <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                    Qiymət *
                  </label>
                  <input
                    type="number"
                    required
                    placeholder="Məs: 185000"
                    value={editPortPrice}
                    onChange={e => setEditPortPrice(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500 font-mono"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                    Valyuta
                  </label>
                  <select
                    value={editPortCurrency}
                    onChange={e => setEditPortCurrency(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2 py-2 text-xs text-white focus:outline-none focus:border-purple-500"
                  >
                    <option value="AZN">AZN (₼)</option>
                    <option value="USD">USD ($)</option>
                  </select>
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  Ətraflı Təsvir
                </label>
                <textarea
                  rows={3}
                  placeholder="Mənzil haqqında ətraflı məlumat, təmir vəziyyəti, infrastruktur..."
                  value={editPortDescription}
                  onChange={e => setEditPortDescription(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-purple-500 resize-none"
                />
              </div>

              {/* Parameters Grid: Rooms, Area, Floor, Total Floors */}
              <div className="grid grid-cols-4 gap-2">
                <div>
                  <label className="text-[10px] font-bold text-slate-400 block mb-1">Otaq</label>
                  <input
                    type="number"
                    placeholder="3"
                    value={editPortRooms}
                    onChange={e => setEditPortRooms(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-white text-center focus:outline-none focus:border-purple-500"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-bold text-slate-400 block mb-1">Sahə (m²)</label>
                  <input
                    type="number"
                    step="0.1"
                    placeholder="110"
                    value={editPortArea}
                    onChange={e => setEditPortArea(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-white text-center focus:outline-none focus:border-purple-500"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-bold text-slate-400 block mb-1">Mərtəbə</label>
                  <input
                    type="number"
                    placeholder="7"
                    value={editPortFloor}
                    onChange={e => setEditPortFloor(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-white text-center focus:outline-none focus:border-purple-500"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-bold text-slate-400 block mb-1">Ümumi Mərt.</label>
                  <input
                    type="number"
                    placeholder="16"
                    value={editPortTotalFloors}
                    onChange={e => setEditPortTotalFloors(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-white text-center focus:outline-none focus:border-purple-500"
                  />
                </div>
              </div>

              {/* District & Metro */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[11px] font-bold text-slate-400 block mb-1">Rayon</label>
                  <select
                    value={editPortDistrict}
                    onChange={e => setEditPortDistrict(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500"
                  >
                    <option value="">Seçin...</option>
                    {BAKU_DISTRICT_OPTIONS.map(d => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-[11px] font-bold text-slate-400 block mb-1">Metro Stansiyası</label>
                  <select
                    value={editPortMetro}
                    onChange={e => setEditPortMetro(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500"
                  >
                    <option value="">Seçin...</option>
                    {BAKU_METRO_OPTIONS.map(m => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Exact Address */}
              <div>
                <label className="text-[11px] font-bold text-slate-400 block mb-1">Dəqiq Ünvan</label>
                <input
                  type="text"
                  placeholder="Məs: Təbriz küçəsi 45, Heydər Əliyev mərkəzinin yanı"
                  value={editPortAddress}
                  onChange={e => setEditPortAddress(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500"
                />
              </div>

              {/* Offer Type, Building Type, Property Type */}
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="text-[10px] font-bold text-slate-400 block mb-1">Təklif Növü</label>
                  <select
                    value={editPortOfferType}
                    onChange={e => setEditPortOfferType(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2 py-1.5 text-xs text-white focus:outline-none focus:border-purple-500"
                  >
                    <option value="sale">Satış</option>
                    <option value="rent">Kirayə</option>
                    <option value="daily">Günlük</option>
                  </select>
                </div>
                <div>
                  <label className="text-[10px] font-bold text-slate-400 block mb-1">Bina Növü</label>
                  <select
                    value={editPortBuildingType}
                    onChange={e => setEditPortBuildingType(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2 py-1.5 text-xs text-white focus:outline-none focus:border-purple-500"
                  >
                    <option value="new_building">Yeni tikili</option>
                    <option value="old_building">Köhnə tikili</option>
                    <option value="other">Digər</option>
                  </select>
                </div>
                <div>
                  <label className="text-[10px] font-bold text-slate-400 block mb-1">Əmlak Növü</label>
                  <select
                    value={editPortPropertyType}
                    onChange={e => setEditPortPropertyType(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2 py-1.5 text-xs text-white focus:outline-none focus:border-purple-500"
                  >
                    <option value="apartment">Mənzil</option>
                    <option value="house">Həyət evi</option>
                    <option value="office">Ofis</option>
                    <option value="commercial">Obyekt</option>
                    <option value="land">Torpaq</option>
                  </select>
                </div>
              </div>

              {/* Photos Gallery Management */}
              <div>
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1.5">
                  Şəkillər ({editPortPhotos.length})
                </label>

                {editPortPhotos.length > 0 && (
                  <div className="grid grid-cols-4 gap-2 mb-2">
                    {editPortPhotos.map((url, idx) => (
                      <div key={idx} className="relative aspect-square rounded-xl bg-slate-950 border border-slate-800 overflow-hidden group">
                        <img src={url} alt={`Foto ${idx + 1}`} className="w-full h-full object-cover" />
                        <button
                          type="button"
                          onClick={() => handleRemovePhoto(idx)}
                          className="absolute top-1 right-1 w-5 h-5 rounded-full bg-rose-600 text-white flex items-center justify-center shadow"
                          title="Şəkli sil"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                <div className="flex gap-2">
                  <input
                    type="url"
                    placeholder="Şəkil URL linki əlavə et..."
                    value={newPhotoInput}
                    onChange={e => setNewPhotoInput(e.target.value)}
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500"
                  />
                  <button
                    type="button"
                    onClick={handleAddPhoto}
                    className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold rounded-xl text-xs"
                  >
                    + Şəkil
                  </button>
                </div>
              </div>

              {/* Contact Information */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[11px] font-bold text-slate-400 block mb-1">Əlaqə Şəxsi</label>
                  <input
                    type="text"
                    placeholder="Adınız və ya agentliyin adı"
                    value={editPortContactName}
                    onChange={e => setEditPortContactName(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-bold text-slate-400 block mb-1">Əlaqə Telefonu</label>
                  <input
                    type="text"
                    placeholder="+994 50 123 45 67"
                    value={editPortContactPhone}
                    onChange={e => setEditPortContactPhone(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500 font-mono"
                  />
                </div>
              </div>

              {/* Private Internal Notes (Agent-only) */}
              <div>
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  Şəxsi Gizli Qeydlərim (Yalnız siz görürsünüz)
                </label>
                <textarea
                  rows={2}
                  placeholder="Məs: Sahibin son qiyməti 175k, komissiya 1.5%, qapı kodu 4521..."
                  value={editPortNotes}
                  onChange={e => setEditPortNotes(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-purple-500 resize-none"
                />
              </div>

              {/* Status & Public Visibility Toggle */}
              <div className="bg-slate-950 border border-slate-800/80 rounded-xl p-3 flex items-center justify-between">
                <div>
                  <p className="text-xs font-bold text-white">İctimai Vitrində Aktivdir</p>
                  <p className="text-[10px] text-slate-400">Deaktiv etsəniz elan silinmir, lakin müştəri linkində görünmür</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={editPortIsActive}
                    onChange={e => setEditPortIsActive(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-purple-600"></div>
                </label>
              </div>

              <div>
                <label className="text-[11px] font-bold text-slate-400 block mb-1">Status</label>
                <select
                  value={editPortStatus}
                  onChange={e => setEditPortStatus(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500"
                >
                  <option value="active">Aktiv (Satışda)</option>
                  <option value="sold">Satıldı (Arxiv)</option>
                  <option value="archived">Dayandırıldı</option>
                </select>
              </div>
            </form>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-800 flex flex-col gap-2 flex-shrink-0">
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={closePortfolioModal}
                  className="w-1/3 py-2.5 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold"
                >
                  Bağla
                </button>
                <button
                  type="submit"
                  form="portfolio-edit-form"
                  disabled={savingPortfolio}
                  className="w-2/3 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold shadow-md shadow-purple-600/20 flex items-center justify-center gap-1"
                >
                  {savingPortfolio ? 'Saxlanılır...' : 'Yadda Saxla'}
                </button>
              </div>

              {selectedPortfolioItem && (
                <button
                  type="button"
                  onClick={() => handleDeletePortfolioItem(selectedPortfolioItem.id)}
                  className="w-full py-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-400 font-bold text-xs flex items-center justify-center gap-1.5 transition-all"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Elanı Portfeldən Sil (Yuva boşalsın)
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* --- DOMAIN MANAGEMENT MODAL --- */}
      {showDomainModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-t-3xl sm:rounded-3xl w-full max-w-md max-h-[90vh] flex flex-col shadow-2xl animate-in slide-in-from-bottom duration-200">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-slate-800 flex-shrink-0">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-xl bg-indigo-500/20 text-indigo-400 flex items-center justify-center">
                  <Globe className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Domen Tənzimləmələri</h3>
                  <p className="text-[10px] text-slate-400">Portfel və vitrin üçün veb ünvanı</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowDomainModal(false)}
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-4 space-y-4 overflow-y-auto flex-1 text-xs">
              {/* Active Domain Info Card */}
              <div className="p-3.5 rounded-2xl bg-dark-950 border border-slate-800 space-y-2">
                <span className="text-slate-400 text-[11px] block">Cari Aktiv Domen:</span>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-mono font-bold text-indigo-300">
                    {portfolioOverview?.custom_domain_info?.active_domain || 'realtor.erma.shop'}
                  </span>
                  <span className={`text-[10px] px-2 py-0.5 rounded font-semibold border ${
                    portfolioOverview?.custom_domain_info?.source === 'agent'
                      ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30'
                      : portfolioOverview?.custom_domain_info?.source === 'reseller'
                      ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                      : 'bg-slate-800 text-slate-400 border-slate-700'
                  }`}>
                    {portfolioOverview?.custom_domain_info?.source === 'agent'
                      ? 'Fərdi Domen'
                      : portfolioOverview?.custom_domain_info?.source === 'reseller'
                      ? 'Reseller Domeni'
                      : 'Sistem Domeni'}
                  </span>
                </div>

                {portfolioOverview?.custom_domain_info?.reseller_custom_domain && (
                  <p className="text-[11px] text-slate-400 pt-1 border-t border-slate-800/80">
                    🏢 Reseller şəbəkəniz: <span className="font-mono text-emerald-400">{portfolioOverview.custom_domain_info.reseller_custom_domain}</span>. Fərdi domeniniz olmadığı halda portfeliniz avtomatik bu reseller domenində açılır.
                  </p>
                )}
              </div>

              {/* Has Feature vs Upgrade Offer */}
              {portfolioOverview?.custom_domain_info?.agent_feature_custom_domain ? (
                <div className="space-y-3">
                  <div className="space-y-1.5">
                    <label className="text-[11px] font-semibold text-slate-300 block">
                      Fərdi Domen Adınız:
                    </label>
                    <input
                      type="text"
                      placeholder="məs: samiremlak.az və ya emlak.sayt.az"
                      value={domainInput}
                      onChange={(e) => setDomainInput(e.target.value)}
                      className="w-full bg-dark-950 border border-slate-700 rounded-xl px-3 py-2 text-indigo-200 font-mono text-xs focus:outline-none focus:border-indigo-500"
                    />
                    <span className="text-[10px] text-slate-500 block">
                      https:// və ya /v/ yazmayın, sadəcə domen adını daxil edin.
                    </span>
                  </div>

                  <label className="flex items-center gap-2.5 p-3 rounded-xl bg-dark-950 border border-slate-800 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={domainEnabled}
                      onChange={(e) => setDomainEnabled(e.target.checked)}
                      className="w-4 h-4 rounded accent-indigo-500"
                    />
                    <div>
                      <span className="font-semibold text-slate-200 block">Fərdi domeni aktiv et</span>
                      <span className="text-[10px] text-slate-400">Deaktiv edildikdə sistem reseller və ya default domenə keçəcək</span>
                    </div>
                  </label>

                  {/* DNS Instructions Card */}
                  <div className="p-3.5 rounded-2xl bg-indigo-950/30 border border-indigo-500/20 space-y-2">
                    <div className="flex items-center gap-1.5 text-indigo-300 font-semibold">
                      <ShieldCheck className="w-4 h-4" />
                      <span>DNS Quraşdırma Təlimatı (CNAME)</span>
                    </div>
                    <p className="text-[11px] text-slate-300 leading-relaxed">
                      Domen provayderinizin (və ya Cloudflare panelinizin) DNS bölməsində aşağıdakı qeydi əlavə edin:
                    </p>
                    <div className="bg-dark-950 p-2.5 rounded-xl border border-slate-800 font-mono text-[11px] space-y-1">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Növ (Type):</span>
                        <span className="text-amber-300 font-bold">CNAME</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Ad (Name/Host):</span>
                        <span className="text-indigo-300 font-bold">@ (və ya subdomen)</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Hədəf (Target):</span>
                        <span className="text-emerald-400 font-bold">
                          {portfolioOverview?.custom_domain_info?.cname_target || 'realtor.erma.shop'}
                        </span>
                      </div>
                    </div>

                    <div className="pt-2">
                      <button
                        type="button"
                        onClick={handleVerifyDomain}
                        disabled={domainVerifying}
                        className="w-full flex items-center justify-center gap-1.5 py-2 rounded-xl bg-indigo-600/30 hover:bg-indigo-600/40 text-indigo-200 border border-indigo-500/30 font-semibold transition-all disabled:opacity-50"
                      >
                        {domainVerifying ? 'DNS Yoxlanılır...' : '🔍 DNS Qeydini Yoxla'}
                      </button>
                    </div>

                    {domainVerifyResult && (
                      <div className={`p-2.5 rounded-xl text-[11px] border mt-2 ${
                        domainVerifyResult.verified
                          ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                          : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                      }`}>
                        <div className="flex items-center gap-1 font-semibold mb-0.5">
                          {domainVerifyResult.verified ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <AlertCircle className="w-3.5 h-3.5 text-amber-400" />}
                          <span>{domainVerifyResult.verified ? 'Təsdiqləndi' : 'Diqqət'}</span>
                        </div>
                        <p>{domainVerifyResult.message}</p>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                /* Feature Not Available - Quick Activation */
                <div className="p-4 rounded-2xl bg-gradient-to-br from-indigo-950/40 via-purple-950/20 to-slate-900 border border-indigo-500/30 space-y-3">
                  <div className="flex items-center gap-2 text-indigo-300 font-bold text-xs">
                    <Sparkles className="w-4 h-4 text-indigo-400" />
                    <span>Fərdi Domen Add-onu (+5 AZN/ay)</span>
                  </div>
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    Portfel vitrininizi və müştəri linklərinizi öz fərdi domeninizlə (məs. <code className="text-indigo-300">samiremlak.az</code>) təqdim edərək müştərilərinizdə daha yüksək etibar yarada bilərsiniz.
                  </p>
                  <div className="space-y-1.5 pt-1">
                    <label className="text-[11px] font-semibold text-slate-300 block">
                      Domen Adınızı Daxil Edin:
                    </label>
                    <input
                      type="text"
                      placeholder="məs: samiremlak.az"
                      value={domainInput}
                      onChange={(e) => setDomainInput(e.target.value)}
                      className="w-full bg-dark-950 border border-slate-700 rounded-xl px-3 py-2 text-indigo-200 font-mono text-xs focus:outline-none focus:border-indigo-500"
                    />
                    <span className="text-[10px] text-slate-500 block">
                      Domeni əlavə etdikdə abunəliyinizə aylıq 5 AZN əlavə olunacaq və faktura yaradılacaq.
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-2 p-4 border-t border-slate-800 flex-shrink-0">
              <button
                type="button"
                onClick={() => setShowDomainModal(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition-colors"
              >
                Bağla
              </button>
              <button
                type="button"
                onClick={handleSaveDomain}
                disabled={domainSaving || !domainInput.trim()}
                className="px-5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl shadow-lg shadow-indigo-600/20 disabled:opacity-50 transition-all flex items-center gap-1.5"
              >
                <Globe className="w-3.5 h-3.5" />
                {domainSaving
                  ? 'Yadda saxlanılır...'
                  : portfolioOverview?.custom_domain_info?.agent_feature_custom_domain
                  ? 'Yadda Saxla'
                  : 'Fərdi Domeni Qoş (+5 AZN)'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Floating Toast Notification */}
      {copiedToast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-slate-900/95 border border-purple-500/40 text-white text-xs font-semibold px-4 py-2.5 rounded-full shadow-2xl backdrop-blur-md flex items-center gap-2 animate-in fade-in duration-200">
          <Check className="w-4 h-4 text-emerald-400" />
          <span>{copiedToast}</span>
        </div>
      )}
    </div>
  );
}

function SwipeableDealCard({
  deal,
  stageObj,
  onOpen,
  onDelete,
  onShareWhatsApp,
  onAddReminder,
  haptic
}: {
  deal: CrmDeal;
  stageObj: any;
  onOpen: (deal: CrmDeal) => void;
  onDelete: (dealId: number) => void;
  onShareWhatsApp: (deal: CrmDeal) => void;
  onAddReminder?: (deal: CrmDeal) => void;
  haptic: (type: 'light' | 'medium' | 'heavy') => void;
}) {
  const [offsetX, setOffsetX] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [startX, setStartX] = useState(0);
  const [isSwipedOpen, setIsSwipedOpen] = useState(false);

  // Touch Handlers for Mobile & Telegram Mini App
  const handleTouchStart = (e: React.TouchEvent) => {
    setStartX(e.touches[0].clientX);
    setIsDragging(true);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!isDragging) return;
    const currentX = e.touches[0].clientX;
    const diff = currentX - startX;
    if (isSwipedOpen) {
      const newOffset = Math.min(0, Math.max(-160, -90 + diff));
      setOffsetX(newOffset);
    } else if (diff < 0) {
      setOffsetX(Math.max(-160, diff));
    }
  };

  const handleTouchEnd = () => {
    if (!isDragging) return;
    setIsDragging(false);
    if (offsetX < -130) {
      haptic('heavy');
      onDelete(deal.id);
      setOffsetX(0);
      setIsSwipedOpen(false);
    } else if (offsetX < -45) {
      haptic('medium');
      setOffsetX(-90);
      setIsSwipedOpen(true);
    } else {
      setOffsetX(0);
      setIsSwipedOpen(false);
    }
  };

  // Mouse Handlers for Desktop Browser
  const handleMouseDown = (e: React.MouseEvent) => {
    setStartX(e.clientX);
    setIsDragging(true);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    const diff = e.clientX - startX;
    if (isSwipedOpen) {
      setOffsetX(Math.min(0, Math.max(-160, -90 + diff)));
    } else if (diff < 0) {
      setOffsetX(Math.max(-160, diff));
    }
  };

  const handleMouseUp = () => {
    if (!isDragging) return;
    setIsDragging(false);
    if (offsetX < -130) {
      haptic('heavy');
      onDelete(deal.id);
      setOffsetX(0);
      setIsSwipedOpen(false);
    } else if (offsetX < -45) {
      haptic('medium');
      setOffsetX(-90);
      setIsSwipedOpen(true);
    } else {
      setOffsetX(0);
      setIsSwipedOpen(false);
    }
  };

  const handleClick = (e: React.MouseEvent) => {
    if (Math.abs(offsetX) > 10) {
      e.stopPropagation();
      setOffsetX(0);
      setIsSwipedOpen(false);
      return;
    }
    onOpen(deal);
  };

  return (
    <div className="relative overflow-hidden rounded-2xl select-none group touch-pan-y">
      {/* Background Delete Action Tray (Revealed on Swipe) */}
      <div className="absolute inset-y-0 right-0 w-24 bg-gradient-to-l from-rose-600 to-rose-700 flex items-center justify-center rounded-2xl z-0 shadow-inner">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            haptic('heavy');
            onDelete(deal.id);
          }}
          className="flex flex-col items-center justify-center text-white w-full h-full active:scale-95 transition-transform"
        >
          <Trash2 className="w-5 h-5 mb-0.5" />
          <span className="text-[10px] font-black uppercase tracking-wider">Sil</span>
        </button>
      </div>

      {/* Foreground Swipeable Card */}
      <div
        style={{
          transform: `translateX(${offsetX}px)`,
          transition: isDragging ? 'none' : 'transform 0.25s cubic-bezier(0.2, 0.8, 0.2, 1)'
        }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onClick={handleClick}
        className="relative z-10 bg-slate-900 border border-slate-800/80 hover:border-slate-700 rounded-2xl p-3.5 transition-colors shadow-sm active:bg-slate-900/90 cursor-pointer"
      >
        <div className="flex gap-3">
          {deal.listing_image ? (
            <img
              src={deal.listing_image}
              alt=""
              className="w-20 h-20 rounded-xl object-cover border border-slate-800 flex-shrink-0 bg-slate-950"
            />
          ) : (
            <div className="w-20 h-20 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-center flex-shrink-0 text-slate-600">
              🏠
            </div>
          )}

          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-1 mb-1">
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${stageObj.color}`}>
                {stageObj.label}
              </span>
              <span className="text-xs font-black text-emerald-400">
                {deal.custom_offer_price ? `${intFormat(deal.custom_offer_price)} AZN` : `${intFormat(deal.listing_price)} ${deal.listing_currency}`}
              </span>
            </div>

            <h3 className="text-xs font-bold text-slate-100 line-clamp-1 mb-1">
              {deal.listing_title}
            </h3>

            {deal.client_name ? (
              <p className="text-[11px] text-blue-400 flex items-center gap-1 font-medium mb-1">
                <Users className="w-3 h-3" />
                {deal.client_name}
              </p>
            ) : (
              <p className="text-[11px] text-slate-500 italic mb-1">Müştəri təyin edilməyib</p>
            )}

            <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-800/60">
              <span>{deal.listing_location || 'Bakı'}</span>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={(e) => { e.stopPropagation(); onAddReminder?.(deal); }}
                  className="flex items-center gap-1 text-purple-400 font-bold bg-purple-500/10 px-2 py-0.5 rounded-md hover:bg-purple-500/20"
                  title="Baxış və ya xatırlatma təyin et"
                >
                  <Clock className="w-3 h-3" />
                  Baxış
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); onShareWhatsApp(deal); }}
                  className="flex items-center gap-1 text-emerald-400 font-bold bg-emerald-500/10 px-2 py-0.5 rounded-md hover:bg-emerald-500/20"
                >
                  <Share2 className="w-3 h-3" />
                  WhatsApp
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); onDelete(deal.id); }}
                  className="p-1 text-slate-500 hover:text-rose-400 rounded-md hover:bg-rose-500/10 transition-colors"
                  title="Sil"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function intFormat(val?: number) {
  if (val === undefined || val === null) return '0';
  return Math.round(val).toLocaleString('az-AZ');
}
