export type Language = 'az' | 'en';

export interface Translations {
  // Navigation
  navDashboard: string;
  navTenants: string;
  navPayments: string;
  navPlans: string;
  navScrapers: string;
  navMap: string;
  navSettings: string;
  saasAdmin: string;
  adminProfile: string;
  signOut: string;

  // Common
  save: string;
  cancel: string;
  close: string;
  delete: string;
  edit: string;
  add: string;
  actions: string;
  status: string;
  active: string;
  inactive: string;
  expired: string;
  trial: string;
  search: string;
  loading: string;
  success: string;
  error: string;
  all: string;
  refresh: string;
  date: string;
  amount: string;
  currency: string;
  notes: string;

  // Dashboard
  dashTitle: string;
  dashSubtitle: string;
  activeTenants: string;
  monthlyRevenue: string;
  activeSearches: string;
  dailyMatches: string;
  scraperHealth: string;
  recentActivity: string;
  quickActions: string;
  addTenantBtn: string;
  recordPaymentBtn: string;
  managePlansBtn: string;

  // Tenants
  tenantsTitle: string;
  tenantsSubtitle: string;
  newTenant: string;
  tenantName: string;
  phone: string;
  whatsappNumber: string;
  plan: string;
  subscriptionEnd: string;
  channel: string;
  featureMultiLoc: string;
  featureAgedListings: string;
  qrCode: string;
  connectWhatsApp: string;
  acceptPayment: string;
  extendSub: string;
  noTenants: string;

  // Payments / Cash Register
  paymentsTitle: string;
  paymentsSubtitle: string;
  totalCollected: string;
  subRevenue: string;
  addonRevenue: string;
  recentTransactions: string;
  recordNewPayment: string;
  paymentType: string;
  subOnly: string;
  addonOnly: string;
  subAndAddon: string;
  monthsCount: string;
  generateReceipt: string;
  printReceipt: string;
  receiptNumber: string;

  // Plans
  plansTitle: string;
  plansSubtitle: string;
  createNewPlan: string;
  planName: string;
  monthlyPrice: string;
  maxSearches: string;
  maxLocations: string;
  multiLocationAllowed: string;
  agedListingsAllowed: string;
  agedListingsPrice: string;
  trialPeriodDays: string;
  isPopular: string;

  // Scrapers
  scrapersTitle: string;
  scrapersSubtitle: string;
  totalListings: string;
  activePortals: string;
  lastScrape: string;
  triggerManualScrape: string;
  scraperStatus: string;
  
  // Settings
  settingsTitle: string;
  settingsSubtitle: string;
  appNameLabel: string;
  aiProvider: string;
  geminiApiKey: string;
  evolutionApiUrl: string;
  evolutionApiKey: string;
  testConnection: string;
  saveSettings: string;
}

export const translations: Record<Language, Translations> = {
  az: {
    // Navigation
    navDashboard: 'İdarəetmə Paneli',
    navTenants: 'Abunəçilər və Agentlər',
    navPayments: 'Kassa və Ödənişlər',
    navPlans: 'Tarif Planları',
    navScrapers: 'Skreyper və Məlumat Bazası',
    navMap: 'Bakı Xəritəsi və İstilik',
    navSettings: 'Sistem Tənzimləmələri',
    saasAdmin: 'SaaS Admin Paneli',
    adminProfile: 'Admin Profili',
    signOut: 'Çıxış et',

    // Common
    save: 'Yadda saxla',
    cancel: 'Ləğv et',
    close: 'Bağla',
    delete: 'Sil',
    edit: 'Düzəliş et',
    add: 'Əlavə et',
    actions: 'Əməliyyatlar',
    status: 'Status',
    active: 'Aktiv',
    inactive: 'Deaktiv',
    expired: 'Müddəti bitib',
    trial: 'Sınaq müddəti',
    search: 'Axtarış...',
    loading: 'Yüklənir...',
    success: 'Uğurla tamamlandı',
    error: 'Xəta baş verdi',
    all: 'Hamısı',
    refresh: 'Yenilə',
    date: 'Tarix',
    amount: 'Məbləğ',
    currency: 'AZN',
    notes: 'Qeydlər',

    // Dashboard
    dashTitle: 'SaaS İdarəetmə Paneli',
    dashSubtitle: 'Real vaxt rejimində agentlik fəaliyyəti, kassa dövriyyəsi və skreyper statistikası',
    activeTenants: 'Aktiv Abunəçi Agentlər',
    monthlyRevenue: 'Aylıq Kassa Gəliri',
    activeSearches: 'Aktiv Axtarış Parametrləri',
    dailyMatches: 'Bugünkü Uyğun Elanlar',
    scraperHealth: 'Məlumat Portallarının Vəziyyəti',
    recentActivity: 'Son Əməliyyatlar və Uyğunluqlar',
    quickActions: 'Sürətli Əməliyyatlar',
    addTenantBtn: 'Yeni Agent Əlavə Et',
    recordPaymentBtn: 'Kassada Ödəniş Qeydə Al',
    managePlansBtn: 'Tarif Planlarını İdarə Et',

    // Tenants
    tenantsTitle: 'Abunəçilər və Əmlak Agentləri',
    tenantsSubtitle: 'Sistemdə qeydiyyatdan keçmiş bütün fərdi agentlər, şirkətlər və onların abunə statusları',
    newTenant: 'Yeni Agent Qeydiyyatı',
    tenantName: 'Agent / Şirkət Adı',
    phone: 'Telefon Nömrəsi',
    whatsappNumber: 'WhatsApp Nömrəsi',
    plan: 'Tarif Planı',
    subscriptionEnd: 'Abunənin Bitmə Tarixi',
    channel: 'Əlaqə Kanalı',
    featureMultiLoc: 'Çoxsaylı Məkan Seçimi',
    featureAgedListings: 'Köhnə Aktiv Elanlar Add-on (Bazar Arxivi)',
    qrCode: 'QR Kod ilə Qoşul',
    connectWhatsApp: 'WhatsApp Qoşulması',
    acceptPayment: 'Ödəniş Qəbul Et',
    extendSub: 'Müddəti Artır',
    noTenants: 'Heç bir abunəçi tapılmadı.',

    // Payments / Cash Register
    paymentsTitle: 'Kassa və Ödənişlərin İdarə Edilməsi',
    paymentsSubtitle: 'Fərdi agentlərdən qəbul edilmiş nağd/köçürmə abunə və add-on ödənişləri',
    totalCollected: 'Ümumi Toplanmış Məbləğ',
    subRevenue: 'Abunəlik Gəliri',
    addonRevenue: 'Add-on Gəliri',
    recentTransactions: 'Kassa Əməliyyat Tarixçəsi',
    recordNewPayment: 'Yeni Kassa Ödənişi Qəbul Et',
    paymentType: 'Ödəniş Kateqoriyası',
    subOnly: 'Yalnız Abunə Haqqı',
    addonOnly: 'Yalnız Add-on Haqqı (Köhnə Elanlar)',
    subAndAddon: 'Abunə + Add-on (Birlikdə)',
    monthsCount: 'Ödənilən Ayların Sayı',
    generateReceipt: 'Qəbz Yarat',
    printReceipt: 'Qəbzi Çap Et',
    receiptNumber: 'Qəbz №',

    // Plans
    plansTitle: 'Tarif Planları və Qiymət Paketləri',
    plansSubtitle: 'Agentlər üçün təklif olunan abunəlik səviyyələri, məkan limitləri və add-on xidmətləri',
    createNewPlan: 'Yeni Tarif Planı Yarat',
    planName: 'Tarifin Adı',
    monthlyPrice: 'Aylıq Abunə Haqqı',
    maxSearches: 'Maksimum Aktiv Axtarış Sayı',
    maxLocations: 'Maksimum Məkan Sayı (Çoxlu Məkan)',
    multiLocationAllowed: 'Çoxsaylı Məkan Seçimi Aktivdir',
    agedListingsAllowed: 'Köhnə Elanlar (Aged Listings) Daxildir',
    agedListingsPrice: 'Köhnə Elanlar Add-on Qiyməti',
    trialPeriodDays: 'Sınaq Müddəti (Günlərlə)',
    isPopular: 'Əsas / Populyar Paket',

    // Scrapers
    scrapersTitle: 'Elan Portalları və Məlumat Borusu',
    scrapersSubtitle: '17 aparıcı Azərbaycan əmlak portalı və Telegram kanallarından avtomatlaşdırılmış skreypinq',
    totalListings: 'Bazadakı Ümumi Elanlar',
    activePortals: 'Aktiv Mənbələrin Sayı',
    lastScrape: 'Son Yenilənmə Vaxtı',
    triggerManualScrape: 'Mənbələri İndi Skreyp Et',
    scraperStatus: 'Portal Vəziyyəti',

    // Settings
    settingsTitle: 'Sistem və AI Tənzimləmələri',
    settingsSubtitle: 'Süni intellekt modelləri, WhatsApp Evolution API və platforma parametrləri',
    appNameLabel: 'Platformanın Adı',
    aiProvider: 'Süni İntellekt Modeli',
    geminiApiKey: 'Google Gemini API Açarı',
    evolutionApiUrl: 'WhatsApp Evolution API Ünvanı',
    evolutionApiKey: 'WhatsApp API Açarı',
    testConnection: 'Bağlantını Yoxla',
    saveSettings: 'Tənzimləmələri Yadda Saxla'
  },
  en: {
    // Navigation
    navDashboard: 'Dashboard',
    navTenants: 'Tenants & Agents',
    navPayments: 'Cash Payments',
    navPlans: 'Subscription Plans',
    navScrapers: 'Scrapers & Pipeline',
    navMap: 'Baku Map & Heatmap',
    navSettings: 'App Settings & AI Config',
    saasAdmin: 'SaaS Admin Dashboard',
    adminProfile: 'Admin Profile',
    signOut: 'Sign Out',

    // Common
    save: 'Save',
    cancel: 'Cancel',
    close: 'Close',
    delete: 'Delete',
    edit: 'Edit',
    add: 'Add',
    actions: 'Actions',
    status: 'Status',
    active: 'Active',
    inactive: 'Inactive',
    expired: 'Expired',
    trial: 'Trial',
    search: 'Search...',
    loading: 'Loading...',
    success: 'Successfully completed',
    error: 'An error occurred',
    all: 'All',
    refresh: 'Refresh',
    date: 'Date',
    amount: 'Amount',
    currency: 'AZN',
    notes: 'Notes',

    // Dashboard
    dashTitle: 'SaaS Admin Dashboard',
    dashSubtitle: 'Real-time agent metrics, cash payments revenue and scraper pipeline statistics',
    activeTenants: 'Active Subscribed Agents',
    monthlyRevenue: 'Monthly Cash Revenue',
    activeSearches: 'Active Search Criteria',
    dailyMatches: 'Today Matched Listings',
    scraperHealth: 'Scrapers Pipeline Health',
    recentActivity: 'Recent Matches & Activity',
    quickActions: 'Quick Actions',
    addTenantBtn: 'Register New Agent',
    recordPaymentBtn: 'Record Cash Payment',
    managePlansBtn: 'Manage Subscription Plans',

    // Tenants
    tenantsTitle: 'Subscribed Agents & Tenants',
    tenantsSubtitle: 'All individual agents, agencies, and their subscription details in one place',
    newTenant: 'Register New Agent',
    tenantName: 'Agent / Agency Name',
    phone: 'Phone Number',
    whatsappNumber: 'WhatsApp Number',
    plan: 'Subscription Plan',
    subscriptionEnd: 'Subscription End Date',
    channel: 'Preferred Channel',
    featureMultiLoc: 'Multi-Location Search',
    featureAgedListings: 'Aged Listings Add-on (Market Lookback)',
    qrCode: 'Pair via QR Code',
    connectWhatsApp: 'WhatsApp Connection',
    acceptPayment: 'Accept Payment',
    extendSub: 'Extend Subscription',
    noTenants: 'No subscribed agents found.',

    // Payments / Cash Register
    paymentsTitle: 'Cash Register & Payment Management',
    paymentsSubtitle: 'Track and issue receipts for manual cash and bank subscription / add-on payments',
    totalCollected: 'Total Revenue Collected',
    subRevenue: 'Subscription Revenue',
    addonRevenue: 'Add-on Revenue',
    recentTransactions: 'Payment History & Ledger',
    recordNewPayment: 'Record Cash Payment',
    paymentType: 'Payment Category',
    subOnly: 'Subscription Fee Only',
    addonOnly: 'Add-on Fee Only (Aged Listings)',
    subAndAddon: 'Subscription + Add-on (Combined)',
    monthsCount: 'Number of Months Paid',
    generateReceipt: 'Generate Receipt',
    printReceipt: 'Print Receipt',
    receiptNumber: 'Receipt #',

    // Plans
    plansTitle: 'Subscription Plans & Tiers',
    plansSubtitle: 'Configure tiered feature limits, pricing, and add-on options for real estate agents',
    createNewPlan: 'Create New Plan',
    planName: 'Plan Name',
    monthlyPrice: 'Monthly Price',
    maxSearches: 'Max Active Searches',
    maxLocations: 'Max Locations (Multi-Location)',
    multiLocationAllowed: 'Multi-Location Allowed',
    agedListingsAllowed: 'Aged Listings Included',
    agedListingsPrice: 'Aged Listings Add-on Price',
    trialPeriodDays: 'Trial Period (Days)',
    isPopular: 'Popular / Featured Plan',

    // Scrapers
    scrapersTitle: 'Real Estate Portals & Data Pipeline',
    scrapersSubtitle: 'Automated crawlers indexing 17 Azerbaijani property portals and Telegram channels',
    totalListings: 'Total Scraped Listings',
    activePortals: 'Active Portals Count',
    lastScrape: 'Last Scrape Run',
    triggerManualScrape: 'Trigger Scrapers Now',
    scraperStatus: 'Portal Status',

    // Settings
    settingsTitle: 'System & AI Configuration',
    settingsSubtitle: 'Configure AI models, WhatsApp Evolution API endpoints, and platform branding',
    appNameLabel: 'Platform App Name',
    aiProvider: 'AI Model Provider',
    geminiApiKey: 'Google Gemini API Key',
    evolutionApiUrl: 'WhatsApp Evolution API URL',
    evolutionApiKey: 'WhatsApp API Key',
    testConnection: 'Test Connection',
    saveSettings: 'Save Settings'
  }
};

let currentLang: Language = (localStorage.getItem('app_lang') as Language) || 'az';

export function getLanguage(): Language {
  return currentLang;
}

export function setLanguage(lang: Language) {
  currentLang = lang;
  localStorage.setItem('app_lang', lang);
  window.dispatchEvent(new Event('app:language_changed'));
}

export function useTranslation() {
  const t = translations[currentLang];
  return { t, lang: currentLang, setLanguage };
}
