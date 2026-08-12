import React, { useEffect, useState } from 'react';
import { UserPlus, Search, ShieldCheck, Clock, AlertCircle, Phone, MessageSquare, Plus, CheckCircle, QrCode, RefreshCw, CheckCircle2, Wifi, WifiOff } from 'lucide-react';
import api from '../api';
import { Tenant, SavedSearch } from '../types';

export const TenantsView: React.FC = () => {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTenant, setSelectedTenant] = useState<{ tenant: Tenant; saved_searches: SavedSearch[] } | null>(null);
  
  // Modals
  const [showAddModal, setShowAddModal] = useState(false);
  const [newTenant, setNewTenant] = useState({
    name: '',
    phone: '',
    type: 'individual_agent',
    preferred_channel: 'telegram',
    plan: 'starter',
    telegram_handle: '',
    whatsapp_number: '',
    backup_enabled: false,
    backup_frequency_days: 7
  });

  const [availablePlans, setAvailablePlans] = useState<any[]>([]);

  // WhatsApp Evolution API Pairing State
  const [waStatus, setWaStatus] = useState<{ connected: boolean; state: string; instance_name: string } | null>(null);
  const [waQrCode, setWaQrCode] = useState<string | null>(null);
  const [waPairingCode, setWaPairingCode] = useState<string | null>(null);
  const [waLoading, setWaLoading] = useState(false);

  const loadTenants = async () => {
    setLoading(true);
    try {
      const [tRes, pRes] = await Promise.all([
        api.get('/tenants'),
        api.get('/plans').catch(() => ({ data: [] }))
      ]);
      setTenants(tRes.data || []);
      setAvailablePlans(pRes.data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTenants();
  }, []);

  const checkWhatsAppStatus = async (instName?: string) => {
    try {
      const res = await api.get('/whatsapp/status', {
        params: { instance_name: instName || 'realestate_agent' }
      });
      setWaStatus(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const generateWhatsAppQrCode = async (instName?: string) => {
    setWaLoading(true);
    setWaQrCode(null);
    setWaPairingCode(null);
    try {
      const res = await api.post('/whatsapp/qrcode', {
        instance_name: instName || 'realestate_agent'
      });
      if (res.data && res.data.qrcode) {
        let qr = res.data.qrcode;
        if (!qr.startsWith('data:image')) {
          qr = `data:image/png;base64,${qr}`;
        }
        setWaQrCode(qr);
        setWaPairingCode(res.data.pairing_code || null);
      } else {
        alert(res.data?.detail || 'WhatsApp instance already connected or initializing...');
      }
      checkWhatsAppStatus(instName);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to generate WhatsApp QR Code.');
    } finally {
      setWaLoading(false);
    }
  };

  const handleCreateTenant = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api.post('/tenants', newTenant);
      setShowAddModal(false);
      loadTenants();

      // If WhatsApp preferred, auto-check status
      if (newTenant.preferred_channel === 'whatsapp') {
        checkWhatsAppStatus(`tenant_${res.data.id}`);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleStatusChange = async (tenantId: number, status: string) => {
    try {
      await api.patch(`/tenants/${tenantId}`, { status });
      loadTenants();
    } catch (e) {
      console.error(e);
    }
  };

  const handleSelectTenant = async (tenantId: number) => {
    try {
      const res = await api.get(`/tenants/${tenantId}`);
      setSelectedTenant(res.data);
      if (res.data.tenant.preferred_channel === 'whatsapp') {
        checkWhatsAppStatus(`tenant_${tenantId}`);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const filteredTenants = tenants.filter(t => 
    t.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    t.phone.includes(searchTerm)
  );

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white">Tenant & Agent Management</h2>
          <p className="text-slate-400 text-xs mt-0.5">Manage agents, subscription plans, and direct WhatsApp / Telegram channel routing.</p>
        </div>
        <button
          onClick={() => {
            setWaQrCode(null);
            setShowAddModal(true);
          }}
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
          placeholder="Search tenants by name or phone..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full glass-input pl-11 pr-4 py-2.5 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
        />
      </div>

      {/* Tenants Table */}
      <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-dark-800/80 text-slate-400 font-medium text-xs uppercase tracking-wider border-b border-slate-800">
            <tr>
              <th className="p-4">Agent / Tenant</th>
              <th className="p-4">Type</th>
              <th className="p-4">Channel</th>
              <th className="p-4">Plan</th>
              <th className="p-4">Status</th>
              <th className="p-4">Expires</th>
              <th className="p-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {filteredTenants.map((t) => (
              <tr key={t.id} className="hover:bg-dark-700/30 transition-colors">
                <td className="p-4">
                  <div className="font-semibold text-white">{t.name}</div>
                  <div className="text-xs text-slate-400">{t.phone}</div>
                </td>
                <td className="p-4 capitalize">{t.type.replace('_', ' ')}</td>
                <td className="p-4">
                  <span className={`inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-medium ${
                    t.preferred_channel === 'whatsapp' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                  }`}>
                    {t.preferred_channel === 'whatsapp' ? 'WhatsApp' : 'Telegram'}
                  </span>
                </td>
                <td className="p-4 capitalize font-medium text-slate-200">{t.plan}</td>
                <td className="p-4">
                  <span className={`inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-medium ${
                    t.status === 'active' ? 'bg-emerald-500/10 text-emerald-400' :
                    t.status === 'pending' ? 'bg-amber-500/10 text-amber-400' : 'bg-red-500/10 text-red-400'
                  }`}>
                    {t.status}
                  </span>
                </td>
                <td className="p-4 text-xs text-slate-400">
                  {t.plan_expires_at ? new Date(t.plan_expires_at).toLocaleDateString() : 'N/A'}
                </td>
                <td className="p-4 text-right space-x-2">
                  <button
                    onClick={() => handleSelectTenant(t.id)}
                    className="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200"
                  >
                    Details & Pairing
                  </button>
                  {t.status !== 'active' ? (
                    <button
                      onClick={() => handleStatusChange(t.id, 'active')}
                      className="text-xs px-3 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30"
                    >
                      Activate
                    </button>
                  ) : (
                    <button
                      onClick={() => handleStatusChange(t.id, 'suspended')}
                      className="text-xs px-3 py-1.5 rounded-lg bg-red-500/20 text-red-300 hover:bg-red-500/30"
                    >
                      Suspend
                    </button>
                  )}
                </td>
              </tr>
            ))}
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

      {/* Add Tenant Modal with WhatsApp Pairing */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="glass-card w-full max-w-lg p-6 rounded-2xl border border-slate-800 space-y-4 max-h-[90vh] overflow-y-auto my-6">
            <h3 className="text-lg font-bold text-white">Create Agent Tenant & Channel Setup</h3>
            <form onSubmit={handleCreateTenant} className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Agent / Agency Name</label>
                <input
                  type="text"
                  required
                  value={newTenant.name}
                  onChange={(e) => setNewTenant({ ...newTenant, name: e.target.value })}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Phone Number (International format)</label>
                <input
                  type="text"
                  required
                  placeholder="+994501234567"
                  value={newTenant.phone}
                  onChange={(e) => setNewTenant({ ...newTenant, phone: e.target.value, whatsapp_number: e.target.value })}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Delivery Channel</label>
                  <select
                    value={newTenant.preferred_channel}
                    onChange={(e) => setNewTenant({ ...newTenant, preferred_channel: e.target.value })}
                    className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800"
                  >
                    <option value="telegram">Telegram Bot</option>
                    <option value="whatsapp">WhatsApp (Evolution API)</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs text-slate-400 block mb-1">Subscription Plan</label>
                  <select
                    value={newTenant.plan}
                    onChange={(e) => setNewTenant({ ...newTenant, plan: e.target.value })}
                    className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800"
                  >
                    {availablePlans.map((p) => (
                      <option key={p.id} value={p.code}>
                        {p.name} ({p.price} {p.currency}/{p.billing_period})
                      </option>
                    ))}
                    {availablePlans.length === 0 && (
                      <>
                        <option value="free">Free Trial</option>
                        <option value="starter">Starter Agent</option>
                        <option value="pro">Pro Agent</option>
                        <option value="agency">Agency Team</option>
                      </>
                    )}
                  </select>
                </div>
              </div>

              {/* WhatsApp Evolution Setup Box */}
              {newTenant.preferred_channel === 'whatsapp' && (
                <div className="p-4 bg-dark-900/80 border border-emerald-500/30 rounded-xl space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-emerald-400 flex items-center gap-1.5">
                      <QrCode className="w-4 h-4 text-emerald-400" />
                      WhatsApp Evolution API Pairing
                    </span>
                    {waStatus?.connected ? (
                      <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-semibold">
                        <Wifi className="w-3 h-3" /> Connected
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 font-semibold">
                        <WifiOff className="w-3 h-3" /> Unpaired
                      </span>
                    )}
                  </div>

                  <p className="text-[11px] text-slate-400">
                    Pair your agent's WhatsApp phone number using QR Code to automatically broadcast matching listings, buyer requests, and group notifications.
                  </p>

                  {!waQrCode ? (
                    <button
                      type="button"
                      disabled={waLoading}
                      onClick={() => generateWhatsAppQrCode()}
                      className="w-full flex items-center justify-center gap-2 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 font-semibold py-2 rounded-xl text-xs transition-colors"
                    >
                      {waLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <QrCode className="w-3.5 h-3.5" />}
                      <span>Generate & Display WhatsApp QR Code</span>
                    </button>
                  ) : (
                    <div className="flex flex-col items-center space-y-2 pt-2 bg-white/5 p-3 rounded-xl border border-slate-700">
                      <img src={waQrCode} alt="WhatsApp QR Code" className="w-48 h-48 rounded-lg shadow-lg bg-white p-2" />
                      <span className="text-[11px] text-slate-300 text-center font-medium">
                        Open WhatsApp on your phone → Linked Devices → Link a Device → Scan QR Code
                      </span>
                      {waPairingCode && (
                        <div className="text-xs font-mono text-emerald-400">
                          Pairing Code: <span className="font-bold">{waPairingCode}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-300 font-medium">Backup-as-a-Service (BaaS) Plan</span>
                  <input
                    type="checkbox"
                    checked={newTenant.backup_enabled}
                    onChange={(e) => setNewTenant({ ...newTenant, backup_enabled: e.target.checked })}
                    className="w-4 h-4 rounded border-slate-700 bg-slate-900 text-emerald-500 focus:ring-emerald-500"
                  />
                </div>
                {newTenant.backup_enabled && (
                  <div>
                    <label className="text-[10px] text-slate-400 block mb-1">Backup Frequency</label>
                    <select
                      value={newTenant.backup_frequency_days}
                      onChange={(e) => setNewTenant({ ...newTenant, backup_frequency_days: Number(e.target.value) })}
                      className="w-full glass-input px-2.5 py-1.5 rounded-lg text-xs text-white bg-dark-800"
                    >
                      <option value={1}>Daily Automated Backup (24h)</option>
                      <option value={7}>Weekly Automated Backup (7 days)</option>
                      <option value={30}>Monthly Automated Backup (30 days)</option>
                    </select>
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
                  className="px-5 py-2 text-sm font-medium bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl"
                >
                  Save Tenant & Complete Setup
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
              <h3 className="text-lg font-bold text-white">{selectedTenant.tenant.name}</h3>
              <button onClick={() => setSelectedTenant(null)} className="text-slate-400 hover:text-white">&times;</button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs bg-dark-700/40 p-3 rounded-xl">
              <div><span className="text-slate-400">Phone:</span> {selectedTenant.tenant.phone}</div>
              <div><span className="text-slate-400">Plan:</span> {selectedTenant.tenant.plan}</div>
              <div><span className="text-slate-400">Channel:</span> {selectedTenant.tenant.preferred_channel}</div>
              <div><span className="text-slate-400">Status:</span> {selectedTenant.tenant.status}</div>
            </div>

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
                  <div key={s.id} className="p-3 rounded-xl bg-dark-800 border border-slate-700/50 text-xs space-y-1">
                    <div className="font-medium text-emerald-400">#{s.id} {s.name}</div>
                    <div className="text-slate-300">{s.raw_criteria_text}</div>
                    <div className="text-slate-500">
                      District: {s.district || 'Any'} | Price: {s.min_price || 0}-{s.max_price || 'Any'} AZN
                    </div>
                  </div>
                ))}
                {selectedTenant.saved_searches.length === 0 && (
                  <div className="text-xs text-slate-500 italic">No saved search criteria set yet.</div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
