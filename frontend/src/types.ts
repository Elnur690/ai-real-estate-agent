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
  preferred_channel: 'whatsapp' | 'telegram' | 'both';
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
  feature_multi_location?: boolean;
  max_locations_per_search?: number;
  feature_aged_listings?: boolean;
  addon_aged_max_months?: number;
  addon_saved_searches?: number;
  feature_watermark_free_images?: boolean;
  addon_image_requests_limit?: number;
  addon_image_requests_used?: number;
  addon_image_requests_price?: number;
  feature_crm?: boolean;
  addon_crm_price?: number;
  feature_portfolio?: boolean;
  portfolio_limit?: number;
  addon_portfolio_price?: number;
  portfolio_expires_at?: string;
  portfolio_slug?: string;
  portfolio_vitrin_url?: string;
  feature_custom_domain?: boolean;
  custom_domain?: string | null;
  custom_domain_enabled?: boolean;
  custom_domain_status?: string;
  addon_custom_domain_price?: number;
  custom_domain_expires_at?: string | null;
  active_searches_count?: number;
  max_saved_searches?: number;
  referral_code?: string;
  referral_balance?: number;
  parent_tenant_id?: number;
  assigned_districts?: string[];
  seller_id?: number;
  seller_name?: string;
  seller_company?: string;
  created_at: string;
}

export interface SavedSearch {
  id: number;
  tenant_id: number;
  name: string;
  raw_criteria_text: string;
  district?: string;
  metro_station?: string;
  include_adjacent_metro?: boolean;
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
  type: 'website' | 'telegram_channel' | 'facebook_group' | 'facebook_page';
  name: string;
  url_or_handle: string;
  status: 'active' | 'paused' | 'error' | 'blocked';
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

export interface CrmClient {
  id: number;
  tenant_id: number;
  name: string;
  phone?: string;
  whatsapp_number?: string;
  telegram_handle?: string;
  client_type: 'buyer' | 'renter' | 'seller' | 'landlord';
  budget_min?: number;
  budget_max?: number;
  rooms_min?: number;
  rooms_max?: number;
  districts?: string[];
  notes?: string;
  deals_count: number;
  created_at: string;
  updated_at: string;
}

export interface CrmActivity {
  id: number;
  deal_id?: number;
  action_type: string;
  description: string;
  created_at: string;
}

export interface CrmReminderItem {
  id: number;
  tenant_id: number;
  client_id?: number | null;
  deal_id?: number | null;
  title: string;
  reminder_type: 'viewing' | 'call' | 'follow_up' | 'notary' | 'other';
  notes?: string | null;
  due_at: string;
  due_at_formatted?: string | null;
  remind_before_minutes: number;
  status: 'pending' | 'notified' | 'completed' | 'cancelled';
  notified_at?: string | null;
  client_name?: string | null;
  client_phone?: string | null;
  deal_title?: string | null;
  deal_price?: number | null;
  created_at: string;
  updated_at: string;
}

export interface CrmDeal {
  id: number;
  tenant_id: number;
  client_id?: number;
  client_name?: string;
  client_phone?: string;
  listing_id?: number;
  listing_title: string;
  listing_price: number;
  listing_currency: string;
  listing_url?: string;
  listing_image?: string;
  listing_location?: string;
  stage: 'new' | 'offered' | 'viewing' | 'negotiation' | 'closed' | 'lost';
  custom_offer_price?: number;
  commission_amount?: number;
  commission_percent?: number;
  private_notes?: string;
  scheduled_viewing_at?: string;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  activities: CrmActivity[];
}

export interface CrmStats {
  total_deals: number;
  stage_counts: Record<string, number>;
  total_clients: number;
  total_won_commission: number;
}

export interface PortfolioListingItem {
  id: number;
  tenant_id: number;
  listing_id?: number;
  title: string;
  description?: string;
  price: number;
  currency: string;
  price_usd?: number;
  district?: string;
  metro_station?: string;
  address?: string;
  rooms?: number;
  area_sqm?: number;
  floor?: number;
  total_floors?: number;
  building_type?: string;
  property_type?: string;
  offer_type?: string;
  photos: string[];
  contact_name?: string;
  contact_phone?: string;
  notes?: string;
  share_code: string;
  share_url?: string;
  is_active: boolean;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface PortfolioOverview {
  items: PortfolioListingItem[];
  active_count: number;
  portfolio_limit: number;
  is_limit_reached: boolean;
  feature_enabled: boolean;
  expires_at?: string;
  portfolio_slug?: string;
  portfolio_vitrin_url?: string;
  custom_domain_info?: {
    base_url: string;
    active_domain: string;
    source: 'agent' | 'reseller' | 'platform';
    cname_target: string;
    agent_custom_domain?: string | null;
    agent_custom_domain_enabled?: boolean;
    agent_feature_custom_domain?: boolean;
    agent_custom_domain_status?: string;
    addon_custom_domain_price?: number;
    custom_domain_expires_at?: string | null;
    seller_id?: number | null;
    reseller_name?: string | null;
    reseller_custom_domain?: string | null;
    reseller_custom_domain_enabled?: boolean;
  };
}

