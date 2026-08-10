import React, { useEffect, useState } from 'react';
import { DollarSign, Plus, Calendar, FileText } from 'lucide-react';
import api from '../api';
import { Payment, Tenant } from '../types';

export const PaymentsView: React.FC = () => {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  const [newPayment, setNewPayment] = useState({
    tenant_id: 0,
    amount: 100,
    currency: 'AZN',
    days_covered: 30,
    notes: 'Cash collected in office'
  });

  const loadData = async () => {
    setLoading(true);
    try {
      const [pRes, tRes] = await Promise.all([
        api.get('/payments'),
        api.get('/tenants')
      ]);
      setPayments(pRes.data);
      setTenants(tRes.data);
      if (tRes.data.length > 0) {
        setNewPayment(prev => ({ ...prev, tenant_id: tRes.data[0].id }));
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
          <h2 className="text-xl font-bold text-white">Cash Payment Collection Tracker</h2>
          <p className="text-slate-400 text-xs mt-0.5">Manually record cash collected from agents to extend plan access.</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 bg-amber-500 hover:bg-amber-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-all shadow-lg shadow-amber-500/20"
        >
          <Plus className="w-4 h-4" />
          Record Cash Payment
        </button>
      </div>

      <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-dark-800/80 text-slate-400 font-medium text-xs uppercase tracking-wider border-b border-slate-800">
            <tr>
              <th className="p-4">Payment ID</th>
              <th className="p-4">Tenant</th>
              <th className="p-4">Amount</th>
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
                  No cash payments recorded yet. Click "Record Cash Payment" to log cash collected.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card w-full max-w-md p-6 rounded-2xl border border-slate-800 space-y-4">
            <h3 className="text-lg font-bold text-white">Record Cash Payment</h3>
            <form onSubmit={handleRecordPayment} className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Select Tenant</label>
                <select
                  value={newPayment.tenant_id}
                  onChange={(e) => setNewPayment({ ...newPayment, tenant_id: Number(e.target.value) })}
                  className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white bg-dark-800"
                >
                  {tenants.map(t => (
                    <option key={t.id} value={t.id}>{t.name} ({t.phone})</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Amount (AZN)</label>
                  <input
                    type="number"
                    required
                    value={newPayment.amount}
                    onChange={(e) => setNewPayment({ ...newPayment, amount: Number(e.target.value) })}
                    className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-400 block mb-1">Days Covered</label>
                  <input
                    type="number"
                    required
                    value={newPayment.days_covered}
                    onChange={(e) => setNewPayment({ ...newPayment, days_covered: Number(e.target.value) })}
                    className="w-full glass-input px-3 py-2 rounded-xl text-sm text-white"
                  />
                </div>
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
                  className="px-5 py-2 text-sm font-medium bg-amber-500 hover:bg-amber-600 text-white rounded-xl"
                >
                  Confirm & Extend Plan
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
