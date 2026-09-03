import React, { useEffect, useState } from 'react';
import { 
  Building, MapPin, Phone, MessageSquare, Share2, ChevronLeft, ChevronRight, 
  Check, Maximize2, X, ExternalLink, Calendar, Home, CheckCircle2, User, Layers
} from 'lucide-react';

interface PublicListing {
  id: number;
  title: string;
  description?: string;
  price: number;
  currency: string;
  price_usd?: number;
  district?: string;
  metro_station?: string;
  address?: string;
  rooms?: number;
  area_sqm?: number;
  floor?: number;
  total_floors?: number;
  building_type?: string;
  property_type: string;
  offer_type: string;
  photos: string[];
  share_code: string;
  share_url?: string;
  agent_name: string;
  agent_phone: string;
  agent_whatsapp?: string;
  agent_slug?: string;
  agent_vitrin_url?: string;
  whatsapp_message_url: string;
  created_at: string;
}

interface AgentShowcase {
  tenant_id: number;
  agent_name: string;
  agent_phone: string;
  agent_whatsapp?: string;
  agent_slug?: string;
  active_listings_count: number;
  listings: Array<{
    id: number;
    title: string;
    price: number;
    currency: string;
    district?: string;
    rooms?: number;
    area_sqm?: number;
    photos: string[];
    share_code: string;
    share_url: string;
  }>;
}

export function PortfolioPublicView() {
  const [listing, setListing] = useState<PublicListing | null>(null);
  const [showcase, setShowcase] = useState<AgentShowcase | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activePhotoIdx, setActivePhotoIdx] = useState<number>(0);
  const [lightboxOpen, setLightboxOpen] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);

  // Parse path or hash
  const path = window.location.pathname || '';
  const hash = window.location.hash || '';
  const currentUrl = (path + (hash.startsWith('#') ? hash.substring(1) : hash)).replace(/^\/+/, '/');

  // 1. Single listing under agent: /v/:slug/:id or /p/:slug/:id or /vitrin/:slug/:id
  const agentListingMatch = currentUrl.match(/(?:\/v\/|\/p\/|\/vitrin\/|\/portfolio\/agent\/)([a-zA-Z0-9_\-]+)\/([a-zA-Z0-9_\-]+)/);
  const agentSlugFromListing = agentListingMatch ? agentListingMatch[1] : null;
  const listingIdFromSlug = agentListingMatch ? agentListingMatch[2] : null;

  // 2. Agent showcase: /v/:slug, /@:slug, /vitrin/:slug, /portfolio/agent/:id
  let agentIdentifier: string | null = null;
  if (!listingIdFromSlug) {
    const vMatch = currentUrl.match(/(?:\/v\/|\/vitrin\/|\/portfolio\/agent\/|\/@)([a-zA-Z0-9_\-]+)/);
    if (vMatch) {
      agentIdentifier = vMatch[1];
    }
  }

  // 3. Standalone share code or numeric listing ID: /p/:code or /portfolio/:code
  let directShareCode: string | null = null;
  if (!agentIdentifier && !listingIdFromSlug) {
    const pMatch = currentUrl.match(/(?:\/p\/|\/portfolio\/)([a-zA-Z0-9_\-]+)/);
    if (pMatch && pMatch[1] !== 'agent') {
      directShareCode = pMatch[1];
    }
  }

  useEffect(() => {
    const fetchPublicData = async () => {
      setLoading(true);
      setError(null);
      try {
        if (agentSlugFromListing && listingIdFromSlug) {
          // Fetch single listing by agent slug and listing ID
          const res = await fetch(`/api/v1/portfolio/public/agent/${agentSlugFromListing}/${listingIdFromSlug}`);
          if (!res.ok) {
            // Fallback to direct share code
            const fallbackRes = await fetch(`/api/v1/portfolio/public/${listingIdFromSlug}`);
            if (!fallbackRes.ok) {
              throw new Error('Bu elan artıq aktiv deyil və ya portfeldən silinib.');
            }
            const data = await fallbackRes.json();
            setListing(data);
          } else {
            const data = await res.json();
            setListing(data);
          }
        } else if (agentIdentifier) {
          // Fetch agent showcase
          const res = await fetch(`/api/v1/portfolio/public/agent/${agentIdentifier}`);
          if (!res.ok) {
            // Fallback: check if agentIdentifier was actually a listing share_code
            const fallbackRes = await fetch(`/api/v1/portfolio/public/${agentIdentifier}`);
            if (fallbackRes.ok) {
              const data = await fallbackRes.json();
              setListing(data);
              return;
            }
            throw new Error('Agent vitrini tapılmadı və ya aktiv deyil.');
          }
          const data = await res.json();
          if (Array.isArray(data)) {
            const first = data[0];
            setShowcase({
              tenant_id: first?.id || 0,
              agent_name: first?.agent_name || agentIdentifier,
              agent_phone: first?.agent_phone || '',
              agent_whatsapp: first?.agent_whatsapp || '',
              agent_slug: first?.agent_slug || agentIdentifier,
              active_listings_count: data.length,
              listings: data.map((d: any) => ({
                id: d.id,
                title: d.title,
                price: d.price,
                currency: d.currency,
                district: d.district,
                rooms: d.rooms,
                area_sqm: d.area_sqm,
                photos: d.photos || [],
                share_code: d.share_code,
                share_url: d.share_url || `/v/${first?.agent_slug || agentIdentifier}/${d.id}`
              }))
            });
          } else {
            setShowcase(data);
          }
        } else if (directShareCode) {
          // Direct share code or ID lookup
          const res = await fetch(`/api/v1/portfolio/public/${directShareCode}`);
          if (!res.ok) {
            // Check if it's an agent showcase
            const agentRes = await fetch(`/api/v1/portfolio/public/agent/${directShareCode}`);
            if (agentRes.ok) {
              const data = await agentRes.json();
              if (Array.isArray(data)) {
                const first = data[0];
                setShowcase({
                  tenant_id: first?.id || 0,
                  agent_name: first?.agent_name || directShareCode,
                  agent_phone: first?.agent_phone || '',
                  agent_whatsapp: first?.agent_whatsapp || '',
                  agent_slug: first?.agent_slug || directShareCode,
                  active_listings_count: data.length,
                  listings: data.map((d: any) => ({
                    id: d.id,
                    title: d.title,
                    price: d.price,
                    currency: d.currency,
                    district: d.district,
                    rooms: d.rooms,
                    area_sqm: d.area_sqm,
                    photos: d.photos || [],
                    share_code: d.share_code,
                    share_url: d.share_url || `/v/${first?.agent_slug || directShareCode}/${d.id}`
                  }))
                });
                return;
              }
            }
            throw new Error('Bu elan artıq aktiv deyil və ya portfeldən silinib.');
          }
          const data = await res.json();
          setListing(data);
        } else {
          throw new Error('Məlumat tapılmadı.');
        }
      } catch (err: any) {
        setError(err.message || 'Xəta baş verdi');
      } finally {
        setLoading(false);
      }
    };

    fetchPublicData();
  }, [currentUrl]);

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const getOfferTypeLabel = (type: string) => {
    switch (type) {
      case 'rent': return 'Kirayə';
      case 'daily_rent': return 'Günlük Kirayə';
      default: return 'Satış';
    }
  };

  const getPropertyTypeLabel = (type: string) => {
    switch (type) {
      case 'house': return 'Həyət Evi / Villa';
      case 'office': return 'Ofis';
      case 'commercial': return 'Obyekt';
      case 'land': return 'Torpaq Sahəsi';
      default: return 'Mənzil';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4 text-white">
        <div className="w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-slate-400 text-sm font-medium">Elan məlumatları yüklənir...</p>
      </div>
    );
  }

  if (error || (!listing && !showcase)) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-center text-white">
        <div className="w-16 h-16 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center mb-4">
          <Home className="w-8 h-8 text-rose-400" />
        </div>
        <h1 className="text-xl font-bold mb-2">Elan Mövcud Deyil</h1>
        <p className="text-slate-400 text-sm max-w-md mb-6 leading-relaxed">
          {error || 'Bu elan müddəti bitdiyi üçün və ya satıldığı üçün portfeldən çıxarılmış ola bilər.'}
        </p>
      </div>
    );
  }

  // --- AGENT SHOWCASE VITRIN VIEW ---
  if (showcase) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 selection:bg-purple-500 selection:text-white pb-20">
        {/* Header */}
        <header className="sticky top-0 z-40 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 px-4 py-3.5">
          <div className="max-w-5xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-600 flex items-center justify-center font-bold text-white shadow-md shadow-purple-600/20">
                {showcase.agent_name.charAt(0).toUpperCase()}
              </div>
              <div>
                <h1 className="text-base font-bold text-white flex items-center gap-1.5">
                  <span>{showcase.agent_name}</span>
                  <CheckCircle2 className="w-4 h-4 text-purple-400" />
                </h1>
                <p className="text-xs text-slate-400">Rəsmi Əmlak Portfeli & Vitrin</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <a
                href={`https://wa.me/${(showcase.agent_whatsapp || showcase.agent_phone).replace(/\D/g, '')}?text=${encodeURIComponent(`Salam ${showcase.agent_name}, vitrindəki elanlarınızla bağlı əlaqə saxlayıram.`)}`}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md transition"
              >
                <MessageSquare className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">WhatsApp</span>
              </a>
              <a
                href={`tel:${showcase.agent_phone}`}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition"
              >
                <Phone className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Zəng et</span>
              </a>
            </div>
          </div>
        </header>

        {/* Content Container */}
        <main className="max-w-5xl mx-auto px-4 pt-8">
          <div className="mb-8 bg-gradient-to-r from-purple-900/30 via-indigo-900/20 to-slate-900 border border-purple-500/20 rounded-2xl p-6 sm:p-8">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <span className="inline-block px-2.5 py-1 rounded-md bg-purple-500/20 text-purple-300 text-xs font-bold uppercase tracking-wider mb-2 border border-purple-500/30">
                  Rəqəmsal Əmlak Vitrini
                </span>
                <h2 className="text-2xl sm:text-3xl font-extrabold text-white mb-1">{showcase.agent_name}</h2>
                <p className="text-slate-400 text-sm">
                  Aktual və təsdiqlənmiş əmlak təklifləri. Birbaşa vasitəçisiz və təmiz təqdimat.
                </p>
              </div>

              <div className="flex items-center gap-3 bg-slate-900/80 px-4 py-3 rounded-xl border border-slate-800 shrink-0">
                <Layers className="w-6 h-6 text-purple-400" />
                <div>
                  <div className="text-xl font-bold text-white">{showcase.active_listings_count}</div>
                  <div className="text-[11px] text-slate-400 uppercase font-semibold">Aktiv Elan</div>
                </div>
              </div>
            </div>
          </div>

          {/* Listings Grid */}
          {showcase.listings.length === 0 ? (
            <div className="text-center py-16 bg-slate-900/40 rounded-2xl border border-slate-800">
              <Home className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <h3 className="text-base font-bold text-slate-300 mb-1">Portfeldə hələlik aktiv elan yoxdur</h3>
              <p className="text-xs text-slate-500">Yaxın zamanda yeni əmlaklar əlavə olunacaq.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {showcase.listings.map((item) => (
                <a
                  key={item.id}
                  href={`/p/${item.share_code}`}
                  className="group bg-slate-900 border border-slate-800/90 hover:border-purple-500/50 rounded-2xl overflow-hidden shadow-lg transition-all duration-300 flex flex-col justify-between"
                >
                  <div>
                    {/* Thumbnail Image */}
                    <div className="aspect-[4/3] bg-slate-950 relative overflow-hidden">
                      {item.photos && item.photos.length > 0 ? (
                        <img
                          src={item.photos[0]}
                          alt={item.title}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                          loading="lazy"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center bg-slate-950 text-slate-700">
                          <Home className="w-12 h-12" />
                        </div>
                      )}
                      <div className="absolute top-3 right-3 bg-slate-950/80 backdrop-blur-md px-2.5 py-1 rounded-lg text-xs font-bold text-white border border-slate-700/50">
                        {item.price ? `${item.price.toLocaleString()} ${item.currency}` : 'Razılaşma'}
                      </div>
                    </div>

                    {/* Details */}
                    <div className="p-4 space-y-2">
                      <h3 className="text-sm font-bold text-white group-hover:text-purple-300 transition-colors line-clamp-2">
                        {item.title}
                      </h3>

                      <div className="flex items-center gap-3 text-xs text-slate-400 pt-1">
                        {item.rooms ? <span>{item.rooms} otaqlı</span> : null}
                        {item.area_sqm ? <span>• {item.area_sqm} m²</span> : null}
                        {item.district ? (
                          <span className="flex items-center gap-1 truncate">
                            • <MapPin className="w-3 h-3 text-slate-500 shrink-0" />
                            {item.district}
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </div>

                  <div className="p-4 pt-0">
                    <div className="w-full py-2 bg-slate-800 group-hover:bg-purple-600 text-slate-300 group-hover:text-white rounded-xl text-xs font-semibold text-center transition">
                      Ətraflı Bax
                    </div>
                  </div>
                </a>
              ))}
            </div>
          )}
        </main>
      </div>
    );
  }

  if (!listing) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-center text-slate-300">
        <Building className="w-12 h-12 text-slate-600 mb-3" />
        <h2 className="text-lg font-bold text-white mb-1">Elan tapılmadı</h2>
        <p className="text-sm text-slate-400">Bu elan mövcud deyil və ya portfeldən silinib.</p>
      </div>
    );
  }

  // --- SINGLE PROPERTY CLIENT LANDING VIEW ---
  const photos = listing.photos && listing.photos.length > 0 ? listing.photos : [];
  const currentPhoto = photos[activePhotoIdx] || null;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 selection:bg-purple-500 selection:text-white pb-24">
      {/* Top Bar */}
      <header className="sticky top-0 z-40 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 px-4 py-3">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <a
              href={listing.agent_vitrin_url || `/v/${listing.agent_slug || ''}`}
              className="flex items-center gap-2 group hover:opacity-90 transition"
              title="Agentin bütün elanlarına bax"
            >
              <div className="w-9 h-9 rounded-xl bg-purple-600/20 border border-purple-500/30 flex items-center justify-center text-purple-300 font-bold text-sm group-hover:bg-purple-600 group-hover:text-white transition">
                {listing.agent_name.charAt(0).toUpperCase()}
              </div>
              <div>
                <div className="text-xs font-bold text-white flex items-center gap-1.5 group-hover:text-purple-300 transition">
                  <span>{listing.agent_name}</span>
                  <CheckCircle2 className="w-3.5 h-3.5 text-purple-400" />
                </div>
                <div className="text-[10px] text-slate-400 font-medium flex items-center gap-1">
                  <span>Vitrin</span>
                  <span>•</span>
                  <span className="text-purple-400 underline decoration-purple-400/50">Bütün Elanlar</span>
                </div>
              </div>
            </a>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopyLink}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 transition"
              title="Linki Kopyala"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Share2 className="w-3.5 h-3.5" />}
              <span className="hidden sm:inline">{copied ? 'Kopyalandı' : 'Paylaş'}</span>
            </button>

            <a
              href={`tel:${listing.agent_phone}`}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition"
            >
              <Phone className="w-3.5 h-3.5 text-purple-400" />
              <span className="hidden sm:inline">{listing.agent_phone}</span>
            </a>

            <a
              href={listing.whatsapp_message_url}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-md shadow-emerald-600/20 transition"
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span>WhatsApp</span>
            </a>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-6xl mx-auto px-4 pt-6">
        {/* Title & Badges Header */}
        <div className="mb-6 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-md bg-purple-500/20 text-purple-300 border border-purple-500/30 text-xs font-bold uppercase tracking-wider">
              {getOfferTypeLabel(listing.offer_type)}
            </span>
            <span className="px-2.5 py-0.5 rounded-md bg-slate-800 text-slate-300 border border-slate-700 text-xs font-semibold">
              {getPropertyTypeLabel(listing.property_type)}
            </span>
            {listing.building_type && (
              <span className="px-2.5 py-0.5 rounded-md bg-slate-800/80 text-slate-400 text-xs">
                {listing.building_type === 'new' ? 'Yeni tikili' : 'Köhnə tikili'}
              </span>
            )}
          </div>

          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h1 className="text-xl sm:text-2xl md:text-3xl font-extrabold text-white tracking-tight">
                {listing.title}
              </h1>

              <div className="flex items-center gap-2 text-slate-400 text-xs sm:text-sm mt-1.5">
                <MapPin className="w-4 h-4 text-purple-400 shrink-0" />
                <span>
                  {[listing.district, listing.metro_station, listing.address].filter(Boolean).join(', ') || 'Bakı'}
                </span>
              </div>
            </div>

            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 md:text-right shrink-0">
              <div className="text-2xl sm:text-3xl font-black text-emerald-400 font-mono">
                {listing.price ? listing.price.toLocaleString() : '0'} {listing.currency}
              </div>
              {listing.price_usd && (
                <div className="text-xs text-slate-400 font-mono mt-0.5">
                  ≈ ${listing.price_usd.toLocaleString()} USD
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Photo Gallery Carousel */}
        {photos.length > 0 && (
          <div className="mb-8 space-y-3">
            {/* Main Active Photo */}
            <div className="relative aspect-[16/10] sm:aspect-[16/9] md:aspect-[21/9] bg-slate-950 rounded-3xl overflow-hidden border border-slate-800 group shadow-2xl">
              <img
                src={currentPhoto!}
                alt={listing.title}
                className="w-full h-full object-contain sm:object-cover bg-black cursor-pointer"
                onClick={() => setLightboxOpen(true)}
              />

              {/* Navigation Arrows */}
              {photos.length > 1 && (
                <>
                  <button
                    onClick={() => setActivePhotoIdx((prev) => (prev > 0 ? prev - 1 : photos.length - 1))}
                    className="absolute left-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/60 hover:bg-black/80 text-white flex items-center justify-center backdrop-blur-sm border border-white/10 transition"
                  >
                    <ChevronLeft className="w-6 h-6" />
                  </button>
                  <button
                    onClick={() => setActivePhotoIdx((prev) => (prev < photos.length - 1 ? prev + 1 : 0))}
                    className="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/60 hover:bg-black/80 text-white flex items-center justify-center backdrop-blur-sm border border-white/10 transition"
                  >
                    <ChevronRight className="w-6 h-6" />
                  </button>
                </>
              )}

              {/* Photo Counter & Fullscreen trigger */}
              <div className="absolute bottom-3 right-3 flex items-center gap-2">
                <span className="px-3 py-1 rounded-xl bg-black/70 backdrop-blur-md text-white text-xs font-bold border border-white/10">
                  {activePhotoIdx + 1} / {photos.length}
                </span>
                <button
                  onClick={() => setLightboxOpen(true)}
                  className="w-8 h-8 rounded-xl bg-black/70 backdrop-blur-md text-white flex items-center justify-center border border-white/10 hover:bg-black/90 transition"
                >
                  <Maximize2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Thumbnails Strip */}
            {photos.length > 1 && (
              <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-thin">
                {photos.map((url, idx) => (
                  <button
                    key={idx}
                    onClick={() => setActivePhotoIdx(idx)}
                    className={`relative w-20 sm:w-24 aspect-video rounded-xl overflow-hidden shrink-0 border-2 transition ${
                      activePhotoIdx === idx ? 'border-purple-500 scale-95 shadow-md shadow-purple-500/30' : 'border-slate-800 opacity-60 hover:opacity-100'
                    }`}
                  >
                    <img src={url} alt={`Şəkil ${idx + 1}`} className="w-full h-full object-cover" />
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Property Key Specs Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
          <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-4">
            <div className="text-xs text-slate-400 font-medium mb-1">Otaq sayı</div>
            <div className="text-lg sm:text-xl font-bold text-white">{listing.rooms ? `${listing.rooms} otaqlı` : '—'}</div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-4">
            <div className="text-xs text-slate-400 font-medium mb-1">Ümumi sahə</div>
            <div className="text-lg sm:text-xl font-bold text-white">{listing.area_sqm ? `${listing.area_sqm} m²` : '—'}</div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-4">
            <div className="text-xs text-slate-400 font-medium mb-1">Mərtəbə</div>
            <div className="text-lg sm:text-xl font-bold text-white">
              {listing.floor ? `${listing.floor}${listing.total_floors ? ` / ${listing.total_floors}` : ''}` : '—'}
            </div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-4">
            <div className="text-xs text-slate-400 font-medium mb-1">Əmlak Növü</div>
            <div className="text-lg sm:text-xl font-bold text-purple-300">{getPropertyTypeLabel(listing.property_type)}</div>
          </div>
        </div>

        {/* Content Layout: Description (Left) + Agent Card (Right) */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column: Description & Details */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-4">
              <h2 className="text-lg font-bold text-white">Əmlak Haqqında Məlumat</h2>
              <div className="text-sm text-slate-300 leading-relaxed whitespace-pre-line">
                {listing.description || 'Ətraflı məlumat üçün agentlə əlaqə saxlayın.'}
              </div>
            </div>

            {/* Additional Features Breakdown */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-6 sm:p-8">
              <h3 className="text-base font-bold text-white mb-4">Əsas Göstəricilər</h3>
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-xs">
                <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                  <dt className="text-slate-400">Təklif növü:</dt>
                  <dd className="text-white font-semibold">{getOfferTypeLabel(listing.offer_type)}</dd>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                  <dt className="text-slate-400">Kateqoriya:</dt>
                  <dd className="text-white font-semibold">{getPropertyTypeLabel(listing.property_type)}</dd>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                  <dt className="text-slate-400">Rayon:</dt>
                  <dd className="text-white font-semibold">{listing.district || '—'}</dd>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                  <dt className="text-slate-400">Metro:</dt>
                  <dd className="text-white font-semibold">{listing.metro_station || '—'}</dd>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                  <dt className="text-slate-400">Bina növü:</dt>
                  <dd className="text-white font-semibold">{listing.building_type === 'new' ? 'Yeni tikili' : 'Köhnə tikili'}</dd>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                  <dt className="text-slate-400">Kod / ID:</dt>
                  <dd className="text-purple-300 font-mono font-bold">#{listing.id}</dd>
                </div>
              </dl>
            </div>
          </div>

          {/* Right Column: Branded Agent Contact Card */}
          <div className="space-y-6">
            <div className="bg-gradient-to-b from-slate-900 to-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-7 space-y-6 shadow-xl sticky top-20">
              <div className="text-center space-y-2">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-purple-600 to-indigo-600 flex items-center justify-center font-bold text-2xl text-white mx-auto shadow-lg shadow-purple-600/30">
                  {listing.agent_name.charAt(0).toUpperCase()}
                </div>
                <h3 className="text-lg font-bold text-white">{listing.agent_name}</h3>
                <p className="text-xs text-slate-400 flex items-center justify-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5 text-purple-400" />
                  <span>Təsdiqlənmiş Əmlak Eksperti</span>
                </p>
              </div>

              {/* Action Buttons */}
              <div className="space-y-2.5">
                <a
                  href={listing.whatsapp_message_url}
                  target="_blank"
                  rel="noreferrer"
                  className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm shadow-lg shadow-emerald-600/25 transition"
                >
                  <MessageSquare className="w-4 h-4" />
                  <span>WhatsApp İlə Əlaqə Saxla</span>
                </a>

                <a
                  href={`tel:${listing.agent_phone}`}
                  className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-sm border border-slate-700 transition"
                >
                  <Phone className="w-4 h-4 text-purple-400" />
                  <span>{listing.agent_phone}</span>
                </a>
              </div>

              <div className="pt-4 border-t border-slate-800/80 space-y-3">
                <button
                  onClick={handleCopyLink}
                  className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-slate-950/60 hover:bg-slate-800 text-slate-400 hover:text-slate-200 text-xs font-semibold border border-slate-800 transition"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Share2 className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Link Kopyalandı!' : 'Elanın Linkini Paylaş'}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Floating Bottom Contact Bar on Mobile */}
      <div className="fixed bottom-0 inset-x-0 bg-slate-900/95 backdrop-blur-md border-t border-slate-800 p-3 sm:hidden z-40 flex items-center gap-2">
        <a
          href={`tel:${listing.agent_phone}`}
          className="flex-1 flex items-center justify-center gap-1.5 py-3 rounded-xl bg-slate-800 text-slate-200 text-xs font-bold border border-slate-700"
        >
          <Phone className="w-4 h-4 text-purple-400" />
          <span>Zəng et</span>
        </a>
        <a
          href={listing.whatsapp_message_url}
          target="_blank"
          rel="noreferrer"
          className="flex-1 flex items-center justify-center gap-1.5 py-3 rounded-xl bg-emerald-600 text-white text-xs font-bold shadow-md shadow-emerald-600/30"
        >
          <MessageSquare className="w-4 h-4" />
          <span>WhatsApp</span>
        </a>
      </div>

      {/* Fullscreen Lightbox Modal */}
      {lightboxOpen && photos.length > 0 && (
        <div className="fixed inset-0 bg-black/95 z-50 flex flex-col items-center justify-between p-4">
          <div className="w-full flex items-center justify-between text-white p-2">
            <span className="text-xs font-mono font-bold">
              {activePhotoIdx + 1} / {photos.length}
            </span>
            <button
              onClick={() => setLightboxOpen(false)}
              className="p-2 text-slate-400 hover:text-white rounded-full bg-white/10"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          <div className="relative max-w-5xl w-full flex-1 flex items-center justify-center p-2">
            <img
              src={photos[activePhotoIdx]}
              alt={`Tam ekran şəkil ${activePhotoIdx + 1}`}
              className="max-h-[80vh] max-w-full object-contain"
            />

            {photos.length > 1 && (
              <>
                <button
                  onClick={() => setActivePhotoIdx((prev) => (prev > 0 ? prev - 1 : photos.length - 1))}
                  className="absolute left-2 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-black/60 text-white flex items-center justify-center"
                >
                  <ChevronLeft className="w-8 h-8" />
                </button>
                <button
                  onClick={() => setActivePhotoIdx((prev) => (prev < photos.length - 1 ? prev + 1 : 0))}
                  className="absolute right-2 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-black/60 text-white flex items-center justify-center"
                >
                  <ChevronRight className="w-8 h-8" />
                </button>
              </>
            )}
          </div>

          {/* Bottom Thumbnails */}
          <div className="w-full max-w-2xl flex gap-2 overflow-x-auto p-2">
            {photos.map((u, i) => (
              <button
                key={i}
                onClick={() => setActivePhotoIdx(i)}
                className={`w-16 h-12 rounded-lg overflow-hidden shrink-0 border-2 ${
                  activePhotoIdx === i ? 'border-purple-500' : 'border-transparent opacity-50'
                }`}
              >
                <img src={u} alt="" className="w-full h-full object-cover" />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
