import re
from typing import Tuple, Optional

# Agency / Broker Detection Keywords
AGENCY_KEYWORDS = [
    "agentlik", "agentliyi", "daşınmaz əmlak", "dasinmaz emlak",
    "əmlak şirkəti", "emlak sirketi", "əmlak ofisi", "emlak ofisi",
    "şirkət", "sirket", "şirkəti", "sirketi", "agent", "vasitəçi (agent)", "vasiteci (agent)",
    "vasitəçi", "vasiteci", "vasitəçilik", "vasitecilik",
    "ofis haqqı", "ofis haqqi", "ofis haqq", "ofis faizi",
    "xidmət haqqı", "xidmet haqqi", "xidmət haqq", "xidmet haqq",
    "komissiya", "komissiyası", "komisiya", "makler", "makler haqqı",
    "rieltor", "realtor", "əmlakçı", "emlakci",
    "şirkətimiz", "filialımız", "elanlarımız",
    "1% ofis", "1% xidmət", "1% xidmet", "2% ofis", "2% xidmət", "2% xidmet",
    "faizlə", "faizle", "depozit tələb", "1-ci ay", "aylıq komissiya"
]

# Commission Percentage Regex Patterns (e.g., 20% ofis haqqı, 30% vasitəçi, 1% xidmət)
COMMISSION_REGEX = re.compile(
    r'(?:\b(?:1|2|3|4|5|10|15|20|25|30|40|50)\s*%\s*(?:ofis|xidmət|xidmet|komissiya|faiz|makler|agentlik|vasitəçi|vasiteci))|'
    r'(?:(?:ofis|xidmət|xidmet|komissiya|makler|agentlik|vasitəçi|vasiteci)\s*(?:haqqı|haqqi|faizi|ödənişi)?\s*[:=-]?\s*(?:1|2|3|4|5|10|15|20|25|30|40|50)\s*%)',
    re.IGNORECASE
)

# Genuine Owner Keywords
OWNER_KEYWORDS = [
    "sahibindən", "sahibinden", "mülkiyyətçidən", "mulkiyyetciden",
    "öz evimdir", "oz evimdir", "öz mənzilimdir", "oz menzilimdir",
    "öz əmlakımdır", "oz emlakimdir", "vasitəçisiz", "vasitecisiz",
    "maklersiz", "maklerlər narahat etməsin", "maklerler narahat etmesin"
]

# Rental / Deal Type Keywords
RENTAL_KEYWORDS = [
    "kirayə", "kiraye", "icarə", "icare", "arenda", "aylıq", "ayliq",
    "günlük", "gunluk", "sutkalıq", "sutkaliq", "kirayəyə verilir",
    "icarəyə verilir", "kiraye verilir", "icareye verilir", "arendaya verilir",
    "depozit", "komendant daxil", "aylıq ödəniş", "ayliq odenis"
]

SALE_KEYWORDS = [
    "satılır", "satilir", "satış", "satis", "satiram", "satıram",
    "satışa çıxarıldı", "satisa cixarildi", "ipoteka", "ilkin ödəniş",
    "kupçalı satılır", "kupcali satilir", "nəğd satılır"
]

def classify_property_and_offer(
    title: str = "",
    description: str = "",
    url: str = "",
    raw_text: str = ""
) -> Tuple[str, str, str]:
    """
    Returns: (offer_type, property_type, seller_type)
    - offer_type: 'sale' | 'rent' | 'daily_rent'
    - property_type: 'apartment' | 'house' | 'office' | 'commercial' | 'land'
    - seller_type: 'agency' | 'owner'
    """
    full_text = f"{title or ''} {description or ''} {url or ''} {raw_text or ''}".lower()

    # 1. Classify Offer Type (Sale vs Rent)
    offer_type = "sale"
    is_rent_url = any(u in url.lower() for u in ["/kiraye", "/icare", "/arenda", "/rent", "/ayliq", "arenda.az"])
    is_sale_url = any(u in url.lower() for u in ["/satilir", "/satis", "/sale", "/alqi-satqi"])

    has_rental_kw = any(kw in full_text for kw in RENTAL_KEYWORDS)
    has_sale_kw = any(kw in full_text for kw in SALE_KEYWORDS)

    if is_rent_url:
        offer_type = "rent"
    elif is_sale_url and not has_rental_kw:
        offer_type = "sale"
    elif has_rental_kw and not has_sale_kw:
        offer_type = "rent"
    elif has_rental_kw and ("icarə" in full_text or "kirayə" in full_text or "arenda" in full_text):
        offer_type = "rent"
    else:
        offer_type = "sale"

    # 2. Classify Property Type
    property_type = "apartment" # default

    if "ofis.az" in url.lower() or "/ofis" in url.lower() or "/ofisler" in url.lower():
        property_type = "office"
    elif "/obyekt" in url.lower() or "/obyektler" in url.lower():
        property_type = "commercial"
    elif "/torpaq" in url.lower() or "/torpaqlar" in url.lower():
        property_type = "land"
    elif "/heyet-evleri" in url.lower() or "/bag-evleri" in url.lower() or "/villalar" in url.lower():
        property_type = "house"
    elif any(k in full_text for k in ["ofis kimi", "ofis icarə", "ofis üçün", "biznes mərkəzi", "plazada ofis", "ofisdir", "ofis satılır", "ofis kirayə"]):
        property_type = "office"
    elif any(k in full_text for k in ["obyekt", "mağaza", "magaza", "restoran", "kafe", "klinika", "salon", "anbar", "istehsalat sahəsi", "qeyri-yaşayış", "qeyri yasayis"]):
        property_type = "commercial"
    elif any(k in full_text for k in ["torpaq sahəsi", "torpaq satılır", "sot torpaq", "hektar"]):
        property_type = "land"
    elif any(k in full_text for k in ["həyət evi", "heyet evi", "bağ evi", "bag evi", "villa", "həyət", "kotec"]):
        property_type = "house"
    else:
        property_type = "apartment"

    # 3. Classify Seller Type (Agency vs Owner)
    has_agency_kw = any(kw in full_text for kw in AGENCY_KEYWORDS) or bool(COMMISSION_REGEX.search(full_text))
    has_owner_kw = any(kw in full_text for kw in OWNER_KEYWORDS) or ("mülkiyyətçi" in full_text) or ("mulkiyyetci" in full_text)

    # Agency keywords always strictly override owner claims (prevent false "sahibindən" makler postings)
    if has_agency_kw:
        seller_type = "agency"
    elif has_owner_kw:
        seller_type = "owner"
    else:
        # In Baku real estate portals, unmarked listings without owner verification are agencies/brokers
        seller_type = "agency"

    return offer_type, property_type, seller_type
