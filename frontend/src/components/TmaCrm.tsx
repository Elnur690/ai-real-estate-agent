import React, { useEffect, useState } from 'react';
import {
  Briefcase, Users, CheckCircle, Clock, Search, Plus, Filter,
  Phone, MessageSquare, ExternalLink, Calendar, DollarSign,
  ChevronRight, X, AlertCircle, Edit3, Trash2, ArrowRight, Share2, Sparkles
} from 'lucide-react';
import api from '../api';
import { CrmDeal, CrmClient, CrmStats } from '../types';

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

export function TmaCrm() {
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const [agentName, setAgentName] = useState<string>('Agent');
  const [agentPhone, setAgentPhone] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'deals' | 'clients' | 'stats'>('deals');
  
  const [deals, setDeals] = useState<CrmDeal[]>([]);
  const [clients, setClients] = useState<CrmClient[]>([]);
  const [stats, setStats] = useState<CrmStats | null>(null);
  
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

  const haptic = (type: 'light' | 'medium' | 'heavy' = 'light') => {
    try {
      window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(type);
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
          setAuthError('Zəhmət olmasa bu tətbiqi Telegram Bot (@RealEstateBot) menyusu daxilində açın.');
          setLoading(false);
          return;
        }

        // Authenticate with backend and check feature_crm access
        const res = await api.post('/auth/telegram-webapp', { init_data: initData });
        const authData = res.data;
        
        localStorage.setItem('token', authData.access_token);
        localStorage.setItem('user_name', authData.user_name);
        setAgentName(authData.tenant_name || authData.user_name);

        await fetchAllData();

        // Check if opened with startapp param (e.g. deal_123)
        const startParam = tg?.initDataUnsafe?.start_param;
        if (startParam && startParam.startsWith('deal_')) {
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

  const fetchAllData = async () => {
    try {
      const [dealsRes, clientsRes, statsRes] = await Promise.all([
        api.get('/crm/deals'),
        api.get('/crm/clients'),
        api.get('/crm/stats'),
      ]);
      setDeals(dealsRes.data || []);
      setClients(clientsRes.data || []);
      setStats(statsRes.data || null);
    } catch (err) {
      console.error('Failed to fetch CRM data:', err);
    }
  };

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
            <button
              onClick={() => { haptic('light'); setShowNewClientModal(true); }}
              className="flex items-center gap-1 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-3 py-1.5 rounded-lg shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" />
              Müştəri
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="grid grid-cols-3 gap-1 bg-slate-950/80 p-1 rounded-xl mt-3 border border-slate-800/80">
          <button
            onClick={() => { haptic('light'); setActiveTab('deals'); }}
            className={`py-1.5 text-xs font-semibold rounded-lg transition-all ${
              activeTab === 'deals' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            📋 Elanlar & Sövdələr ({deals.length})
          </button>
          <button
            onClick={() => { haptic('light'); setActiveTab('clients'); }}
            className={`py-1.5 text-xs font-semibold rounded-lg transition-all ${
              activeTab === 'clients' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            👥 Müştərilər ({clients.length})
          </button>
          <button
            onClick={() => { haptic('light'); setActiveTab('stats'); }}
            className={`py-1.5 text-xs font-semibold rounded-lg transition-all ${
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
                {filteredDeals.map(deal => {
                  const stageObj = STAGES.find(s => s.key === deal.stage) || STAGES[0];
                  return (
                    <div
                      key={deal.id}
                      onClick={() => openDealModal(deal)}
                      className="bg-slate-900 border border-slate-800/80 hover:border-slate-700 rounded-2xl p-3.5 transition-all shadow-sm active:scale-[0.99] cursor-pointer"
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
                            <button
                              onClick={(e) => { e.stopPropagation(); shareToClientWhatsApp(deal); }}
                              className="flex items-center gap-1 text-emerald-400 font-bold bg-emerald-500/10 px-2 py-0.5 rounded-md hover:bg-emerald-500/20"
                            >
                              <Share2 className="w-3 h-3" />
                              WhatsApp
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
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
                    </div>
                  </div>
                ))}
              </div>
            )}
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
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  Baxış Tarixi və Saatı
                </label>
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

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-800 flex gap-2">
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
    </div>
  );
}

function intFormat(val?: number) {
  if (val === undefined || val === null) return '0';
  return Math.round(val).toLocaleString('az-AZ');
}
