import React, { useEffect, useState } from 'react';
import { MapPin, TrendingDown, Layers, Search, Filter, ExternalLink, ShieldAlert, Sparkles, Building, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react';
import api from '../api';

interface DistrictHeatmap {
  district: string;
  lat: number;
  lng: number;
  active_count: number;
  avg_price_per_sqm: number;
  bargain_deals_count: number;
}

interface PropertyPin {
  id: number;
  title: string;
  source_name?: string;
  price: number;
  currency: string;
  district?: string;
  metro_station?: string;
  rooms?: number;
  area_sqm?: number;
  price_per_sqm?: number;
  bargain_percentage: number;
  is_bargain: boolean;
  lat: number;
  lng: number;
  listing_url: string;
}

export const BakuPropertyMap: React.FC = () => {
  const [heatmap, setHeatmap] = useState<DistrictHeatmap[]>([]);
  const [pins, setPins] = useState<PropertyPin[]>([]);
  const [totalActiveListings, setTotalActiveListings] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [fetchLimit, setFetchLimit] = useState<number>(1000);
  const [selectedDistrict, setSelectedDistrict] = useState<string>('all');
  const [filterBargainOnly, setFilterBargainOnly] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPin, setSelectedPin] = useState<PropertyPin | null>(null);

  // Pagination state
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(18);

  const getSourceBadgeColor = (source?: string) => {
    switch ((source || '').toLowerCase()) {
      case 'bina.az':
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
      case 'tap.az':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/30';
      case 'yeniemlak.az':
        return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
      case 'lalafo.az':
        return 'bg-purple-500/20 text-purple-300 border-purple-500/30';
      case 'evonline.az':
        return 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30';
      case 'binam.az':
        return 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30';
      case 'ipoteka.az':
        return 'bg-rose-500/20 text-rose-300 border-rose-500/30';
      case 'ev10.az':
        return 'bg-teal-500/20 text-teal-300 border-teal-500/30';
      case 'vipemlak.az':
        return 'bg-amber-400/20 text-amber-200 border-amber-400/30';
      default:
        return 'bg-slate-700/50 text-slate-300 border-slate-600';
    }
  };

  const getValidExternalUrl = (url?: string) => {
    if (!url) return '#';
    const trimmed = url.trim();
    if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
      if (trimmed.startsWith('/')) {
        return `https://bina.az${trimmed}`;
      }
      return `https://${trimmed}`;
    }
    return trimmed;
  };

  const fetchMapData = async (limitToFetch: number = fetchLimit) => {
    setLoading(true);
    try {
      const res = await api.get(`/analytics/map?limit=${limitToFetch}`);
      setHeatmap(res.data.districts_heatmap || []);
      setPins(res.data.property_pins || []);
      setTotalActiveListings(res.data.total_active_listings || res.data.property_pins?.length || 0);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMapData(fetchLimit);
  }, [fetchLimit]);

  const handleDistrictChange = (district: string) => {
    setSelectedDistrict(district);
    setCurrentPage(1);
  };

  const handleBargainFilterToggle = () => {
    setFilterBargainOnly(!filterBargainOnly);
    setCurrentPage(1);
  };

  const handleSearchChange = (val: string) => {
    setSearchQuery(val);
    setCurrentPage(1);
  };

  const filteredPins = pins.filter(p => {
    const pDistrict = (p.district || '').toLowerCase();
    const pTitle = (p.title || '').toLowerCase();
    const pMetro = (p.metro_station || '').toLowerCase();
    const pSource = (p.source_name || '').toLowerCase();
    const q = (searchQuery || '').toLowerCase().trim();

    const matchesDistrict = selectedDistrict === 'all' || pDistrict === selectedDistrict.toLowerCase();
    const matchesBargain = !filterBargainOnly || p.is_bargain;
    const matchesSearch = !q || (
      pTitle.includes(q) ||
      pMetro.includes(q) ||
      pSource.includes(q) ||
      pDistrict.includes(q)
    );
    return matchesDistrict && matchesBargain && matchesSearch;
  });

  const totalPages = Math.max(1, Math.ceil(filteredPins.length / pageSize));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const startIndex = (safeCurrentPage - 1) * pageSize;
  const paginatedPins = filteredPins.slice(startIndex, startIndex + pageSize);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <MapPin className="w-5 h-5 text-emerald-400" />
            Baku Interactive Price/m² Heatmap & Deal Map
          </h2>
          <p className="text-slate-400 text-xs mt-0.5">
            Real-time district valuation heatmap, price per sqm analysis, and urgent bargain property locations.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Limit selector */}
          <div className="flex items-center gap-1.5 bg-dark-800 border border-slate-700/60 rounded-xl px-2.5 py-1 text-xs text-slate-300">
            <span className="text-slate-400 text-[11px]">Load:</span>
            <select
              value={fetchLimit}
              onChange={(e) => setFetchLimit(Number(e.target.value))}
              className="bg-transparent text-emerald-400 font-semibold focus:outline-none cursor-pointer"
            >
              <option value={200} className="bg-dark-900 text-white">200 Pins</option>
              <option value={500} className="bg-dark-900 text-white">500 Pins</option>
              <option value={1000} className="bg-dark-900 text-white">1,000 Pins</option>
              <option value={2500} className="bg-dark-900 text-white">2,500 Pins</option>
              <option value={5000} className="bg-dark-900 text-white">5,000 Pins (All)</option>
            </select>
          </div>

          <button
            onClick={() => fetchMapData(fetchLimit)}
            disabled={loading}
            className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold px-3.5 py-2 rounded-xl transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* District Heatmap Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {heatmap.slice(0, 8).map(d => (
          <div
            key={d.district}
            onClick={() => handleDistrictChange(selectedDistrict === d.district ? 'all' : d.district)}
            className={`p-3.5 rounded-2xl border transition-all cursor-pointer ${
              selectedDistrict === d.district
                ? 'bg-emerald-500/20 border-emerald-500/50 shadow-lg shadow-emerald-500/10'
                : 'glass-card border-slate-800 hover:border-slate-700'
            }`}
          >
            <div className="flex justify-between items-start">
              <span className="text-xs font-bold text-white">{d.district}</span>
              {d.bargain_deals_count > 0 && (
                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-semibold flex items-center gap-1">
                  <Sparkles className="w-2.5 h-2.5" /> {d.bargain_deals_count} Bargains
                </span>
              )}
            </div>
            <div className="mt-2 text-lg font-extrabold text-emerald-400">
              {d.avg_price_per_sqm > 0 ? `${Math.round(d.avg_price_per_sqm).toLocaleString()} AZN/m²` : '—'}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">{d.active_count} Active Listings</div>
          </div>
        ))}
      </div>

      {/* Interactive Map Visual Grid */}
      <div className="glass-card rounded-2xl border border-slate-800 p-5 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2 flex-wrap">
            <Layers className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-bold text-white">
              Baku Property Pins ({filteredPins.length})
            </h3>
            {totalActiveListings > 0 && (
              <span className="text-[11px] text-slate-500 font-mono">
                / {totalActiveListings.toLocaleString()} Active in DB
              </span>
            )}
            {selectedDistrict !== 'all' && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-mono">
                {selectedDistrict}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search title, metro, source..."
                value={searchQuery}
                onChange={(e) => handleSearchChange(e.target.value)}
                className="bg-dark-900/80 border border-slate-700/60 rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder:text-slate-500 w-44 focus:w-56 transition-all focus:outline-none focus:border-emerald-500"
              />
            </div>

            <button
              onClick={handleBargainFilterToggle}
              className={`text-xs px-3 py-1.5 rounded-xl border flex items-center gap-1.5 font-medium transition-all ${
                filterBargainOnly
                  ? 'bg-emerald-500 text-dark-900 border-emerald-400 font-bold'
                  : 'bg-dark-800 text-slate-300 border-slate-700 hover:bg-dark-700'
              }`}
            >
              <TrendingDown className="w-3.5 h-3.5" />
              Bargains Only (-10%+)
            </button>

            {selectedDistrict !== 'all' && (
              <button
                onClick={() => handleDistrictChange('all')}
                className="text-xs text-slate-400 hover:text-white px-2 py-1"
              >
                Clear District
              </button>
            )}
          </div>
        </div>

        {/* Property Pins Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 min-h-[300px]">
          {paginatedPins.map(p => (
            <div
              key={p.id}
              onClick={() => setSelectedPin(p)}
              className={`p-3.5 rounded-xl border transition-all cursor-pointer space-y-2 flex flex-col justify-between ${
                p.is_bargain
                  ? 'bg-emerald-500/10 border-emerald-500/40 hover:bg-emerald-500/20 shadow-sm'
                  : 'bg-dark-800/80 border-slate-700 hover:bg-dark-700'
              }`}
            >
              <div className="space-y-2">
                <div className="flex justify-between items-start gap-2">
                  <span className="text-xs font-bold text-white truncate max-w-[180px]">{p.title}</span>
                  <div className="flex items-center gap-1 shrink-0">
                    <span className={`text-[10px] px-2 py-0.5 rounded-md border font-semibold ${getSourceBadgeColor(p.source_name)}`}>
                      {p.source_name || 'Bina.az'}
                    </span>
                    {p.is_bargain ? (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-emerald-500 text-dark-900 font-extrabold flex items-center gap-0.5">
                        <TrendingDown className="w-2.5 h-2.5" /> {p.bargain_percentage}%
                      </span>
                    ) : null}
                  </div>
                </div>

                <div className="flex items-baseline gap-2">
                  <span className="text-base font-extrabold text-emerald-400">
                    {Math.round(p.price).toLocaleString()} {p.currency}
                  </span>
                  {p.price_per_sqm && p.price_per_sqm > 0 ? (
                    <span className="text-xs text-slate-400 font-medium">
                      ({Math.round(p.price_per_sqm).toLocaleString()} AZN/m²)
                    </span>
                  ) : null}
                </div>
              </div>

              <div className="flex items-center gap-2 text-[11px] text-slate-400 pt-1 border-t border-slate-800/60">
                <span className="flex items-center gap-1 text-slate-300">
                  <MapPin className="w-3 h-3 text-emerald-400" /> {p.district || 'Bakı'}
                </span>
                {p.metro_station && (
                  <span className="text-amber-400 font-medium">🚇 {p.metro_station}</span>
                )}
                <span>• {p.rooms || '-'} otaq</span>
                <span>• {p.area_sqm || '-'} m²</span>
              </div>
            </div>
          ))}

          {filteredPins.length === 0 && !loading && (
            <div className="col-span-full p-12 text-center text-slate-500">
              No property pins found for the selected district or filter criteria.
            </div>
          )}
        </div>

        {/* Pagination Bar */}
        {filteredPins.length > 0 && (
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-slate-800/80 text-xs">
            <div className="text-slate-400 flex items-center gap-2">
              <span>
                Showing <strong className="text-white font-mono">{startIndex + 1}</strong> to{' '}
                <strong className="text-white font-mono">{Math.min(startIndex + pageSize, filteredPins.length)}</strong> of{' '}
                <strong className="text-white font-mono">{filteredPins.length}</strong> matching properties
              </span>
              <div className="flex items-center gap-1 pl-2 border-l border-slate-700">
                <span className="text-slate-500 text-[11px]">Per page:</span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="bg-dark-800 border border-slate-700 text-slate-300 rounded px-1.5 py-0.5 text-xs focus:outline-none"
                >
                  <option value={18}>18</option>
                  <option value={36}>36</option>
                  <option value={72}>72</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={safeCurrentPage <= 1}
                className="px-2.5 py-1 rounded-lg bg-dark-800 text-slate-300 hover:bg-dark-700 disabled:opacity-40 disabled:hover:bg-dark-800 flex items-center gap-1 border border-slate-700/60"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Prev</span>
              </button>

              <div className="flex items-center gap-1 font-mono">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let pageNum: number;
                  if (totalPages <= 5) {
                    pageNum = i + 1;
                  } else if (safeCurrentPage <= 3) {
                    pageNum = i + 1;
                  } else if (safeCurrentPage >= totalPages - 2) {
                    pageNum = totalPages - 4 + i;
                  } else {
                    pageNum = safeCurrentPage - 2 + i;
                  }
                  return (
                    <button
                      key={pageNum}
                      onClick={() => setCurrentPage(pageNum)}
                      className={`w-7 h-7 rounded-lg text-xs font-semibold transition-all ${
                        safeCurrentPage === pageNum
                          ? 'bg-emerald-500 text-dark-950 font-bold shadow-md shadow-emerald-500/20'
                          : 'bg-dark-800 text-slate-300 hover:bg-dark-700 border border-slate-700/60'
                      }`}
                    >
                      {pageNum}
                    </button>
                  );
                })}
              </div>

              <button
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                disabled={safeCurrentPage >= totalPages}
                className="px-2.5 py-1 rounded-lg bg-dark-800 text-slate-300 hover:bg-dark-700 disabled:opacity-40 disabled:hover:bg-dark-800 flex items-center gap-1 border border-slate-700/60"
              >
                <span>Next</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Property Pin Detail Modal */}
      {selectedPin && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card w-full max-w-md p-6 rounded-2xl border border-slate-800 space-y-4">
            <div className="flex justify-between items-start">
              <div>
                <div className="flex items-center gap-2">
                  <span className={`text-[11px] px-2.5 py-0.5 rounded-md border font-semibold ${getSourceBadgeColor(selectedPin.source_name)}`}>
                    🌐 {selectedPin.source_name || 'Bina.az'}
                  </span>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                    {selectedPin.district ? `${selectedPin.district} District` : 'Baku'} {selectedPin.metro_station ? `• ${selectedPin.metro_station} Metro` : ''}
                  </span>
                </div>
                <h3 className="text-base font-bold text-white mt-1.5">{selectedPin.title}</h3>
              </div>
              <button onClick={() => setSelectedPin(null)} className="text-slate-400 hover:text-white">&times;</button>
            </div>

            <div className="p-3 bg-dark-900 rounded-xl border border-slate-800 space-y-2 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Source Portal:</span>
                <span className={`text-xs px-2 py-0.5 rounded font-semibold border ${getSourceBadgeColor(selectedPin.source_name)}`}>
                  {selectedPin.source_name || 'Bina.az'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Total Price:</span>
                <strong className="text-base font-extrabold text-emerald-400">{Math.round(selectedPin.price).toLocaleString()} {selectedPin.currency}</strong>
              </div>
              {selectedPin.price_per_sqm && (
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Price per m²:</span>
                  <strong className="text-slate-200">{Math.round(selectedPin.price_per_sqm)} AZN / m²</strong>
                </div>
              )}
              {selectedPin.is_bargain && (
                <div className="p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400 text-xs font-semibold flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4" /> This listing is {Math.abs(selectedPin.bargain_percentage)}% below historical district average!
                </div>
              )}
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setSelectedPin(null)}
                className="px-4 py-2 text-xs text-slate-400 hover:text-white"
              >
                Close
              </button>
              <a
                href={getValidExternalUrl(selectedPin.listing_url)}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 text-xs font-semibold bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl flex items-center gap-1.5 shadow-lg shadow-emerald-500/20"
              >
                <span>View on {selectedPin.source_name || 'Portal'}</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
