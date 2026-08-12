import React, { useEffect, useState } from 'react';
import { MapPin, TrendingDown, Layers, Search, Filter, ExternalLink, ShieldAlert, Sparkles, Building, RefreshCw } from 'lucide-react';
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
  price: number;
  currency: string;
  district: string;
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
  const [loading, setLoading] = useState(true);
  const [selectedDistrict, setSelectedDistrict] = useState<string>('all');
  const [filterBargainOnly, setFilterBargainOnly] = useState(false);
  const [selectedPin, setSelectedPin] = useState<PropertyPin | null>(null);

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

  const fetchMapData = async () => {
    setLoading(true);
    try {
      const res = await api.get('/analytics/map');
      setHeatmap(res.data.districts_heatmap || []);
      setPins(res.data.property_pins || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMapData();
  }, []);

  const filteredPins = pins.filter(p => {
    const matchesDistrict = selectedDistrict === 'all' || p.district.toLowerCase() === selectedDistrict.toLowerCase();
    const matchesBargain = !filterBargainOnly || p.is_bargain;
    return matchesDistrict && matchesBargain;
  });

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
        <button
          onClick={fetchMapData}
          disabled={loading}
          className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold px-3.5 py-2 rounded-xl transition-all"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh Map Data
        </button>
      </div>

      {/* District Heatmap Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {heatmap.slice(0, 8).map(d => (
          <div
            key={d.district}
            onClick={() => setSelectedDistrict(selectedDistrict === d.district ? 'all' : d.district)}
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

      {/* Map Controls */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-dark-800/80 p-3 rounded-2xl border border-slate-800">
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="flex items-center gap-1.5 text-xs text-slate-300">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <span>District:</span>
          </div>
          <select
            value={selectedDistrict}
            onChange={(e) => setSelectedDistrict(e.target.value)}
            className="glass-input px-3 py-1.5 rounded-xl text-xs text-white bg-dark-900 border border-slate-700"
          >
            <option value="all">All Baku Districts ({pins.length} pins)</option>
            {heatmap.map(h => (
              <option key={h.district} value={h.district}>{h.district} ({h.active_count} listings)</option>
            ))}
          </select>
        </div>

        <button
          onClick={() => setFilterBargainOnly(!filterBargainOnly)}
          className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-xl border transition-all ${
            filterBargainOnly
              ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
              : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-white'
          }`}
        >
          <TrendingDown className="w-3.5 h-3.5" />
          <span>Only Urgent Bargains (-10%+ Below Market)</span>
        </button>
      </div>

      {/* Visual Interactive Map Canvas */}
      <div className="glass-card rounded-2xl border border-slate-800 p-4 relative min-h-[450px] overflow-hidden flex flex-col justify-between">
        {/* Background Grid Map Layout */}
        <div className="absolute inset-0 bg-dark-950 opacity-90 flex items-center justify-center pointer-events-none">
          <div className="w-full h-full bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:16px_16px] opacity-40"></div>
        </div>

        {/* Pins Map Display */}
        <div className="relative z-10 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {filteredPins.map(p => (
            <div
              key={p.id}
              onClick={() => setSelectedPin(p)}
              className={`p-3.5 rounded-xl border transition-all cursor-pointer space-y-2 ${
                p.is_bargain
                  ? 'bg-emerald-500/10 border-emerald-500/40 hover:bg-emerald-500/20'
                  : 'bg-dark-800/80 border-slate-700 hover:bg-dark-700'
              }`}
            >
              <div className="flex justify-between items-start">
                <span className="text-xs font-bold text-white truncate max-w-[200px]">{p.title}</span>
                {p.is_bargain ? (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500 text-dark-900 font-extrabold flex items-center gap-1">
                    <TrendingDown className="w-3 h-3" /> {p.bargain_percentage}%
                  </span>
                ) : (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                    Fair Price
                  </span>
                )}
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

              <div className="flex items-center gap-2 text-[11px] text-slate-400">
                <span className="flex items-center gap-1 text-slate-300">
                  <MapPin className="w-3 h-3 text-emerald-400" /> {p.district}
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

        {/* Legend Footer */}
        <div className="relative z-10 pt-4 mt-4 border-t border-slate-800 flex flex-wrap items-center justify-between text-xs text-slate-400 gap-2">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span> Bargain (-10%+ Below Market)</span>
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-blue-500"></span> Fair Market Value</span>
          </div>
          <span>Showing {filteredPins.length} Baku property pins</span>
        </div>
      </div>

      {/* Property Pin Detail Modal */}
      {selectedPin && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card w-full max-w-md p-6 rounded-2xl border border-slate-800 space-y-4">
            <div className="flex justify-between items-start">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                  {selectedPin.district} District {selectedPin.metro_station ? `• ${selectedPin.metro_station} Metro` : ''}
                </span>
                <h3 className="text-base font-bold text-white mt-1">{selectedPin.title}</h3>
              </div>
              <button onClick={() => setSelectedPin(null)} className="text-slate-400 hover:text-white">&times;</button>
            </div>

            <div className="p-3 bg-dark-900 rounded-xl border border-slate-800 space-y-2 text-xs">
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
                className="px-4 py-2 text-xs font-semibold bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl flex items-center gap-1.5"
              >
                <span>View Original Listing</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
