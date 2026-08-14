export interface Tenant {
  id: number;
  name: string;
  type: 'individual_agent' | 'agency';
  phone: string;
  telegram_handle?: string;
  plan: 'free' | 'starter' | 'pro' | 'agency' | 'enterprise';
  plan_period: 'daily' | 'monthly' | 'quarterly' | 'annual' | 'lifetime';
  trial_days?: number;
  plan_started_at: string;
  plan_expires_at?: string;
  status: 'active' | 'expired' | 'suspended' | 'pending';
  preferred_channel: 'whatsapp' | 'telegram';
  whatsapp_number?: string;
  telegram_chat_id?: string;
  digest_mode: 'instant' | 'hourly' | 'daily';
  backup_enabled?: boolean;
  backup_frequency_days?: number;
  last_backup_at?: string;
  feature_makler_detector?: boolean;
  feature_avm_bargain_finder?: boolean;
  feature_social_brochure?: boolean;
  feature_client_intake_bot?: boolean;
  feature_aged_listings?: boolean;
  addon_aged_max_months?: number;
  referral_code?: string;
  referral_balance?: number;
  parent_tenant_id?: number;
  assigned_districts?: string[];
  created_at: string;
}

export interface SavedSearch {
  id: number;
  tenant_id: number;
  name: string;
  raw_criteria_text: string;
  district?: string;
  min_price?: number;
  max_price?: number;
  min_rooms?: number;
  max_rooms?: number;
  seller_type: string;
  building_type: string;
  is_active: boolean;
  created_at: string;
}

export interface Payment {
  id: number;
  tenant_id: number;
  amount: number;
  currency: string;
  period_covered_start: string;
  period_covered_end: string;
  received_by?: number;
  received_at: string;
  notes?: string;
}

export interface AIProviderConfigItem {
  id: number;
  tenant_id?: number;
  task_type: 'criteria_parsing' | 'listing_parsing' | 'match_scoring';
  provider: 'gemini' | 'claude' | 'gpt';
  model_name: string;
  api_key_masked: string;
  is_active: boolean;
  updated_at: string;
}

export interface AICallLogItem {
  id: number;
  tenant_id?: number;
  provider: string;
  task_type: string;
  model_name: string;
  status: string;
  latency_ms: number;
  error_message?: string;
  created_at: string;
}

export interface ScraperSource {
  id: number;
  type: 'website' | 'telegram_channel';
  name: string;
  url_or_handle: string;
  status: 'active' | 'error' | 'blocked';
  last_scraped_at?: string;
  created_at: string;
}

export interface AdminUser {
  id: number;
  name: string;
  email: string;
  phone?: string;
  role: string;
  created_at?: string;
}

