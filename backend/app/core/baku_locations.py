from typing import Optional, List, Dict

BAKU_METRO_STATIONS: Dict[str, List[str]] = {
    "Elmlər Akademiyası": ["elmlər", "elmler", "elmlər akademiyası", "elmler akademiyasi", "elmlər m", "elmler m", "bdu", "hüseyn cavid", "huseyn cavid"],
    "28 May": ["28 may", "28may", "28 may m", "may 28", "vağzal", "dilarə əliyeva", "28 mall", "28 mol"],
    "Gənclik": ["gənclik", "genclik", "gənclik m", "genclik m", "gənclik mall", "genclik mall", "zoopark", "tibb universiteti", "koroglu heykeli"],
    "Nəriman Nərimanov": ["nərimanov", "nerimanov", "n.nərimanov", "nərimanov m", "nerimanov m", "montin", "metropark", "life centre"],
    "İnşaatçılar": ["inşaatçılar", "insaatcilar", "inşaatçılar m", "insaatcilar m", "qələbə dairəsi", "qelebe dairesi", "şərifzadə", "serifzade", "ats"],
    "20 Yanvar": ["20 yanvar", "20yanvar", "20 yanvar m", "velotrek", "onkoloji", "respublika xəstəxanası"],
    "Memar Əcəmi": ["əcəmi", "ecemi", "memar əcəmi", "memar ecemi", "əcəmi m", "ecemi m", "3-cü mkr", "4-cü mkr", "5-ci mkr"],
    "Nəsimi": ["nəsimi m", "nesimi m", "nəsimi metrosu", "nesimi metrosu", "zarifa aliyeva parki"],
    "Azadlıq prospekti": ["azadlıq", "azadliq", "azadlıq m", "azadliq m", "azadlıq prospekti", "azadliq prospekti", "azadlıq metrosu", "azadliq metrosu", "8-ci mikrorayon", "8 ci mkr", "8-ci mkr", "7-ci mikrorayon", "7 ci mkr", "7-ci mkr"],
    "Dərnəgül": ["dərnəgül", "dernegul", "dərnəgül m", "dernegul m", "6-cı mkr", "6 ci mkr", "9-cu mkr", "9 ci mkr"],
    "İçərişəhər": ["içərişəhər", "iceriseher", "içəri şəhər", "iceri seher", "içərişəhər m", "axundov bağı", "governor", "fountain square"],
    "Sahil": ["sahil", "sahil m", "sahil metrosu", "bulvar", "tarqovi", "fəvvarələr", "torqoviy", "pedaqoji"],
    "Nizami": ["nizami m", "nizami metrosu", "qış parkı", "qis parki", "nizami kinoteatri", "beşmərtəbə"],
    "Xətai": ["xətai m", "xetai m", "xətai metrosu", "şah ismayıl xətai", "sah ismayil xetai", "ağ şəhər", "ag seher", "ali mehkeme"],
    "Cəfər Cabbarlı": ["cəfər cabbarlı", "cefer cabbarli", "c.cabbarlı"],
    "Ulduz": ["ulduz", "ulduz m", "ulduz metrosu"],
    "Koroğlu": ["koroğlu", "koroglu", "koroğlu m", "koroglu m", "məşədi əzizbəyov", "azik"],
    "Qara Qarayev": ["qara qarayev", "qarayev", "qara qarayev m", "qarayev m", "planet"],
    "Neftçilər": ["neftçilər", "neftciler", "neftçilər m", "neftciler m", "intertibb", "icra hakimiyyəti"],
    "Xalqlar Dostluğu": ["xalqlar", "xalqlar dostluğu", "xalqlar dostlugu", "xalqlar m", "laçın", "babək prospekti"],
    "Əhmədli": ["əhmədli", "ehmedli", "əhmədli m", "ehmedli m", "sarayevo", "baku medical plaza"],
    "Həzi Aslanov": ["həzi aslanov", "hezi aslanov", "aslanov", "aslanov m", "həzi aslanov m", "kvadratlar"],
    "Avtovağzal": ["avtovağzal", "avtovagzal", "avtovağzal m", "avtovagzal m", "beynəlxalq avtovağzal"],
    "8 Noyabr": ["8 noyabr", "8noyabr", "8 noyabr m", "8 noyabr metrosu", "hərbi hospital"],
    "Xocəsən": ["xocəsən", "xocesen", "xocəsən m", "xocesen m"]
}

# Baku Metro Lines Network Adjacency Graph (1-stop neighboring stations)
METRO_ADJACENCY: Dict[str, List[str]] = {
    "Dərnəgül": ["Azadlıq prospekti"],
    "Azadlıq prospekti": ["Dərnəgül", "Nəsimi"],
    "Nəsimi": ["Azadlıq prospekti", "Memar Əcəmi"],
    "Memar Əcəmi": ["Nəsimi", "20 Yanvar", "8 Noyabr", "Avtovağzal"],
    "20 Yanvar": ["Memar Əcəmi", "İnşaatçılar"],
    "İnşaatçılar": ["20 Yanvar", "Elmlər Akademiyası"],
    "Elmlər Akademiyası": ["İnşaatçılar", "Nizami"],
    "Nizami": ["Elmlər Akademiyası", "28 May"],
    "28 May": ["Nizami", "Gənclik", "Sahil", "Cəfər Cabbarlı"],
    "Cəfər Cabbarlı": ["28 May", "Xətai"],
    "Sahil": ["28 May", "İçərişəhər"],
    "İçərişəhər": ["Sahil"],
    "Gənclik": ["28 May", "Nəriman Nərimanov"],
    "Nəriman Nərimanov": ["Gənclik", "Ulduz"],
    "Ulduz": ["Nəriman Nərimanov", "Koroğlu"],
    "Koroğlu": ["Ulduz", "Qara Qarayev"],
    "Qara Qarayev": ["Koroğlu", "Neftçilər"],
    "Neftçilər": ["Qara Qarayev", "Xalqlar Dostluğu"],
    "Xalqlar Dostluğu": ["Neftçilər", "Əhmədli"],
    "Əhmədli": ["Xalqlar Dostluğu", "Həzi Aslanov"],
    "Həzi Aslanov": ["Əhmədli"],
    "8 Noyabr": ["Memar Əcəmi", "Avtovağzal"],
    "Avtovağzal": ["8 Noyabr", "Memar Əcəmi", "Xocəsən"],
    "Xocəsən": ["Avtovağzal"],
    "Xətai": ["Cəfər Cabbarlı", "28 May"]
}

BAKU_DISTRICTS: Dict[str, List[str]] = {
    "Binəqədi": ["binəqədi r", "bineqedi r", "binəqədi rayonu", "bineqedi rayonu", "binəqədidə", "bineqedide", "binəqədi", "bineqedi"],
    "Nəsimi": ["nəsimi r", "nesimi r", "nəsimi rayonu", "nesimi rayonu", "nəsimidə", "nesimide", "nəsimi", "nesimi"],
    "Yasamal": ["yasamal r", "yasamal rayonu", "yasamalda", "yeni yasamal", "yasamal"],
    "Xətai": ["xətai r", "xetai r", "xətai rayonu", "xetai rayonu", "xətaidə", "xetaide", "xətai", "xetai"],
    "Nərimanov": ["nərimanov r", "nerimanov r", "nərimanov rayonu", "nerimanov rayonu", "nərimanovda", "nerimanovda", "nərimanov", "nerimanov"],
    "Səbail": ["səbail r", "sebail r", "səbail rayonu", "sebail rayonu", "səbaildə", "sebailde", "səbail", "sebail"],
    "Nizami": ["nizami r", "nizami rayonu", "nizamidə", "nizamide"],
    "Sabunçu": ["sabunçu r", "sabuncu r", "sabunçu rayonu", "sabuncu rayonu", "sabunçuda", "sabuncuda", "sabunçu", "sabuncu"],
    "Suraxanı": ["suraxanı r", "suraxani r", "suraxanı rayonu", "suraxani rayonu", "suraxanıda", "suraxanida", "suraxanı", "suraxani"],
    "Xəzər": ["xəzər r", "xezer r", "xəzər rayonu", "xezer rayonu", "xəzərdə", "xezerde", "xəzər", "xezer"],
    "Abşeron": ["abşeron r", "abseron r", "abşeron rayonu", "abseron rayonu", "abşeronda", "abseronda", "abşeron", "abseron"],
    "Sumqayıt": ["sumqayıt", "sumqayit", "sumqayıtda", "sumqayitda"],
    "Qaradağ": ["qaradağ r", "qaradag r", "qaradağ rayonu", "qaradag rayonu", "qaradağda", "qaradagda", "qaradağ", "qaradag"],
    "Pirallahi": ["pirallahi", "pirallahı", "pirallahida", "pirallahıda"]
}

# Baku Micro-Locations, Settlements & Quarters (Qəsəbələr, Mikrorayonlar, Yaşayış Massivləri)
BAKU_SETTLEMENTS: Dict[str, List[str]] = {
    "Badamdar": ["badamdar", "badamdarda", "badamdar qəs", "badamdar qes", "1-ci massiv", "2-ci massiv", "3-cü massiv"],
    "Bayıl": ["bayıl", "bayil", "bayılda", "bayilde", "20-ci sahə", "20 ci sahe", "krasin"],
    "Şıxov": ["şıxov", "sixov", "şıxovda", "bibiheybət", "bibiheybet"],
    "Bakıxanov": ["bakıxanov", "bakixanov", "bakıxanovda", "bakixanovda", "razin", "razində"],
    "Qaraçuxur": ["qaraçuxur", "qaracuxur", "qaraçuxurda", "qaracuxurda"],
    "Yeni Günəşli": ["yeni günəşli", "yeni gunesli", "günəşli", "gunesli", "v massivi", "ab massivi", "d massivi", "q massivi"],
    "Köhnə Günəşli": ["köhnə günəşli", "kohne gunesli"],
    "Əhmədli": ["əhmədli qəs", "ehmedli qes", "əhmədli kəndi", "ehmedli kendi"],
    "Hövsan": ["hövsan", "hovsan", "hövsanda", "hovsanda", "hövsan qəs", "hovsan qes"],
    "Biləcəri": ["biləcəri", "bileceri", "biləcəridə", "bileceride"],
    "Sulutəpə": ["sulutəpə", "sulutepe"],
    "Rəsulzadə": ["rəsulzadə", "resulzade", "m.ə.rəsulzadə", "xutor"],
    "Binə": ["binə qəs", "bine qes", "binədə", "binede", "atçılıq", "südçülük"],
    "Mərdəkan": ["mərdəkan", "merdekan", "mərdəkanda", "merdekanda"],
    "Şüvəlan": ["şüvəlan", "suvelan", "şüvəlanda", "suvelanda"],
    "Buzovna": ["buzovna", "buzovnada"],
    "Bilgəh": ["bilgəh", "bilgeh", "bilgəhdə", "bilgehde"],
    "Zabrat": ["zabrat", "zabratda", "zabrat 1", "zabrat 2", "zabrat qəs"],
    "Maştağa": ["maştağa", "mastaga", "maştağada", "mastagada"],
    "Nardaran": ["nardaran", "nardaranda", "sea breeze"],
    "Pirşağı": ["pirşağı", "pirsagi", "pirşağıda"],
    "Kürdəxanı": ["kürdəxanı", "kurdexani"],
    "Balaxanı": ["balaxanı", "balaxani"],
    "Ramana": ["ramana", "ramanada"],
    "Əmircan": ["əmircan", "emircan"],
    "Bülbülə": ["bülbülə", "bulbule"],
    "Zirə": ["zirə", "zire"],
    "Türkan": ["türkan", "turkan"],
    "Qala": ["qala", "qala qəs", "qalada"],
    "Zığ": ["zığ", "zig", "zığ şossesi", "zig sossesi"],
    "Xırdalan": ["xırdalan", "xirdalan", "xırdalanda", "xirdalanda", "aaaf park", "kristal abseron xirdalan"],
    "Masazır": ["masazır", "masazir", "masazırda", "masazirda", "qurtuluş 93", "yeni baki"],
    "Saray": ["saray", "sarayda", "saray qəs"],
    "Novxanı": ["novxanı", "novxani", "novxanıda"],
    "Mehdiabad": ["mehdiabad", "mehdiabadda"],
    "Fatmayı": ["fatmayı", "fatmayi"],
    "Digah": ["digah"],
    "Məmmədli": ["məmədli", "məhəmmədi", "mehemmedi", "mammedli"],
    "Lökbatan": ["lökbatan", "lokbatan", "lökbatanda", "sederek"],
    "Sahil": ["sahil qəs", "sahil qes"],
    "Qobustan": ["qobustan qəs", "qobustan qes"],
    "Ağ Şəhər": ["ağ şəhər", "ag seher", "white city", "baku white city"],
    "Port Baku": ["port baku", "port baki"],
    "Montin": ["montin", "montində", "montinde"],
    "Papanin": ["papanin", "papanində"],
    "Kubinka": ["kubinka", "kubinkada"],
    "Sovetski": ["sovetski", "sovet"],
    "1-ci mikrorayon": ["1-ci mikrorayon", "1 ci mikrorayon", "1-ci mkr", "1 ci mkr", "1mkr"],
    "2-ci mikrorayon": ["2-ci mikrorayon", "2 ci mikrorayon", "2-ci mkr", "2 ci mkr", "2mkr"],
    "3-cü mikrorayon": ["3-cü mikrorayon", "3 cu mikrorayon", "3-cü mkr", "3 cu mkr", "3mkr"],
    "4-cü mikrorayon": ["4-cü mikrorayon", "4 cu mikrorayon", "4-cü mkr", "4 cu mkr", "4mkr"],
    "5-ci mikrorayon": ["5-ci mikrorayon", "5 ci mikrorayon", "5-ci mkr", "5 ci mkr", "5mkr"],
    "6-cı mikrorayon": ["6-cı mikrorayon", "6 ci mikrorayon", "6-cı mkr", "6 ci mkr", "6mkr"],
    "7-ci mikrorayon": ["7-ci mikrorayon", "7 ci mikrorayon", "7-ci mkr", "7 ci mkr", "7mkr"],
    "8-ci mikrorayon": ["8-ci mikrorayon", "8 ci mikrorayon", "8-ci mkr", "8 ci mkr", "8mkr"],
    "9-cu mikrorayon": ["9-cu mikrorayon", "9 cu mikrorayon", "9-cu mkr", "9 ci mkr", "9mkr"]
}

# Baku Adjacent Geographical Neighboring Districts
DISTRICT_ADJACENCY: Dict[str, List[str]] = {
    "Binəqədi": ["Nəsimi", "Nərimanov", "Abşeron"],
    "Nəsimi": ["Yasamal", "Binəqədi", "Nərimanov", "Səbail"],
    "Yasamal": ["Nəsimi", "Səbail", "Binəqədi", "Abşeron"],
    "Səbail": ["Yasamal", "Nəsimi", "Xətai", "Qaradağ"],
    "Nərimanov": ["Nəsimi", "Binəqədi", "Nizami", "Xətai"],
    "Nizami": ["Nərimanov", "Xətai", "Sabunçu", "Suraxanı"],
    "Xətai": ["Nərimanov", "Nizami", "Suraxanı", "Səbail"],
    "Sabunçu": ["Nizami", "Suraxanı", "Abşeron", "Xəzər"],
    "Suraxanı": ["Xətai", "Nizami", "Sabunçu", "Xəzər"],
    "Xəzər": ["Sabunçu", "Suraxanı", "Pirallahi"],
    "Abşeron": ["Binəqədi", "Yasamal", "Sabunçu", "Sumqayıt", "Qaradağ"],
    "Sumqayıt": ["Abşeron"],
    "Qaradağ": ["Səbail", "Yasamal", "Abşeron"],
    "Pirallahi": ["Xəzər"]
}

def extract_metro_station(text: str) -> Optional[str]:
    """Extract Baku Metro station name from text input if present."""
    stations = extract_all_metro_stations(text)
    return stations[0] if stations else None

def extract_all_metro_stations(text: str) -> List[str]:
    """Extract all Baku Metro station names mentioned in text in order of appearance."""
    if not text:
        return []
    text_lower = text.lower()
    found = []
    # Sort by position in text if multiple
    for station_name, aliases in BAKU_METRO_STATIONS.items():
        for alias in aliases:
            pos = text_lower.find(alias)
            if pos != -1:
                if station_name not in found:
                    found.append((pos, station_name))
                break
    found.sort(key=lambda x: x[0])
    return [name for _, name in found]

def extract_baku_settlement(text: str) -> Optional[str]:
    """Extract specific Baku settlement or micro-district name."""
    settlements = extract_all_baku_settlements(text)
# Mapping of Settlements/Quarters to Parent Baku Administrative Districts
SETTLEMENT_TO_DISTRICT: Dict[str, str] = {
    "Badamdar": "Səbail", "Bayıl": "Səbail", "Şıxov": "Səbail",
    "Bakıxanov": "Sabunçu", "Zabrat": "Sabunçu", "Maştağa": "Sabunçu", "Nardaran": "Sabunçu", "Bilgəh": "Sabunçu", "Pirşağı": "Sabunçu", "Kürdəxanı": "Sabunçu", "Balaxanı": "Sabunçu", "Ramana": "Sabunçu",
    "Qaraçuxur": "Suraxanı", "Yeni Günəşli": "Suraxanı", "Köhnə Günəşli": "Suraxanı", "Hövsan": "Suraxanı", "Əmircan": "Suraxanı", "Bülbülə": "Suraxanı", "Zığ": "Suraxanı",
    "Biləcəri": "Binəqədi", "Sulutəpə": "Binəqədi", "Rəsulzadə": "Binəqədi", "6-cı mikrorayon": "Binəqədi", "7-ci mikrorayon": "Binəqədi", "8-ci mikrorayon": "Binəqədi", "9-cu mikrorayon": "Binəqədi", "Binəqədi qəs.": "Binəqədi",
    "1-ci mikrorayon": "Nəsimi", "2-ci mikrorayon": "Nəsimi", "3-cü mikrorayon": "Nəsimi", "4-cü mikrorayon": "Nəsimi", "5-ci mikrorayon": "Nəsimi", "Papanin": "Nəsimi", "Kubinka": "Nəsimi",
    "Mərdəkan": "Xəzər", "Şüvəlan": "Xəzər", "Buzovna": "Xəzər", "Binə": "Xəzər", "Qala": "Xəzər", "Zirə": "Xəzər", "Türkan": "Xəzər", "Şaqan": "Xəzər",
    "Xırdalan": "Abşeron", "Masazır": "Abşeron", "Saray": "Abşeron", "Novxanı": "Abşeron", "Mehdiabad": "Abşeron", "Fatmayı": "Abşeron", "Digah": "Abşeron", "Məmmədli": "Abşeron", "Qobu": "Abşeron", "Hökməli": "Abşeron",
    "Ağ Şəhər": "Xətai", "Əhmədli": "Xətai", "Həzi Aslanov": "Xətai", "NZS": "Xətai",
    "Montin": "Nərimanov", "Böyükşor": "Nərimanov",
    "Yeni Yasamal": "Yasamal",
    "Lökbatan": "Qaradağ", "Sahil qəs.": "Qaradağ", "Qobustan": "Qaradağ", "Səngəçal": "Qaradağ",
    "Pirallahi": "Pirallahi", "Gürgən": "Pirallahi"
}

# Mapping of Baku Metro Stations to Parent Administrative Districts
METRO_TO_DISTRICT: Dict[str, str] = {
    "Elmlər Akademiyası": "Yasamal", "İnşaatçılar": "Yasamal", "20 Yanvar": "Yasamal",
    "28 May": "Nəsimi", "Memar Əcəmi": "Nəsimi", "Nəsimi": "Nəsimi", "8 Noyabr": "Nəsimi", "Cəfər Cabbarlı": "Nəsimi",
    "Gənclik": "Nərimanov", "Nəriman Nərimanov": "Nərimanov",
    "Xətai": "Xətai", "Əhmədli": "Xətai", "Həzi Aslanov": "Xətai",
    "Qara Qarayev": "Nizami", "Neftçilər": "Nizami", "Xalqlar Dostluğu": "Nizami",
    "İçərişəhər": "Səbail", "Sahil": "Səbail",
    "Azadlıq prospekti": "Binəqədi", "Dərnəgül": "Binəqədi", "Avtovağzal": "Binəqədi", "Xocəsən": "Binəqədi",
    "Ulduz": "Nərimanov", "Koroğlu": "Nizami", "Nizami": "Yasamal"
}

def get_all_aliases_for_location(loc_name: str) -> List[str]:
    """
    Returns comprehensive keywords & aliases for a search location.
    If loc_name is a district, includes all metro stations, settlements, and micro-locations situated within that district.
    """
    if not loc_name:
        return []
    
    loc_clean = loc_name.strip()
    aliases = list(BAKU_SETTLEMENTS.get(loc_clean, [])) + list(BAKU_METRO_STATIONS.get(loc_clean, [])) + list(BAKU_DISTRICTS.get(loc_clean, []))
    
    # If loc_clean is a District (e.g. Yasamal, Nəsimi), also pull all child settlements and metros
    for s_name, parent_dist in SETTLEMENT_TO_DISTRICT.items():
        if parent_dist.lower() == loc_clean.lower() or loc_clean.lower() in parent_dist.lower():
            aliases.extend(BAKU_SETTLEMENTS.get(s_name, []))
            aliases.append(s_name.lower())
            
    for m_name, parent_dist in METRO_TO_DISTRICT.items():
        if parent_dist.lower() == loc_clean.lower() or loc_clean.lower() in parent_dist.lower():
            aliases.extend(BAKU_METRO_STATIONS.get(m_name, []))
            aliases.append(m_name.lower())
            
    aliases.append(loc_clean.lower())
    return list(dict.fromkeys(aliases))

def extract_baku_settlement(text: str) -> Optional[str]:
    """Extract primary Baku settlement or micro-district from text."""
    settlements = extract_all_baku_settlements(text)
    return settlements[0] if settlements else None

def extract_all_baku_settlements(text: str) -> List[str]:
    """Extract all specific Baku settlements and micro-locations mentioned in text."""
    if not text:
        return []
    text_lower = text.lower()
    found = []
    for s_name, keywords in BAKU_SETTLEMENTS.items():
        for kw in keywords:
            pos = text_lower.find(kw)
            if pos != -1:
                if s_name not in found:
                    found.append((pos, s_name))
                break
    found.sort(key=lambda x: x[0])
    return [name for _, name in found]

def extract_baku_district(text: str) -> Optional[str]:
    """Extract official Baku district name from text input. Returns None if no district found."""
    districts = extract_all_baku_districts(text)
    return districts[0] if districts else None

def extract_all_baku_districts(text: str) -> List[str]:
    """Extract all official Baku district names mentioned in text in order of appearance."""
    if not text:
        return []
    text_lower = text.lower()
    found = []
    for dist_name, keywords in BAKU_DISTRICTS.items():
        for kw in keywords:
            pos = text_lower.find(kw)
            if pos != -1:
                if dist_name not in found:
                    found.append((pos, dist_name))
                break
    found.sort(key=lambda x: x[0])
    return [name for _, name in found]

def extract_all_locations(text: str) -> List[str]:
    """Extract all distinct locations (settlements, metro stations, districts) with maximum precision."""
    settlements = extract_all_baku_settlements(text)
    metros = extract_all_metro_stations(text)
    districts = extract_all_baku_districts(text)
    return list(dict.fromkeys(settlements + metros + districts))

def is_adjacent_metro(target_metro: str, candidate_metro: str) -> bool:
    """Returns True if candidate_metro is an immediate 1-stop neighbor of target_metro."""
    if not target_metro or not candidate_metro:
        return False
    neighbors = METRO_ADJACENCY.get(target_metro, [])
    return candidate_metro in neighbors

def is_adjacent_district(target_district: str, candidate_district: str) -> bool:
    """Returns True if candidate_district is an immediate geographical neighbor of target_district."""
    if not target_district or not candidate_district:
        return False
    neighbors = DISTRICT_ADJACENCY.get(target_district, [])
    return candidate_district in neighbors

def extract_az_phone(text: str) -> Optional[tuple[str, str]]:
    """
    Extract Azerbaijani phone number from text.
    Returns (formatted_display, raw_digits_for_tel_url) or None.
    Example: ('+994 50 123 45 67', '+994501234567')
    """
    import re
    if not text:
        return None
    m = re.search(r'(?:\+?994\s*|0)?\s*\(?\s*(50|51|55|70|77|99|12|10)\s*\)?\s*[\s.-]?\s*(\d{3})\s*[\s.-]?\s*(\d{2})\s*[\s.-]?\s*(\d{2})', text)
    if m:
        prefix, p1, p2, p3 = m.group(1), m.group(2), m.group(3), m.group(4)
        formatted = f"+994 {prefix} {p1} {p2} {p3}"
        raw_digits = f"+994{prefix}{p1}{p2}{p3}"
        return formatted, raw_digits
    return None
