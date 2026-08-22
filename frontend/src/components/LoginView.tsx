import React, { useState } from 'react';
import { Building, Lock, Mail, ArrowRight, ShieldCheck, AlertCircle, Globe, Smartphone, ArrowLeft } from 'lucide-react';
import api from '../api';
import { useTranslation, Language } from '../i18n';

interface LoginViewProps {
  onLoginSuccess: (token: string, userName: string, role?: string) => void;
  appName: string;
}

export function LoginView({ onLoginSuccess, appName }: LoginViewProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  
  // 2FA Challenge state
  const [requires2FA, setRequires2FA] = useState(false);
  const [tempToken, setTempToken] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [pendingUserName, setPendingUserName] = useState('');
  const [pendingRole, setPendingRole] = useState('');

  const { t, lang, setLanguage } = useTranslation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const res = await api.post('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      if (res.data && res.data.requires_2fa) {
        setRequires2FA(true);
        setTempToken(res.data.temp_token);
        setPendingUserName(res.data.user_name || 'Admin');
        setPendingRole(res.data.role || 'admin');
      } else if (res.data && res.data.access_token) {
        onLoginSuccess(res.data.access_token, res.data.user_name || 'Admin', res.data.role || 'admin');
      } else {
        setError('Giriş xətası: Serverdən gözlənilməz cavab alındı.');
      }
    } catch (err: any) {
      if (err.response && err.response.data && err.response.data.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Daxil edilən məlumatlar yanlışdır və ya server əlçatan deyil.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handle2FAVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await api.post('/auth/2fa/verify-login', {
        temp_token: tempToken,
        code: totpCode
      });

      if (res.data && res.data.access_token) {
        onLoginSuccess(res.data.access_token, res.data.user_name || pendingUserName, res.data.role || pendingRole);
      } else {
        setError('2FA doğrulama xətası.');
      }
    } catch (err: any) {
      if (err.response && err.response.data && err.response.data.detail) {
        setError(err.response.data.detail);
      } else {
        setError('2FA doğrulama kodu yanlışdır və ya sessiya bitib.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-dark-900 text-slate-100 flex items-center justify-center p-4">
      {/* Background Glow Accents */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/3 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md bg-dark-800/90 border border-slate-800/80 rounded-2xl p-8 shadow-2xl backdrop-blur-xl relative z-10 space-y-6">
        {/* Language Switcher in Login */}
        <div className="flex justify-end">
          <div className="flex items-center gap-1 bg-dark-900/80 border border-slate-800/80 p-1 rounded-xl text-xs">
            <Globe className="w-3.5 h-3.5 text-emerald-400 ml-1 mr-0.5" />
            <button
              onClick={() => setLanguage('az')}
              className={`px-2 py-0.5 rounded-lg font-semibold transition-all ${
                lang === 'az' ? 'bg-emerald-500 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              🇦🇿 AZ
            </button>
            <button
              onClick={() => setLanguage('en')}
              className={`px-2 py-0.5 rounded-lg font-semibold transition-all ${
                lang === 'en' ? 'bg-emerald-500 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              🇬🇧 EN
            </button>
          </div>
        </div>

        {/* Header Branding */}
        <div className="text-center space-y-3">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-emerald-500 to-indigo-600 shadow-xl shadow-emerald-500/20 mb-1">
            <Building className="w-7 h-7 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">{appName}</h1>
            <p className="text-xs text-slate-400 font-medium mt-1">
              {lang === 'az' ? 'SaaS Admin Panelinə daxil olun' : 'Sign in to access SaaS Admin Control Panel'}
            </p>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="flex items-center gap-2.5 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs px-3.5 py-3 rounded-xl">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Login Form or 2FA Challenge Form */}
        {!requires2FA ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">
                {lang === 'az' ? 'Admin E-poçt Ünvanı' : 'Admin Email'}
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@erma.shop"
                  className="w-full bg-dark-900/90 border border-slate-700/60 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">
                {lang === 'az' ? 'Şifrə' : 'Password'}
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full bg-dark-900/90 border border-slate-700/60 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-semibold py-3 px-4 rounded-xl text-sm transition-all shadow-lg shadow-emerald-500/20 disabled:opacity-50 mt-2"
            >
              {loading ? (
                <span className="inline-block animate-pulse">{t.loading}</span>
              ) : (
                <>
                  <span>{lang === 'az' ? 'Admin Panelinə Daxil Ol' : 'Sign In to Admin Dashboard'}</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        ) : (
          <form onSubmit={handle2FAVerify} className="space-y-4 animate-in fade-in zoom-in duration-200">
            <div className="p-3.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-start gap-2.5">
              <Smartphone className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
              <div className="text-xs text-indigo-200/90 space-y-0.5">
                <div className="font-bold text-white">İki Mərhələli Doğrulama (2FA)</div>
                <div className="text-[11px] text-slate-300">
                  Google Authenticator və ya ehtiyat bərpa kodunuzu daxil edin.
                </div>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">
                6 Rəqəmli Doğrulama Kodu və ya Ehtiyat Kod
              </label>
              <input
                type="text"
                required
                autoFocus
                placeholder="123456 və ya XXXX-XXXX"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                className="w-full bg-dark-900/90 border border-indigo-500/60 rounded-xl px-4 py-3 text-center font-mono text-base tracking-widest text-white placeholder-slate-500 focus:outline-none focus:border-indigo-400 transition-colors"
              />
            </div>

            <button
              type="submit"
              disabled={loading || !totpCode.trim()}
              className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-400 hover:to-purple-500 text-white font-semibold py-3 px-4 rounded-xl text-sm transition-all shadow-lg shadow-indigo-500/20 disabled:opacity-50"
            >
              {loading ? (
                <span className="inline-block animate-pulse">Doğrulanır...</span>
              ) : (
                <>
                  <span>Təsdiqlə və Daxil Ol</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>

            <button
              type="button"
              onClick={() => {
                setRequires2FA(false);
                setTotpCode('');
                setError(null);
              }}
              className="w-full flex items-center justify-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 py-1"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Giriş ekranına qayıt</span>
            </button>
          </form>
        )}

        {/* Footer Security Badge */}
        <div className="pt-4 border-t border-slate-800/80 flex items-center justify-center gap-2 text-[11px] text-slate-500">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span>{lang === 'az' ? 'AES-256 JWT & RFC 6238 2FA Təhlükəsiz Giriş Sistemi' : 'Protected by AES-256 JWT & RFC 6238 2FA'}</span>
        </div>
      </div>
    </div>
  );
}
