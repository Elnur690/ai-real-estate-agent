import React, { useEffect, useState } from 'react';
import { DollarSign, Plus, Calendar, FileText, CheckCircle } from 'lucide-react';
import api from '../api';
import { Payment, Tenant } from '../types';

export const PaymentsView: React.FC = () => {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  const [newPayment, setNewPayment] = useState({
    tenant_id: 0,
    amount: 0,
    currency: 'AZN',
    days_covered: 30,
    include_aged_listings: false,
    addon_aged_max_months: 12,
    notes: ''
  });

  const calculatePaymentAmount = (tenantId: number, days: number, includeAged: boolean) => {
    const selected = tenants.find(t => t.id === tenantId);
    const planCode = selected ? selected.plan : 'starter';
    const planObj = plans.find(p => p.code.toLowerCase() === planCode.toLowerCase());
    const basePrice = planObj ? planObj.price : 29.0;
    const addonPrice = planObj?.addon_aged_listings_price !== undefined ? planObj.addon_aged_listings_price : 15.0;
    const multiplier = days === 365 ? 10 : (days === 180 ? 5 : (days === 90 ? 2.7 : 1));
    return Math.round((basePrice * multiplier) + (includeAged ? (addonPrice * multiplier) : 0));
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const [pRes, tRes, planRes] = await Promise.all([
        api.get('/payments'),
        api.get('/tenants'),
        api.get('/plans').catch(() => ({ data: [] }))
      ]);
      setPayments(pRes.data || []);
      const fetchedTenants = tRes.data || [];
      setTenants(fetchedTenants);
      const fetchedPlans = planRes.data || [];
      setPlans(fetchedPlans);

      if (fetchedTenants.length > 0) {
        const firstTenant = fetchedTenants[0];
        const isAged = !!firstTenant.feature_aged_listings;
        const maxMonths = firstTenant.addon_aged_max_months || 12;
        const matchPlan = fetchedPlans.find((p: any) => p.code.toLowerCase() === firstTenant.plan.toLowerCase());
        const basePrice = matchPlan ? matchPlan.price : 29.0;
        const addonPrice = matchPlan?.addon_aged_listings_price !== undefined ? matchPlan.addon_aged_listings_price : 15.0;
        const total = Math.round(basePrice + (isAged ? addonPrice : 0));

        setNewPayment({
          tenant_id: firstTenant.id,
          amount: total,
          currency: matchPlan ? matchPlan.currency : 'AZN',
          days_covered: 30,
          include_aged_listings: isAged,
          addon_aged_max_months: maxMonths,
          notes: `Cash collected for ${firstTenant.name} (${firstTenant.plan.toUpperCase()} Plan)`
        });
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleTenantSelect = (tenantId: number) => {
    const selected = tenants.find(t => t.id === tenantId);
    if (selected) {
      const matchPlan = plans.find(p => p.code.toLowerCase() === selected.plan.toLowerCase());
      const isAged = !!selected.feature_aged_listings;
      const maxMonths = selected.addon_aged_max_months || 12;
      const total = calculatePaymentAmount(tenantId, newPayment.days_covered, isAged);

      setNewPayment(prev => ({
        ...prev,
        tenant_id: tenantId,
        amount: total,
        currency: matchPlan ? matchPlan.currency : 'AZN',
        include_aged_listings: isAged,
        addon_aged_max_months: maxMonths,
        notes: `Cash collected for ${selected.name} (${selected.plan.toUpperCase()} Plan)`
      }));
    }
  };

  const handlePeriodOrAddonChange = (days: number, includeAged: boolean) => {
    const total = calculatePaymentAmount(newPayment.tenant_id, days, includeAged);
    setNewPayment(prev => ({
      ...prev,
      days_covered: days,
      include_aged_listings: includeAged,
      amount: total
    }));
  };

  const handleRecordPayment = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/payments', newPayment);
      setShowModal(false);
      loadData();
    } catch (e) {
      console.error(e);
    }
  };

  const getTenantName = (id: number) => {
    const t = tenants.find(x => x.id === id);
    return t ? t.name : `Tenant #${id}`;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white">Cash Payment Collection & Subscription Period Tracker</h2>
          <p className="text-slate-400 text-xs mt-0.5">Record cash collected from agents to set plan status to active and track expiration periods.</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-all shadow-lg shadow-emerald-500/20"
        >
          <Plus className="w-4 h-4" />
          Record Cash Payment & Activate
        </button>
      </div>

      <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-dark-800/80 text-slate-400 font-medium text-xs uppercase tracking-wider border-b border-slate-800">
            <tr>
              <th className="p-4">Payment ID</th>
              <th className="p-4">Tenant / Agent</th>
              <th className="p-4">Amount Paid</th>
              <th className="p-4">Period Covered</th>
              <th className="p-4">Received Date</th>
              <th className="p-4">Notes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {payments.map((p) => (
              <tr key={p.id} className="hover:bg-dark-700/30 transition-colors">
                <td className="p-4 font-mono text-xs text-slate-400">#{p.id}</td>
                <td className="p-4 font-medium text-white">{getTenantName(p.tenant_id)}</td>
                <td className="p-4 font-bold text-emerald-400">{p.amount} {p.currency}</td>
                <td className="p-4 text-xs text-slate-300">
                  {new Date(p.period_covered_start).toLocaleDateString()} &rarr; {new Date(p.period_covered_end).toLocaleDateString()}
                </td>
                <td className="p-4 text-xs text-slate-400">{new Date(p.received_at).toLocaleDateString()}</td>
                <td className="p-4 text-xs text-slate-400">{p.notes || '-'}</td>
              </tr>
            ))}
            {payments.length === 0 && (
              <tr>
                <td colSpan={6} className="p-8 text-center text-slate-500">
                  No cash payments recorded yet. Click "Record Cash Payment & Activate" to log cash collected.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card w-full max-w-md p-6 rounded-2xl border border-slate-800 space-y-4">
            <h3 className="text-lg font-bold text-white">Record Cash Payment & Activate Account</h3>
            <form onSubmit={handleRecordPayment} className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Select Tenant / Agent</label>
                <select
                  value={newPayment.tenant_id}
                  onChange={(e) => handleTenantSelect(Number(e.target.value))}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800"
                >
                  {tenants.map(t => (
                    <option key={t.id} value={t.id}>{t.name} ({t.plan.toUpperCase()} Plan - {t.phone})</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Plan Fee Amount (AZN)</label>
                  <input
                    type="number"
                    required
                    value={newPayment.amount}
                    onChange={(e) => setNewPayment({ ...newPayment, amount: Number(e.target.value) })}
                    className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white font-semibold"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-400 block mb-1">Coverage Period</label>
                  <select
                    value={newPayment.days_covered}
                    onChange={(e) => handlePeriodOrAddonChange(Number(e.target.value), newPayment.include_aged_listings)}
                    className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800"
                  >
                    <option value={30}>1 Month (30 Days)</option>
                    <option value={90}>3 Months (90 Days)</option>
                    <option value={180}>6 Months (180 Days)</option>
                    <option value={365}>1 Year (365 Days)</option>
                  </select>
                </div>
              </div>

              {/* Aged Listings Addon Option */}
              <div className="p-3 bg-dark-900/80 rounded-xl border border-slate-800 space-y-2">
                <label className="flex items-center justify-between cursor-pointer">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={newPayment.include_aged_listings}
                      onChange={(e) => {
                        const val = e.target.checked;
                        handlePeriodOrAddonChange(newPayment.days_covered, val);
                      }}
                      className="rounded accent-emerald-500"
                    />
                    <span className="text-xs font-semibold text-slate-200">
                      Aged Active Listings Add-on
                    </span>
                  </div>
                  <span className="text-[11px] text-purple-400 font-mono font-semibold">
                    +15 AZN/mo
                  </span>
                </label>

                {newPayment.include_aged_listings && (
                  <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 text-xs">
                    <span className="text-slate-400">Historical Lookback Limit:</span>
                    <select
                      value={newPayment.addon_aged_max_months}
                      onChange={(e) => setNewPayment({ ...newPayment, addon_aged_max_months: Number(e.target.value) })}
                      className="bg-dark-800 border border-slate-700 text-white rounded-lg px-2 py-1 text-xs font-medium"
                    >
                      <option value={1}>1 Month</option>
                      <option value={3}>3 Months</option>
                      <option value={6}>6 Months</option>
                      <option value={12}>12 Months (1 Year)</option>
                      <option value={24}>24 Months (2 Years)</option>
                    </select>
                  </div>
                )}
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Notes / Internal Reference</label>
                <textarea
                  rows={2}
                  value={newPayment.notes}
                  onChange={(e) => setNewPayment({ ...newPayment, notes: e.target.value })}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-sm text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-sm font-medium bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl flex items-center gap-1.5"
                >
                  <CheckCircle className="w-4 h-4" />
                  Confirm Cash & Activate Tenant
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
