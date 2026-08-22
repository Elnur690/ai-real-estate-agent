import React, { useEffect, useState } from 'react';
import { ShieldCheck, Mail, Phone, Lock, Save, AlertTriangle, CheckCircle, X, KeyRound, User, Smartphone, Copy, RefreshCw } from 'lucide-react';
import api from '../api';

interface AdminProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  onProfileUpdated?: (updatedName: string) => void;
}

export const AdminProfileModal: React.FC<AdminProfileModalProps> = ({ isOpen, onClose, onProfileUpdated }) => {
  const [profile, setProfile] = useState<{ id: number; name: string; email: string; phone?: string; role: string; totp_enabled?: boolean; created_at?: string } | null>(null);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // 2FA state
  const [totpEnabled, setTotpEnabled] = useState(false);
  const [showTotpSetup, setShowTotpSetup] = useState(false);
  const [totpSecret, setTotpSecret] = useState('');
  const [otpauthUrl, setOtpauthUrl] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [totpPassword, setTotpPassword] = useState('');
  const [showDisableModal, setShowDisableModal] = useState(false);
  const [totpLoading, setTotpLoading] = useState(false);
  const [copiedSecret, setCopiedSecret] = useState(false);

  const loadProfile = async () => {
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      const res = await api.get('/auth/me');
      if (res.data) {
        setProfile(res.data);
        setName(res.data.name || '');
        setEmail(res.data.email || '');
        setPhone(res.data.phone || '');
        setTotpEnabled(!!res.data.totp_enabled);
      }
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Profil məlumatlarını yükləmək mümkün olmadı.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadProfile();
      setCurrentPassword('');
      setNewPassword('');
      setShowTotpSetup(false);
      setShowDisableModal(false);
      setBackupCodes([]);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setSaving(true);
    try {
      const res = await api.put('/auth/profile', {
        name,
        email,
        phone: phone || undefined,
        current_password: currentPassword || undefined,
        new_password: newPassword || undefined
      });

      setProfile(res.data);
      localStorage.setItem('user_name', res.data.name);
      if (onProfileUpdated) {
        onProfileUpdated(res.data.name);
      }
      setCurrentPassword('');
      setNewPassword('');
      setSuccess('Profil məlumatları və təhlükəsizlik şifrəsi uğurla yeniləndi!');
      setTimeout(() => {
        setSuccess('');
      }, 3500);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Profili yeniləmək mümkün olmadı.');
    } finally {
      setSaving(false);
    }
  };

  const handleStartTotpSetup = async () => {
    setTotpLoading(true);
    setError('');
    try {
      const res = await api.post('/auth/2fa/setup');
      setTotpSecret(res.data.secret);
      setOtpauthUrl(res.data.otpauth_url);
      setShowTotpSetup(true);
    } catch (e: any) {
      setError(e.response?.data?.detail || '2FA quraşdırmasını başlatmaq mümkün olmadı.');
    } finally {
      setTotpLoading(false);
    }
  };

  const handleEnableTotp = async (e: React.FormEvent) => {
    e.preventDefault();
    setTotpLoading(true);
    setError('');
    try {
      const res = await api.post('/auth/2fa/enable', { code: totpCode });
      setTotpEnabled(true);
      setBackupCodes(res.data.backup_codes || []);
      setShowTotpSetup(false);
      setTotpCode('');
      setSuccess('İki mərhələli doğrulama (2FA) uğurla aktivləşdirildi!');
    } catch (e: any) {
      setError(e.response?.data?.detail || '2FA təsdiq kodu yanlışdır.');
    } finally {
      setTotpLoading(false);
    }
  };

  const handleDisableTotp = async (e: React.FormEvent) => {
    e.preventDefault();
    setTotpLoading(true);
    setError('');
    try {
      await api.post('/auth/2fa/disable', { password: totpPassword });
      setTotpEnabled(false);
      setShowDisableModal(false);
      setTotpPassword('');
      setSuccess('2FA uğurla deaktiv edildi.');
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Şifrə yanlışdır.');
    } finally {
      setTotpLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="glass-card w-full max-w-xl max-h-[90vh] overflow-y-auto p-6 rounded-2xl border border-slate-800 space-y-5 shadow-2xl animate-in fade-in zoom-in duration-200">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <User className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                Administrator Profili & Təhlükəsizlik
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20 font-mono font-semibold">
                  Superadmin
                </span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">Şəxsi giriş məlumatları, güclü şifrə və 2FA quraşdırması</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-dark-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Alert Banners */}
        {error && (
          <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
            <CheckCircle className="w-4 h-4 shrink-0" />
            <span>{success}</span>
          </div>
        )}

        {loading ? (
          <div className="py-12 text-center text-xs text-slate-500">Profil məlumatları yüklənir...</div>
        ) : (
          <div className="space-y-6">
            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-slate-300 font-semibold block mb-1">Ad və Soyad</label>
                  <input
                    type="text"
                    required
                    placeholder="Məs: Samir Məmmədov"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full bg-dark-900 border border-slate-700/80 px-3 py-2.5 rounded-xl text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>

                <div>
                  <label className="text-slate-300 font-semibold block mb-1">E-poçt Ünvanı</label>
                  <div className="relative">
                    <Mail className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-500" />
                    <input
                      type="email"
                      required
                      placeholder="admin@estate.az"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full bg-dark-900 border border-slate-700/80 pl-9 pr-3 py-2.5 rounded-xl text-white focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className="text-slate-300 font-semibold block mb-1">Əlaqə Telefonu (Könüllü)</label>
                <div className="relative">
                  <Phone className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-500" />
                  <input
                    type="text"
                    placeholder="+994501234567"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full bg-dark-900 border border-slate-700/80 pl-9 pr-3 py-2.5 rounded-xl text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              {/* Password Update Section */}
              <div className="pt-4 border-t border-slate-800 space-y-3">
                <h4 className="font-bold text-slate-300 flex items-center gap-1.5">
                  <KeyRound className="w-3.5 h-3.5 text-purple-400" />
                  Şifrəni Dəyişdir (Könüllü)
                </h4>
                <div className="p-2.5 rounded-xl bg-purple-500/5 border border-purple-500/15 text-[11px] text-purple-300/80 leading-relaxed">
                  🔒 <strong className="text-purple-200">Güclü Şifrə Tələbi:</strong> Minimum 8 simvol olmalı, ən azı 1 böyük hərf (A-Z), 1 kiçik hərf (a-z), 1 rəqəm (0-9) və 1 xüsusi simvol (!@#$%^&*...) ehtiva etməlidir.
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-slate-400 block mb-1 text-[11px]">Cari Şifrə</label>
                    <div className="relative">
                      <Lock className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-500" />
                      <input
                        type="password"
                        placeholder="Şifrəni dəyişmək üçün vacibdir"
                        value={currentPassword}
                        onChange={(e) => setCurrentPassword(e.target.value)}
                        className="w-full bg-dark-900 border border-slate-700/80 pl-9 pr-3 py-2.5 rounded-xl text-white focus:outline-none focus:border-emerald-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-slate-400 block mb-1 text-[11px]">Yeni Güclü Şifrə</label>
                    <div className="relative">
                      <Lock className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-500" />
                      <input
                        type="password"
                        placeholder="Məs: SafePass2026!"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        className="w-full bg-dark-900 border border-slate-700/80 pl-9 pr-3 py-2.5 rounded-xl text-white focus:outline-none focus:border-emerald-500"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Modal Actions */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="submit"
                  disabled={saving}
                  className="flex items-center gap-2 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-semibold px-5 py-2.5 rounded-xl transition-all shadow-lg shadow-emerald-500/20 disabled:opacity-50"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>{saving ? 'Yadda saxlanılır...' : 'Məlumatları Yadda Saxla'}</span>
                </button>
              </div>
            </form>

            {/* 2FA (Two-Factor Authentication) Section */}
            <div className="pt-5 border-t border-slate-800 space-y-4 text-xs">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                    <Smartphone className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="font-bold text-slate-200">İki Mərhələli Doğrulama (2FA - Authenticator)</h4>
                    <p className="text-[11px] text-slate-400">Google Authenticator, 1Password və ya Apple Passwords ilə təhlükəsiz giriş</p>
                  </div>
                </div>

                <span className={`px-2.5 py-1 rounded-full text-[11px] font-semibold border ${
                  totpEnabled
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                    : 'bg-slate-800 text-slate-400 border-slate-700'
                }`}>
                  {totpEnabled ? 'Aktivdir 🛡️' : 'Deaktivdir'}
                </span>
              </div>

              {!totpEnabled && !showTotpSetup && (
                <div className="p-4 rounded-xl bg-dark-900/80 border border-slate-800 flex items-center justify-between">
                  <div className="text-[11px] text-slate-400">
                    Hesabınızı kənar girişlərdən qorumaq üçün Authenticator tətbiqi ilə 2FA-nı aktiv edin.
                  </div>
                  <button
                    type="button"
                    onClick={handleStartTotpSetup}
                    disabled={totpLoading}
                    className="flex items-center gap-1.5 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl text-xs transition-colors shadow-lg shadow-indigo-600/20"
                  >
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>2FA Quraşdır</span>
                  </button>
                </div>
              )}

              {/* 2FA Setup Flow */}
              {showTotpSetup && (
                <form onSubmit={handleEnableTotp} className="p-4 rounded-xl bg-indigo-950/20 border border-indigo-500/30 space-y-4">
                  <div className="font-semibold text-indigo-300 text-xs flex items-center justify-between">
                    <span>1. Authenticator Tətbiqinizə Əlavə Edin</span>
                    <button
                      type="button"
                      onClick={() => setShowTotpSetup(false)}
                      className="text-slate-400 hover:text-white"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="space-y-2">
                    <label className="text-[11px] text-slate-400">Gizli Açar (Base32 Secret):</label>
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        readOnly
                        value={totpSecret}
                        className="w-full bg-dark-900 border border-slate-700 font-mono text-xs text-amber-300 px-3 py-2 rounded-xl"
                      />
                      <button
                        type="button"
                        onClick={() => {
                          navigator.clipboard.writeText(totpSecret);
                          setCopiedSecret(true);
                          setTimeout(() => setCopiedSecret(false), 2000);
                        }}
                        className="px-3 py-2 bg-dark-800 hover:bg-dark-700 border border-slate-700 rounded-xl text-slate-300 text-xs flex items-center gap-1 shrink-0"
                      >
                        <Copy className="w-3.5 h-3.5" />
                        <span>{copiedSecret ? 'Kopyalandı!' : 'Kopyala'}</span>
                      </button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-[11px] text-slate-300 font-semibold">2. Tətbiqdəki 6 Rəqəmli Təsdiq Kodunu Daxil Edin:</label>
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        required
                        maxLength={6}
                        placeholder="123456"
                        value={totpCode}
                        onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                        className="w-40 bg-dark-900 border border-indigo-500/50 font-mono text-center text-sm font-bold text-white px-3 py-2 rounded-xl focus:outline-none focus:border-indigo-400"
                      />
                      <button
                        type="submit"
                        disabled={totpLoading || totpCode.length !== 6}
                        className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-xl text-xs transition-colors disabled:opacity-50"
                      >
                        {totpLoading ? 'Yoxlanılır...' : 'Təsdiqlə və Aktiv Et'}
                      </button>
                    </div>
                  </div>
                </form>
              )}

              {/* Show Backup Codes */}
              {backupCodes.length > 0 && (
                <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 space-y-3">
                  <div className="text-amber-300 font-bold text-xs flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                    <span>Təcili Ehtiyat Bərpa Kodlarınız (Birdəfəlik)</span>
                  </div>
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    Telefonunuzu itirdiyiniz halda bu kodlardan istifadə edərək daxil ola bilərsiniz. Bu kodları təhlükəsiz yerdə saxlayın:
                  </p>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-dark-900/90 p-3 rounded-xl border border-slate-800 font-mono text-xs text-amber-200 text-center font-bold">
                    {backupCodes.map((code, idx) => (
                      <div key={idx} className="p-1 rounded bg-slate-800/60">{code}</div>
                    ))}
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard.writeText(backupCodes.join('\n'));
                      alert('Ehtiyat kodlar buferə kopyalandı!');
                    }}
                    className="text-xs text-amber-400 hover:underline flex items-center gap-1"
                  >
                    <Copy className="w-3.5 h-3.5" />
                    <span>Bütün kodları kopyala</span>
                  </button>
                </div>
              )}

              {/* Active 2FA management */}
              {totpEnabled && (
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setShowDisableModal(true)}
                    className="px-3.5 py-2 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-400 font-semibold rounded-xl text-xs transition-colors"
                  >
                    2FA Deaktiv Et
                  </button>
                </div>
              )}

              {/* Disable 2FA Modal */}
              {showDisableModal && (
                <form onSubmit={handleDisableTotp} className="p-4 rounded-xl bg-rose-950/20 border border-rose-500/30 space-y-3">
                  <div className="text-xs font-semibold text-rose-300">2FA Deaktiv Etmək üçün Şifrənizi Daxil Edin:</div>
                  <div className="flex items-center gap-2">
                    <input
                      type="password"
                      required
                      placeholder="Hesab şifrəniz"
                      value={totpPassword}
                      onChange={(e) => setTotpPassword(e.target.value)}
                      className="w-full bg-dark-900 border border-slate-700 px-3 py-2 rounded-xl text-white text-xs"
                    />
                    <button
                      type="submit"
                      disabled={totpLoading}
                      className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white font-semibold rounded-xl text-xs shrink-0"
                    >
                      {totpLoading ? 'Gözləyin...' : 'Deaktiv Et'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowDisableModal(false)}
                      className="px-3 py-2 bg-dark-800 text-slate-400 rounded-xl text-xs"
                    >
                      Ləğv et
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
