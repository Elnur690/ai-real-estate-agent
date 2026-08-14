import React, { useEffect, useState } from 'react';
import { UserPlus, Search, ShieldCheck, Clock, AlertCircle, Phone, MessageSquare, Plus, CheckCircle, QrCode, RefreshCw, CheckCircle2, Wifi, WifiOff, DollarSign, Edit3, Trash2, X, AlertTriangle, Users, MapPin } from 'lucide-react';
import api from '../api';
import { Tenant, SavedSearch } from '../types';

const BAKU_DISTRICT_OPTIONS = [
  "Yasamal", "Nəsimi", "Binəqədi", "Nərimanov", "Səbail",
  "Xətai", "Nizami", "Sabunçu", "Suraxanı", "Xəzər",
  "Abşeron", "Sumqayıt", "Qaradağ", "Pirallahi"
];

export const TenantsView: React.FC = () => {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTenant, setSelectedTenant] = useState<{ tenant: Tenant; saved_searches: SavedSearch[]; sub_agents?: Tenant[] } | null>(null);
  
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
    backup_frequency_days: 7,
    feature_aged_listings: false,
    addon_aged_max_months: 12
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
  const [editFormData, setEditFormData] = useState({
    name: '',
    phone: '',
    type: 'individual_agent',
    preferred_channel: 'telegram',
    plan: 'starter',
    whatsapp_number: '',
    telegram_chat_id: '',
    backup_enabled: false,
    backup_frequency_days: 7,
    feature_aged_listings: false,
    addon_aged_max_months: 12
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
      backup_frequency_days: t.backup_frequency_days || 7,
      feature_aged_listings: t.feature_aged_listings || false,
      addon_aged_max_months: t.addon_aged_max_months || 12
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
        whatsapp_number: '',
        backup_enabled: false,
        backup_frequency_days: 7,
        feature_aged_listings: false,
        addon_aged_max_months: 12
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

  const openCashPaymentModal = (t: Tenant) => {
    setPaymentModalTenant(t);
    const planObj = availablePlans.find(p => p.code === t.plan) || availablePlans[0];
    const initialPlan = planObj ? planObj.code : 'starter';
    const initialPrice = planObj ? planObj.price : 29.0;
    
    setPaymentPlan(initialPlan);
    setCashDays(30);
    setCashAmount(initialPrice);
    setCashNotes(`Cash payment received for ${t.name} (1 Month)`);
  };

  const handlePlanOrPeriodChange = (planCode: string, days: number) => {
    setPaymentPlan(planCode);
    setCashDays(days);
    const planObj = availablePlans.find(p => p.code === planCode);
    const basePrice = planObj ? planObj.price : 29.0;
    const multiplier = days === 365 ? 10 : (days === 180 ? 5 : (days === 90 ? 2.7 : 1));
    const calculatedAmount = Math.round(basePrice * multiplier);
    setCashAmount(calculatedAmount);
    setCashNotes(`Cash payment for ${planCode.toUpperCase()} (${days} days)`);
  };

  const handleRecordCashPayment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!paymentModalTenant) return;
    try {
      await api.post(`/tenants/${paymentModalTenant.id}/cash-payment`, {
        plan: paymentPlan,
        duration_days: cashDays,
        amount_paid: Number(cashAmount),
        notes: cashNotes
      });
      setPaymentModalTenant(null);
      loadTenants();
      if (selectedTenant && selectedTenant.tenant.id === paymentModalTenant.id) {
        handleSelectTenant(paymentModalTenant.id);
      }
      alert('Cash payment confirmed! Tenant subscription activated.');
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
      <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-dark-800/80 text-slate-400 font-medium text-xs uppercase tracking-wider border-b border-slate-800">
            <tr>
              <th className="p-4">Agent / Agency</th>
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
                    <span className={`inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full font-medium ${
                      t.type === 'agency' ? 'bg-purple-500/10 text-purple-300 border border-purple-500/20' : 'bg-slate-700/50 text-slate-300'
                    }`}>
                      {t.type === 'agency' ? '🏢 Agency' : '👤 Individual'}
                    </span>
                  </td>
                  <td className="p-4">
                    <span className={`inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-medium ${
                      t.preferred_channel === 'whatsapp' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                    }`}>
                      {t.preferred_channel === 'whatsapp' ? 'WhatsApp' : 'Telegram'}
                    </span>
                  </td>
                  <td className="p-4">
                    <div className="capitalize font-medium text-slate-200">{t.plan}</div>
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

              <div>
                <label className="text-xs text-slate-400 block mb-1">Preferred Bot Channel</label>
                <select
                  value={subAgentForm.preferred_channel}
                  onChange={(e) => setSubAgentForm({ ...subAgentForm, preferred_channel: e.target.value })}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800"
                >
                  <option value="whatsapp">WhatsApp</option>
                  <option value="telegram">Telegram</option>
                </select>
              </div>

              {subAgentForm.preferred_channel === 'whatsapp' ? (
                <div>
                  <label className="text-xs text-slate-400 block mb-1">WhatsApp Number</label>
                  <input
                    type="text"
                    placeholder="+994501234567"
                    value={subAgentForm.whatsapp_number}
                    onChange={(e) => setSubAgentForm({ ...subAgentForm, whatsapp_number: e.target.value })}
                    className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                  />
                </div>
              ) : (
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
              )}

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

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Account Type</label>
                  <select
                    value={editFormData.type}
                    onChange={(e) => setEditFormData({ ...editFormData, type: e.target.value })}
                    className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800"
                  >
                    <option value="individual_agent">Individual Agent</option>
                    <option value="agency">Agency / Brokerage</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Bot Channel</label>
                  <select
                    value={editFormData.preferred_channel}
                    onChange={(e) => setEditFormData({ ...editFormData, preferred_channel: e.target.value })}
                    className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800"
                  >
                    <option value="telegram">Telegram</option>
                    <option value="whatsapp">WhatsApp</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Subscription Plan</label>
                <select
                  value={editFormData.plan}
                  onChange={(e) => setEditFormData({ ...editFormData, plan: e.target.value })}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800 capitalize"
                >
                  {availablePlans.map((p) => (
                    <option key={p.id} value={p.code}>
                      {p.name} ({p.price} {p.currency}) - {p.max_agents || 1} Seats
                    </option>
                  ))}
                </select>
              </div>

              {editFormData.preferred_channel === 'whatsapp' ? (
                <div>
                  <label className="text-xs text-slate-400 block mb-1">WhatsApp Number</label>
                  <input
                    type="text"
                    value={editFormData.whatsapp_number}
                    onChange={(e) => setEditFormData({ ...editFormData, whatsapp_number: e.target.value })}
                    className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                  />
                </div>
              ) : (
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Telegram Chat ID</label>
                  <input
                    type="text"
                    value={editFormData.telegram_chat_id}
                    onChange={(e) => setEditFormData({ ...editFormData, telegram_chat_id: e.target.value })}
                    className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                  />
                </div>
              )}

              {/* Aged Listings Addon */}
              <div className="pt-2 border-t border-slate-800">
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

              <div className="grid grid-cols-2 gap-3">
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
                  <label className="text-xs text-slate-400 block mb-1">Preferred Bot Channel</label>
                  <select
                    value={newTenant.preferred_channel}
                    onChange={(e) => setNewTenant({ ...newTenant, preferred_channel: e.target.value })}
                    className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800"
                  >
                    <option value="telegram">Telegram</option>
                    <option value="whatsapp">WhatsApp</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Subscription Plan</label>
                <select
                  value={newTenant.plan}
                  onChange={(e) => setNewTenant({ ...newTenant, plan: e.target.value })}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800 capitalize"
                >
                  {availablePlans.map((p) => (
                    <option key={p.id} value={p.code}>
                      {p.name} ({p.price} {p.currency}) - {p.max_agents || 1} Seats
                    </option>
                  ))}
                </select>
              </div>

              {newTenant.preferred_channel === 'whatsapp' ? (
                <div>
                  <label className="text-xs text-slate-400 block mb-1">WhatsApp Number</label>
                  <input
                    type="text"
                    placeholder="+994501234567"
                    value={newTenant.whatsapp_number}
                    onChange={(e) => setNewTenant({ ...newTenant, whatsapp_number: e.target.value })}
                    className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                  />
                </div>
              ) : (
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Telegram Handle</label>
                  <input
                    type="text"
                    placeholder="@agent_username"
                    value={newTenant.telegram_handle}
                    onChange={(e) => setNewTenant({ ...newTenant, telegram_handle: e.target.value })}
                    className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                  />
                </div>
              )}

              {/* Aged Listings Addon */}
              <div className="pt-2 border-t border-slate-800">
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
              <div>
                <label className="text-xs text-slate-400 block mb-1">Subscription Plan</label>
                <select
                  value={paymentPlan}
                  onChange={(e) => handlePlanOrPeriodChange(e.target.value, cashDays)}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800 capitalize"
                >
                  {availablePlans.map((p) => (
                    <option key={p.id} value={p.code}>
                      {p.name} ({p.price} {p.currency}) - {p.max_agents || 1} Seats
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Amount Paid (AZN)</label>
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
              <div>
                <h3 className="text-lg font-bold text-white">{selectedTenant.tenant.name}</h3>
                <span className="text-xs text-purple-400 font-mono capitalize">{selectedTenant.tenant.type.replace('_', ' ')}</span>
              </div>
              <button onClick={() => setSelectedTenant(null)} className="text-slate-400 hover:text-white">&times;</button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs bg-dark-700/40 p-3 rounded-xl">
              <div><span className="text-slate-400">Phone:</span> {selectedTenant.tenant.phone}</div>
              <div><span className="text-slate-400">Plan:</span> {selectedTenant.tenant.plan}</div>
              <div><span className="text-slate-400">Channel:</span> {selectedTenant.tenant.preferred_channel}</div>
              <div><span className="text-slate-400">Status:</span> {selectedTenant.tenant.status}</div>
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
                        District: {s.district || 'Any'} | Price: {s.min_price || 0}-{s.max_price || 'Any'} AZN
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
    </div>
  );
};
