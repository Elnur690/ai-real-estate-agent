import React, { useEffect, useState } from 'react';
import { UserPlus, Search, ShieldCheck, Clock, AlertCircle, Phone, MessageSquare, Plus, CheckCircle, QrCode, RefreshCw, CheckCircle2, Wifi, WifiOff, DollarSign, Edit3, Trash2, X, AlertTriangle } from 'lucide-react';
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
    trial_days: 7,
    telegram_handle: '',
    whatsapp_number: '',
    backup_enabled: false,
    backup_frequency_days: 7
  });

  const [availablePlans, setAvailablePlans] = useState<any[]>([]);

  // Edit Modal State
  const [editTenant, setEditTenant] = useState<Tenant | null>(null);
  const [editFormData, setEditFormData] = useState({
    name: '',
    phone: '',
    type: 'individual_agent',
    preferred_channel: 'telegram',
    plan: 'starter',
    whatsapp_number: '',
    telegram_chat_id: '',
    backup_enabled: false,
    backup_frequency_days: 7
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
  const [paymentPlan, setPaymentPlan] = useState<string>('starter');
  const [cashAmount, setCashAmount] = useState<number>(0);
  const [cashDays, setCashDays] = useState<number>(30);
  const [cashNotes, setCashNotes] = useState<string>('');

  const loadTenants = async () => {
    setLoading(true);
    try {
      const [tRes, pRes] = await Promise.all([
        api.get('/tenants'),
        api.get('/plans').catch(() => ({ data: [] }))
      ]);
      setTenants(tRes.data || []);
      const fetchedPlans = pRes.data || [];
      setAvailablePlans(fetchedPlans);

      if (fetchedPlans.length > 0 && !newTenant.plan) {
        setNewTenant(prev => ({ ...prev, plan: fetchedPlans[0].code }));
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
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
      backup_frequency_days: t.backup_frequency_days || 7
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
      loadTenants();
    } catch (err) {
      console.error(err);
      alert('Failed to delete tenant.');
    } finally {
      setDeleting(false);
    }
  };

  const calculatePriceForPeriod = (planCode: string, days: number) => {
    const matchPlan = availablePlans.find(p => p.code.toLowerCase() === planCode.toLowerCase());
    const monthlyPrice = matchPlan ? matchPlan.price : (planCode === 'pro' ? 100 : planCode === 'agency' ? 250 : 50);
    const months = days / 30;
    return Math.round(monthlyPrice * (months >= 12 ? 12 : months));
  };

  const handlePlanOrPeriodChange = (newPlan: string, newDays: number) => {
    setPaymentPlan(newPlan);
    setCashDays(newDays);
    const newPrice = calculatePriceForPeriod(newPlan, newDays);
    setCashAmount(newPrice);
    if (paymentModalTenant) {
      setCashNotes(`Cash received for ${paymentModalTenant.name} (${newPlan.toUpperCase()} Plan - ${newDays} days)`);
    }
  };

  const openCashPaymentModal = (t: Tenant) => {
    const pCode = (t.plan || 'starter').toLowerCase();
    setPaymentModalTenant(t);
    setPaymentPlan(pCode);
    setCashDays(30);
    const initialPrice = calculatePriceForPeriod(pCode, 30);
    setCashAmount(initialPrice);
    setCashNotes(`Cash received for ${t.name} (${pCode.toUpperCase()} Plan - 30 days)`);
  };

  const handleRecordCashPayment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!paymentModalTenant) return;
    try {
      await api.post('/payments', {
        tenant_id: paymentModalTenant.id,
        plan: paymentPlan,
        amount: cashAmount,
        days_covered: cashDays,
        notes: cashNotes
      });
      setPaymentModalTenant(null);
      loadTenants();
    } catch (err) {
      console.error(err);
      alert('Failed to record payment.');
    }
  };

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

      if (newTenant.preferred_channel === 'whatsapp') {
        checkWhatsAppStatus(`tenant_${res.data.id}`);
      }
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
          <p className="text-slate-400 text-xs mt-0.5">Manage agents, subscription plans, cash payments, edit details, and delete accounts.</p>
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
                    {t.status === 'pending' ? 'Pending Payment' : t.status}
                  </span>
                </td>
                <td className="p-4 text-xs text-slate-400">
                  {t.plan_expires_at ? new Date(t.plan_expires_at).toLocaleDateString() : 'Pending Cash Payment'}
                </td>
                <td className="p-4 text-right space-x-1.5">
                  <button
                    onClick={() => handleSelectTenant(t.id)}
                    className="text-xs px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium"
                    title="Pairing & Details"
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

      {/* Edit Tenant Modal */}
      {editTenant && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card w-full max-w-lg p-6 rounded-2xl border border-slate-800 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Edit3 className="w-5 h-5 text-blue-400" /> Edit Agent / Tenant #{editTenant.id}
              </h3>
              <button onClick={() => setEditTenant(null)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUpdateTenant} className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Agent / Agency Name</label>
                <input
                  type="text"
                  required
                  value={editFormData.name}
                  onChange={(e) => setEditFormData({ ...editFormData, name: e.target.value })}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
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
                  <label className="text-xs text-slate-400 block mb-1">Delivery Channel</label>
                  <select
                    value={editFormData.preferred_channel}
                    onChange={(e) => setEditFormData({ ...editFormData, preferred_channel: e.target.value })}
                    className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800"
                  >
                    <option value="telegram">Telegram Bot</option>
                    <option value="whatsapp">WhatsApp (Evolution API)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">WhatsApp Number / JID</label>
                  <input
                    type="text"
                    placeholder="+994501234567"
                    value={editFormData.whatsapp_number}
                    onChange={(e) => setEditFormData({ ...editFormData, whatsapp_number: e.target.value })}
                    className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white font-mono"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-400 block mb-1">Telegram Chat ID</label>
                  <input
                    type="text"
                    placeholder="999888777"
                    value={editFormData.telegram_chat_id}
                    onChange={(e) => setEditFormData({ ...editFormData, telegram_chat_id: e.target.value })}
                    className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Subscription Plan</label>
                <select
                  value={editFormData.plan}
                  onChange={(e) => setEditFormData({ ...editFormData, plan: e.target.value })}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800"
                >
                  {availablePlans.map((p) => (
                    <option key={p.id} value={p.code}>
                      {p.name} ({p.price} {p.currency}/{p.billing_period})
                    </option>
                  ))}
                  {availablePlans.length === 0 && (
                    <>
                      <option value="free">Free Trial Tier</option>
                      <option value="starter">Starter Agent Plan</option>
                      <option value="pro">Pro Agent Plan</option>
                      <option value="agency">Agency Team Plan</option>
                    </>
                  )}
                </select>
              </div>

              <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-300 font-medium">Backup-as-a-Service (BaaS) Plan</span>
                  <input
                    type="checkbox"
                    checked={editFormData.backup_enabled}
                    onChange={(e) => setEditFormData({ ...editFormData, backup_enabled: e.target.checked })}
                    className="w-4 h-4 rounded border-slate-700 bg-slate-900 text-emerald-500 focus:ring-emerald-500"
                  />
                </div>
                {editFormData.backup_enabled && (
                  <div>
                    <label className="text-[10px] text-slate-400 block mb-1">Backup Frequency</label>
                    <select
                      value={editFormData.backup_frequency_days}
                      onChange={(e) => setEditFormData({ ...editFormData, backup_frequency_days: Number(e.target.value) })}
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
                  onClick={() => setEditTenant(null)}
                  className="px-4 py-2 text-sm text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-sm font-medium bg-blue-500 hover:bg-blue-600 text-white rounded-xl"
                >
                  Save Agent Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Tenant Confirmation Modal */}
      {deleteTenantTarget && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card w-full max-w-md p-6 rounded-2xl border border-red-500/30 space-y-4">
            <div className="flex items-center gap-3 text-red-400">
              <div className="w-10 h-10 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Delete Tenant Account?</h3>
                <p className="text-xs text-slate-400">This action will remove all saved searches and matches.</p>
              </div>
            </div>

            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-slate-300">
              Are you sure you want to permanently delete <strong>{deleteTenantTarget.name}</strong> ({deleteTenantTarget.phone})?
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setDeleteTenantTarget(null)}
                className="px-4 py-2 text-sm text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deleting}
                onClick={handleDeleteTenant}
                className="px-5 py-2 text-sm font-medium bg-red-500 hover:bg-red-600 text-white rounded-xl flex items-center gap-1.5 shadow-lg shadow-red-500/20"
              >
                <Trash2 className="w-4 h-4" />
                {deleting ? 'Deleting...' : 'Confirm Delete Tenant'}
              </button>
            </div>
          </div>
        </div>
      )}

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
                        <option value="free">Free Trial Tier (Daily)</option>
                        <option value="starter">Starter Agent Plan</option>
                        <option value="pro">Pro Agent Plan</option>
                        <option value="agency">Agency Team Plan</option>
                      </>
                    )}
                  </select>
                </div>
              </div>

              {newTenant.plan === 'free' && (
                <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl space-y-1">
                  <label className="text-xs text-amber-300 font-semibold block mb-1">
                    Free Trial Duration (Days)
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min={1}
                      max={90}
                      value={newTenant.trial_days}
                      onChange={(e) => setNewTenant({ ...newTenant, trial_days: Number(e.target.value) })}
                      className="w-full glass-input px-3 py-1.5 rounded-lg text-sm text-white font-bold bg-dark-900 border-amber-500/40"
                    />
                    <span className="text-xs text-amber-300 font-medium whitespace-nowrap">Days Trial</span>
                  </div>
                  <p className="text-[10px] text-amber-400/80">
                    Agent will get active access for {newTenant.trial_days} days. When finished, system will auto-stop access and offer paid plans over Telegram/WhatsApp.
                  </p>
                </div>
              )}

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
                  Save Tenant (Pending Cash Payment)
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirm Cash Payment Modal */}
      {paymentModalTenant && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card w-full max-w-md p-6 rounded-2xl border border-slate-800 space-y-4">
            <h3 className="text-lg font-bold text-white">Record Cash Payment & Activate Account</h3>
            <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800 text-xs text-slate-300 space-y-1">
              <div><span className="text-slate-400">Agent:</span> <strong className="text-white">{paymentModalTenant.name}</strong> ({paymentModalTenant.phone})</div>
              <div><span className="text-slate-400">Selected Plan:</span> <strong className="text-emerald-400 capitalize">{paymentModalTenant.plan} Plan</strong></div>
              {paymentModalTenant.referral_code && (
                <div><span className="text-slate-400">Referral Code:</span> <code className="text-amber-400">{paymentModalTenant.referral_code}</code></div>
              )}
            </div>

            {!!paymentModalTenant.referral_balance && paymentModalTenant.referral_balance > 0 && (
              <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-xs text-emerald-300 flex items-center justify-between">
                <span>🎁 Referral Bonus Credit Available: <strong>{paymentModalTenant.referral_balance} AZN</strong></span>
                <span className="text-[10px] bg-emerald-500/20 px-2 py-0.5 rounded font-bold">Auto-Deducted on Save</span>
              </div>
            )}

            <form onSubmit={handleRecordCashPayment} className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Subscription Plan</label>
                <select
                  value={paymentPlan}
                  onChange={(e) => handlePlanOrPeriodChange(e.target.value, cashDays)}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800"
                >
                  {availablePlans.map((p) => (
                    <option key={p.id} value={p.code}>
                      {p.name} ({p.price} {p.currency}/mo)
                    </option>
                  ))}
                  {availablePlans.length === 0 && (
                    <>
                      <option value="free">Free Trial Tier (0 AZN)</option>
                      <option value="starter">Starter Agent Plan (50 AZN/mo)</option>
                      <option value="pro">Pro Agent Plan (100 AZN/mo)</option>
                      <option value="agency">Agency Team Plan (250 AZN/mo)</option>
                    </>
                  )}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Total Fee (AZN)</label>
                  <input
                    type="number"
                    required
                    value={cashAmount}
                    onChange={(e) => setCashAmount(Number(e.target.value))}
                    className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white font-bold text-emerald-400"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-400 block mb-1">Subscription Period</label>
                  <select
                    value={cashDays}
                    onChange={(e) => handlePlanOrPeriodChange(paymentPlan, Number(e.target.value))}
                    className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800"
                  >
                    <option value={30}>1 Month (30 Days)</option>
                    <option value={90}>3 Months (90 Days)</option>
                    <option value={180}>6 Months (180 Days)</option>
                    <option value={365}>1 Year (365 Days)</option>
                  </select>
                </div>
              </div>

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
