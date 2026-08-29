import re
from typing import Optional, List, Dict

BAKU_METRO_STATIONS: Dict[str, List[str]] = {
    "Elmlər Akademiyası": [
        "elmlər", "elmler", "elmlər akademiyası", "elmler akademiyasi", "elmlər m", "elmler m",
        "bdu", "bakı dövlət universiteti", "baki dovlet universiteti", "dövlət universiteti", "dovlet universiteti", "baku state university",
        "aztu", "texniki universitet", "texniki universiteti", "politexnik", "politexnik institutu",
        "azmiu", "azmıu", "memarlıq və inşaat universiteti", "memarliq ve insaat universiteti", "inşaat universiteti", "insaat universiteti", "inşaat institutu", "inşaat unisi",
        "admiu", "admıu", "incəsənət universiteti", "incesenet universiteti", "mədəniyyət və incəsənət",
        "avropa liseyi", "bakı avropa liseyi", "zərifə əliyeva liseyi", "zerife eliyeva liseyi", "zərifə əliyeva adına",
        "fritl", "fizika riyaziyyat liseyi", "fizika-riyaziyyat liseyi",
        "20 nömrəli məktəb", "20 nomreli mekteb", "20 saylı məktəb", "20 sayli mekteb", "20 nömrəli",
        "53 nömrəli məktəb", "53 nomreli mekteb", "53 saylı məktəb",
        "hüseyn cavid", "huseyn cavid", "mətbuat prospekti", "metbuat prospekti"
    ],
    "28 May": [
        "28 may", "28may", "28 may m", "may 28", "vağzal", "vagzal", "dilarə əliyeva", "28 mall", "28 mol",
        "adnsu", "azii", "azii universiteti", "azii-nin yanı", "neft akademiyası", "neft akademiyasi", "azərbaycan dövlət neft və sənaye", "neft institutu",
        "adu", "dillər universiteti", "diller universiteti", "xarici dillər", "xarici diller", "inyaz",
        "bsu", "slavyan universiteti", "slavyan", "baki slavyan universiteti", "api rus",
        "bma", "konservatoriya", "musiqi akademiyası", "musiqi akademiyasi", "hacıbəyov adına musiqi",
        "ufaz", "fransız azərbaycan universiteti", "fransiz azerbaycan universiteti",
        "azərbaycan universiteti", "azerbaycan universiteti",
        "elitar gimnaziya", "elitar lisey", "ilyas əfəndiyev adına",
        "dəmir yolu liseyi", "demir yolu liseyi",
        "160 nömrəli məktəb", "160 nomreli mekteb", "160 saylı məktəb", "160 nömrəli gimnaziya", "160 nömrəli",
        "23 nömrəli məktəb", "23 nomreli mekteb", "23 saylı məktəb", "23 nömrəli",
        "46 nömrəli məktəb", "46 nomreli mekteb", "46 saylı məktəb",
        "8 nömrəli məktəb", "8 nomreli mekteb", "8 saylı məktəb"
    ],
    "Gənclik": [
        "gənclik", "genclik", "gənclik m", "genclik m", "gənclik mall", "genclik mall", "zoopark",
        "atu", "tibb universiteti", "tibb institutu", "tibb instutu", "tibb unisi", "azərbaycan tibb universiteti", "tibb",
        "ada", "ada universiteti", "ada unisi", "diplomatik akademiya", "ada university",
        "oyu", "odlar yurdu", "odlar yurdu universiteti",
        "adbtia", "adbtıa", "idman akademiyası", "idman akademiyasi", "bədən tərbiyəsi akademiyası", "fizkultura institutu",
        "dünya məktəbi", "dunya mektebi", "dunya school",
        "258 nömrəli məktəb", "258 nomreli mekteb", "258 saylı məktəb",
        "koroglu heykeli", "koroğlu parkı", "dədə qorqud parkı"
    ],
    "Nəriman Nərimanov": [
        "nərimanov", "nerimanov", "nərmanov", "nermanov", "nərman", "nerman", "n.nərimanov", "nərimanov m", "nerimanov m", "nərmanov m", "nermanov m", "montin", "metropark", "life centre",
        "adra", "rəssamlıq akademiyası", "ressamliq akademiyasi", "rəssamlıq",
        "kooperasiya universiteti", "kooperasiya unisi", "kooperasiya institutu",
        "tərəqqi liseyi", "tereqqi liseyi",
        "müasir təhsil kompleksi", "muasir tehsil kompleksi", "mtk məktəbi", "mtk məktəb",
        "200 nömrəli məktəb", "200 nomreli mekteb", "200 saylı məktəb",
        "177 nömrəli məktəb", "177 nomreli mekteb", "177 saylı məktəb"
    ],
    "İnşaatçılar": [
        "inşaatçılar", "insaatcilar", "inşaatçılar m", "insaatcilar m", "qələbə dairəsi", "qelebe dairesi", "şərifzadə", "serifzade", "yasamal ats",
        "158 nömrəli məktəb", "158 nomreli mekteb", "158 saylı məktəb"
    ],
    "20 Yanvar": [
        "20 yanvar", "20yanvar", "20 yanvar m", "velotrek", "onkoloji", "respublika xəstəxanası", "şamaxinka", "samaxinka",
        "qızlar universiteti", "qizlar universiteti", "bakı qızlar universiteti",
        "incəsənət gimnaziyası", "incesenet gimnaziyasi", "respublika incəsənət gimnaziyası"
    ],
    "Memar Əcəmi": [
        "əcəmi", "ecemi", "memar əcəmi", "memar ecemi", "əcəmi m", "ecemi m", "3-cü mkr", "4-cü mkr", "5-ci mkr",
        "247 nömrəli məktəb", "247 nomreli mekteb", "247 saylı məktəb"
    ],
    "Nəsimi": ["nəsimi m", "nesimi m", "nəsimi metrosu", "nesimi metrosu", "zarifa aliyeva parki"],
    "Azadlıq prospekti": [
        "azadlıq", "azadliq", "azadlıq m", "azadliq m", "azadlıq prospekti", "azadliq prospekti", "azadlıq metrosu", "azadliq metrosu",
        "8-ci mikrorayon", "8 ci mkr", "8-ci mkr", "7-ci mikrorayon", "7 ci mkr", "7-ci mkr",
        "hədəf liseyi", "hedef liseyi", "hədəf məktəbi",
        "244 nömrəli məktəb", "244 nomreli mekteb", "244 saylı məktəb",
        "83 nömrəli məktəb", "83 nomreli mekteb", "83 saylı məktəb"
    ],
    "Dərnəgül": [
        "dərnəgül", "dernegul", "dərnəgül m", "dernegul m", "6-cı mkr", "6 ci mkr", "9-cu mkr", "9 ci mkr",
        "tisa", "tisa school", "the international school of azerbaijan",
        "baku international school", "bis məktəbi",
        "115 nömrəli məktəb", "115 nomreli mekteb", "115 saylı məktəb"
    ],
    "İçərişəhər": [
        "içərişəhər", "iceriseher", "içəri şəhər", "iceri seher", "içərişəhər m", "governor", "qubernator bağı", "filarmoniya",
        "unec", "adiu", "iqtisad universiteti", "iqtisadiyyat universiteti", "narxoz", "narxozun yanı", "dövlət iqtisad universiteti",
        "dia", "dövlət idarəçilik akademiyası", "dovlet idarecilik akademiyasi", "idarəçilik akademiyası", "prezident yanında idarəçilik",
        "qərbi kaspi universiteti", "qerbi kaspi universiteti", "qərb universiteti", "qerb universiteti", "western university",
        "6 nömrəli məktəb", "6 nomreli mekteb", "6 saylı məktəb", "6 nömrəli",
        "134 nömrəli məktəb", "134 nomreli mekteb", "134 saylı məktəb", "134 nömrəli",
        "189 nömrəli məktəb", "190 nömrəli məktəb", "189 saylı məktəb", "190 saylı məktəb"
    ],
    "Sahil": [
        "sahil m", "sahil metrosu", "sahil stansiyası", "sahildə m", "sahilde m", "sahil bağı", "malakan bağı",
        "adpu", "pedaqoji", "pedaqoji universitet", "pedaqoji universiteti", "api", "apinin yanı", "dövlət pedaqoji universiteti",
        "bülbül adına musiqi məktəbi", "bulbul adina musiqi mektebi", "bülbül adına məktəb"
    ],
    "Nizami": ["nizami m", "nizami metrosu", "qış parkı", "qis parki", "nizami kinoteatri", "beşmərtəbə"],
    "Xətai": [
        "xətai m", "xetai m", "xətai metrosu", "şah ismayıl xətai", "sah ismayil xetai", "ağ şəhər", "ag seher", "ali mehkeme",
        "fransız liseyi", "fransiz liseyi", "baku francais lycee",
        "kaspi liseyi", "kaspi məktəbi",
        "27 nömrəli məktəb", "27 nomreli mekteb", "27 saylı məktəb"
    ],
    "Cəfər Cabbarlı": ["cəfər cabbarlı", "cefer cabbarli", "c.cabbarlı"],
    "Ulduz": ["ulduz", "ulduz m", "ulduz metrosu"],
    "Koroğlu": [
        "koroğlu", "koroglu", "koroğlu m", "koroglu m", "məşədi əzizbəyov", "azik",
        "baau", "avrasiya universiteti", "bakı avrasiya universiteti", "gimnastika arenası"
    ],
    "Qara Qarayev": [
        "qara qarayev", "qarayev", "qara qarayev m", "qarayev m", "planet",
        "251 nömrəli məktəb", "251 nomreli mekteb", "251 saylı məktəb"
    ],
    "Neftçilər": [
        "neftçilər", "neftciler", "neftçilər m", "neftciler m", "intertibb", "icra hakimiyyəti",
        "xəzər universiteti", "xezer universiteti", "khazar university", "xəzər unisi",
        "214 nömrəli məktəb", "214 nomreli mekteb", "214 saylı məktəb",
        "220 nömrəli məktəb", "220 nomreli mekteb", "220 saylı məktəb"
    ],
    "Xalqlar Dostluğu": [
        "xalqlar", "xalqlar dostluğu", "xalqlar dostlugu", "xalqlar m", "laçın", "babək prospekti",
        "272 nömrəli məktəb", "272 nomreli mekteb", "272 saylı məktəb"
    ],
    "Əhmədli": [
        "əhmədli m", "ehmedli m", "əhmədli metrosu", "ehmedli metrosu", "sarayevo", "baku medical plaza",
        "95 nömrəli məktəb", "95 nomreli mekteb", "95 saylı məktəb"
    ],
    "Həzi Aslanov": [
        "həzi aslanov", "hezi aslanov", "aslanov", "aslanov m", "həzi aslanov m", "kvadratlar",
        "257 nömrəli məktəb", "257 nomreli mekteb", "257 saylı məktəb"
    ],
    "Avtovağzal": ["avtovağzal", "avtovagzal", "avtovağzal m", "avtovagzal m", "beynəlxalq avtovağzal"],
    "8 Noyabr": ["8 noyabr", "8noyabr", "8 noyabr m", "8 noyabr metrosu", "hərbi hospital"],
    "Xocəsən": [
        "xocəsən", "xocesen", "xocəsən m", "xocesen m",
        "mdu", "lomonosov universiteti", "moskva dövlət universiteti"
    ],
    "Bakmil": ["bakmil", "bakmil m", "bakmil metrosu"]
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
    "Nəriman Nərimanov": ["Gənclik", "Ulduz", "Bakmil"],
    "Bakmil": ["Nəriman Nərimanov", "Ulduz"],
    "Ulduz": ["Nəriman Nərimanov", "Koroğlu", "Bakmil"],
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
    "Nərimanov": ["nərimanov r", "nerimanov r", "nərmanov r", "nermanov r", "nərimanov rayonu", "nerimanov rayonu", "nərmanov rayonu", "nermanov rayonu", "nərimanovda", "nerimanovda", "nərmanovda", "nermanovda", "nərimanov", "nerimanov", "nərmanov", "nermanov"],
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
    "Badamdar": [
        "badamdar", "badamdarda", "badamdar qəs", "badamdar qes", "1-ci massiv", "2-ci massiv", "3-cü massiv",
        "oxford məktəbi", "oxford mektebi", "baku oxford school", "oksford məktəbi", "oxford school", "eas badamdar"
    ],
    "Bayıl": [
        "bayıl", "bayil", "bayılda", "bayilde", "20-ci sahə", "20 ci sahe", "krasin",
        "banm", "bhos", "bakı ali neft məktəbi", "baki ali neft mektebi", "ali neft məktəbi", "baku higher oil school",
        "landau bayıl", "su idmanı sarayı"
    ],
    "Şıxov": ["şıxov", "sixov", "şıxovda", "bibiheybət", "bibiheybet"],
    "Bakıxanov": ["bakıxanov", "bakixanov", "bakıxanovda", "bakixanovda", "razin", "razində", "kaspi bakıxanov"],
    "Qaraçuxur": ["qaraçuxur", "qaracuxur", "qaraçuxurda", "qaracuxurda"],
    "Yeni Günəşli": ["yeni günəşli", "yeni gunesli", "günəşli", "gunesli", "v massivi", "ab massivi", "d massivi", "q massivi"],
    "Köhnə Günəşli": ["köhnə günəşli", "kohne gunesli"],
    "Yeni Yasamal": [
        "yeni yasamal", "yeni yasamalda", "dadaş bünyadzadə", "dadas bunyadzade", "əsəd əhmədov", "esed ehmedov",
        "286 nömrəli məktəb", "286 nomreli mekteb", "286 saylı məktəb"
    ],
    "Əhmədli": ["əhmədli qəs", "ehmedli qes", "əhmədli kəndi", "ehmedli kendi"],
    "Hövsan": ["hövsan", "hovsan", "hövsanda", "hovsanda", "hövsan qəs", "hovsan qes"],
    "Biləcəri": ["biləcəri", "bileceri", "biləcəridə", "bileceride"],
    "Sulutəpə": ["sulutəpə", "sulutepe"],
    "Rəsulzadə": ["rəsulzadə", "resulzade", "m.ə.rəsulzadə", "xutor"],
    "Binə": ["binə qəs", "bine qes", "binədə", "binede", "atçılıq", "südçülük", "maa", "aviasiya akademiyası", "milli aviasiya"],
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
    "Xırdalan": [
        "xırdalan", "xirdalan", "xırdalanda", "xirdalanda", "aaaf park", "kristal abseron xirdalan",
        "bmu", "mühəndislik universiteti", "muhendislik universiteti", "qafqaz universiteti", "qafqaz unisi"
    ],
    "Masazır": [
        "masazır", "masazir", "masazırda", "masazirda", "qurtuluş 93", "yeni baki",
        "gömrük akademiyası", "gomruk akademiyasi"
    ],
    "Saray": ["saray", "sarayda", "saray qəs"],
    "Novxanı": ["novxanı", "novxani", "novxanıda"],
    "Mehdiabad": ["mehdiabad", "mehdiabadda"],
    "Fatmayı": ["fatmayı", "fatmayi"],
    "Digah": ["digah"],
    "Məmmədli": ["məmədli", "məhəmmədi", "mehemmedi", "mammedli"],
    "Lökbatan": ["lökbatan", "lokbatan", "lökbatanda", "sederek"],
    "Sahil": ["sahil qəs", "sahil qes", "sahil qəsəbəsi", "sahil qesebesi", "sahil qəs.", "sahil qes."],
    "Qobustan": ["qobustan qəs", "qobustan qes"],
    "Ağ Şəhər": [
        "ağ şəhər", "ag seher", "white city", "baku white city",
        "fransız liseyi", "fransiz liseyi", "baku francais lycee", "kaspi liseyi"
    ],
    "Port Baku": ["port baku", "port baki", "landau port baku", "landau school"],
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
    "9-cu mikrorayon": ["9-cu mikrorayon", "9 cu mikrorayon", "9-cu mkr", "9 ci mkr", "9mkr"],
    "Nizami küçəsi": ["nizami küç", "nizami kuc", "nizami küçəsi", "nizami kucesi", "nizami k.", "nizami k-si", "nizami k-də", "nizami kəs", "nizami prospekti"],
    "Torqovaya": ["torqovı", "torqovaya", "tarqovi", "tarqoviy", "torqovi", "fəvvarələr meydanı", "fevvareler meydani", "fountain square", "isr plaza"],
    "Şaqan": ["şaqan", "saqan", "şaqanda", "saqanda"],
    "Qobu": ["qobu", "qobuda"],
    "Hökməli": ["hökməli", "hokmeli", "hökməlidə", "hokmelide"],
    "NZS": ["nzs", "nzs qəs", "nzs qes", "nzs qəsəbəsi"],
    "Böyükşor": ["böyükşor", "boyuksor", "böyükşorda", "boyuksorda"],
    "Gürgən": ["gürgən", "gurgen", "gürgəndə"],
    "Səngəçal": ["səngəçal", "sengecal", "səngəçalda", "sangachal"],
    "Albalılıq": ["albalılıq", "albaliliq", "albalı", "vişnyovka", "visnyovka"],
    "Zuğulba": ["zuğulba", "zugulba", "zuğulbada"],
    "Dübəndi": ["dübəndi", "dubendi", "dübəndidə"],
    "Pirəkəşkül": ["pirəkəşkül", "pirekeskul"]
}

# Baku Universities, Academies and Higher Educational Institutes
BAKU_UNIVERSITIES: Dict[str, List[str]] = {
    "Bakı Dövlət Universiteti": ["bdu", "bakı dövlət universiteti", "baki dovlet universiteti", "dövlət universiteti", "dovlet universiteti", "baku state university"],
    "Azərbaycan Dövlət Neft və Sənaye Universiteti": ["adnsu", "azii", "azii universiteti", "azii-nin yanı", "neft akademiyası", "neft akademiyasi", "azərbaycan dövlət neft və sənaye", "azerbaycan dovlet neft ve senaye", "neft institutu"],
    "Azərbaycan Tibb Universiteti": ["atu", "tibb universiteti", "tibb institutu", "tibb instutu", "tibb unisi", "azərbaycan tibb universiteti", "azerbaycan tibb universiteti", "tibb"],
    "ADA Universiteti": ["ada", "ada universiteti", "ada unisi", "diplomatik akademiya", "ada university"],
    "Azərbaycan Texniki Universiteti": ["aztu", "texniki universitet", "texniki universiteti", "politexnik", "politexnik institutu", "politexnik unisi"],
    "Azərbaycan Memarlıq və İnşaat Universiteti": ["azmiu", "azmıu", "memarlıq və inşaat universiteti", "memarliq ve insaat universiteti", "inşaat universiteti", "insaat universiteti", "inşaat institutu", "insaat institutu", "inşaat unisi"],
    "Azərbaycan Dövlət İqtisad Universiteti": ["unec", "adiu", "iqtisad universiteti", "iqtisadiyyat universiteti", "narxoz", "narxozun yanı", "dövlət iqtisad universiteti"],
    "Azərbaycan Dövlət Pedaqoji Universiteti": ["adpu", "pedaqoji", "pedaqoji universitet", "pedaqoji universiteti", "api", "apinin yanı", "dövlət pedaqoji universiteti"],
    "Azərbaycan Dillər Universiteti": ["adu", "dillər universiteti", "diller universiteti", "xarici dillər", "xarici diller", "inyaz", "inyazın yanı"],
    "Bakı Slavyan Universiteti": ["bsu", "slavyan universiteti", "slavyan", "baki slavyan universiteti", "api rus"],
    "Milli Aviasiya Akademiyası": ["maa", "aviasiya akademiyası", "aviasiya akademiyasi", "aviasiya", "milli aviasiya akademiyası"],
    "Bakı Mühəndislik Universiteti": ["bmu", "mühəndislik universiteti", "muhendislik universiteti", "qafqaz universiteti", "qafqaz unisi"],
    "Xəzər Universiteti": ["xəzər universiteti", "xezer universiteti", "khazar university", "xəzər unisi"],
    "Bakı Ali Neft Məktəbi": ["banm", "bhos", "bakı ali neft məktəbi", "baki ali neft mektebi", "ali neft məktəbi", "baku higher oil school"],
    "Dövlət İdarəçilik Akademiyası": ["dia", "dövlət idarəçilik akademiyası", "dovlet idarecilik akademiyasi", "idarəçilik akademiyası", "prezident yanında idarəçilik"],
    "Bakı Musiqi Akademiyası": ["bma", "konservatoriya", "musiqi akademiyası", "musiqi akademiyasi", "hacıbəyov adına musiqi"],
    "Azərbaycan Dövlət Mədəniyyət və İncəsənət Universiteti": ["admiu", "admıu", "incəsənət universiteti", "incesenet universiteti", "mədəniyyət və incəsənət universiteti", "incəsənət institutu"],
    "Azərbaycan Dövlət Rəssamlıq Akademiyası": ["adra", "rəssamlıq akademiyası", "ressamliq akademiyasi", "rəssamlıq"],
    "Azərbaycan Dövlət Bədən Tərbiyəsi və İdman Akademiyası": ["adbtia", "adbtıa", "idman akademiyası", "idman akademiyasi", "bədən tərbiyəsi akademiyası", "fizkultura institutu"],
    "Dövlət Gömrük Komitəsinin Akademiyası": ["gömrük akademiyası", "gomruk akademiyasi"],
    "Bakı Avrasiya Universiteti": ["baau", "avrasiya universiteti", "bakı avrasiya universiteti"],
    "Azərbaycan Universiteti": ["azərbaycan universiteti", "azerbaycan universiteti"],
    "Qərbi Kaspi Universiteti": ["qərbi kaspi universiteti", "qerbi kaspi universiteti", "qərb universiteti", "qerb universiteti", "western university", "western caspian university"],
    "Odlar Yurdu Universiteti": ["oyu", "odlar yurdu", "odlar yurdu universiteti"],
    "Bakı Qızlar Universiteti": ["qızlar universiteti", "qizlar universiteti", "bakı qızlar universiteti"],
    "Azərbaycan Kooperasiya Universiteti": ["kooperasiya universiteti", "kooperasiya unisi", "kooperasiya institutu"],
    "Fransız-Azərbaycan Universiteti": ["ufaz", "fransız azərbaycan universiteti", "fransiz azerbaycan universiteti"],
    "MDU Bakı filialı": ["mdu", "lomonosov universiteti", "moskva dövlət universiteti"],
    "Seçenov adına MDMU": ["seçenov", "secenov", "seçenov adına tibb", "birinci mdmu"]
}

# Baku Schools, Lyceums, Gymnasiums & International Schools
BAKU_SCHOOLS: Dict[str, List[str]] = {
    "Bakı Oksford Məktəbi": ["oxford məktəbi", "oxford mektebi", "baku oxford school", "oksford məktəbi", "oxford school"],
    "Bakı Avropa Liseyi": ["avropa liseyi", "bakı avropa liseyi"],
    "Akademik Zərifə Əliyeva adına Lisey": ["zərifə əliyeva liseyi", "zerife eliyeva liseyi", "zərifə əliyeva adına lisey"],
    "Landau School": ["landau", "landau school", "landau məktəbi", "landau mektebi"],
    "Baku British School": ["baku british school", "british school", "britaniya məktəbi"],
    "European Azerbaijan School": ["eas", "european azerbaijan school", "avropa azərbaycan məktəbi"],
    "The International School of Azerbaijan": ["tisa", "tisa school", "the international school of azerbaijan"],
    "Baku International School": ["baku international school", "bis məktəbi"],
    "Müasir Təhsil Kompleksi": ["müasir təhsil kompleksi", "muasir tehsil kompleksi", "mtk məktəbi", "mtk məktəb"],
    "Dünya Məktəbi": ["dünya məktəbi", "dunya mektebi", "dunya school", "xəzər dünya məktəbi"],
    "Kaspi Liseyi": ["kaspi liseyi", "kaspi məktəbi", "kaspi lisey"],
    "Hədəf Liseyi": ["hədəf liseyi", "hedef liseyi", "hədəf məktəbi"],
    "Fizika Riyaziyyat Liseyi": ["fritl", "fizika riyaziyyat liseyi", "fizika-riyaziyyat liseyi"],
    "Bülbül adına Musiqi Məktəbi": ["bülbül adına musiqi məktəbi", "bulbul adina musiqi mektebi", "bülbül adına məktəb"],
    "Tərəqqi Liseyi": ["tərəqqi liseyi", "tereqqi liseyi"],
    "Elitar Gimnaziya": ["elitar gimnaziya", "elitar lisey", "ilyas əfəndiyev adına"],
    "Dəmir Yolu Liseyi": ["dəmir yolu liseyi", "demir yolu liseyi"],
    "Respublika İncəsənət Gimnaziyası": ["incəsənət gimnaziyası", "incesenet gimnaziyasi", "respublika incəsənət gimnaziyası"],
    "Bakı Fransız Liseyi": ["fransız liseyi", "fransiz liseyi", "baku francais lycee"],
    "23 nömrəli məktəb": ["23 nömrəli məktəb", "23 nomreli mekteb", "23 saylı məktəb", "23 sayli mekteb", "23 nömrəli"],
    "6 nömrəli məktəb": ["6 nömrəli məktəb", "6 nomreli mekteb", "6 saylı məktəb", "6 sayli mekteb", "6 nömrəli"],
    "160 nömrəli klassik gimnaziya": ["160 nömrəli məktəb", "160 nomreli mekteb", "160 saylı məktəb", "160 sayli mekteb", "160 nömrəli gimnaziya", "160 nömrəli klassik gimnaziya", "160 nömrəli"],
    "134 nömrəli məktəb": ["134 nömrəli məktəb", "134 nomreli mekteb", "134 saylı məktəb", "134 sayli mekteb", "134 nömrəli"],
    "189-190 nömrəli məktəb": ["189 nömrəli məktəb", "190 nömrəli məktəb", "189-190 nömrəli", "189 saylı məktəb", "190 saylı məktəb"],
    "20 nömrəli məktəb": ["20 nömrəli məktəb", "20 nomreli mekteb", "20 saylı məktəb", "20 sayli mekteb", "20 nömrəli lisey", "20 nömrəli"],
    "46 nömrəli məktəb": ["46 nömrəli məktəb", "46 nomreli mekteb", "46 saylı məktəb", "46 sayli mekteb"],
    "8 nömrəli məktəb": ["8 nömrəli məktəb", "8 nomreli mekteb", "8 saylı məktəb", "8 sayli mekteb"],
    "200 nömrəli məktəb": ["200 nömrəli məktəb", "200 nomreli mekteb", "200 saylı məktəb", "200 sayli mekteb"],
    "177 nömrəli məktəb": ["177 nömrəli məktəb", "177 nomreli mekteb", "177 saylı məktəb"],
    "258 nömrəli məktəb": ["258 nömrəli məktəb", "258 nomreli mekteb", "258 saylı məktəb"],
    "244 nömrəli məktəb": ["244 nömrəli məktəb", "244 nomreli mekteb", "244 saylı məktəb"],
    "83 nömrəli məktəb": ["83 nömrəli məktəb", "83 nomreli mekteb", "83 saylı məktəb"],
    "115 nömrəli məktəb": ["115 nömrəli məktəb", "115 nomreli mekteb", "115 saylı məktəb"],
    "247 nömrəli məktəb": ["247 nömrəli məktəb", "247 nomreli mekteb", "247 saylı məktəb"],
    "95 nömrəli məktəb": ["95 nömrəli məktəb", "95 nomreli mekteb", "95 saylı məktəb"],
    "27 nömrəli məktəb": ["27 nömrəli məktəb", "27 nomreli mekteb", "27 saylı məktəb"],
    "257 nömrəli məktəb": ["257 nömrəli məktəb", "257 nomreli mekteb", "257 saylı məktəb"],
    "251 nömrəli məktəb": ["251 nömrəli məktəb", "251 nomreli mekteb", "251 saylı məktəb"],
    "214 nömrəli məktəb": ["214 nömrəli məktəb", "214 nomreli mekteb", "214 saylı məktəb"],
    "220 nömrəli məktəb": ["220 nömrəli məktəb", "220 nomreli mekteb", "220 saylı məktəb"],
    "272 nömrəli məktəb": ["272 nömrəli məktəb", "272 nomreli mekteb", "272 saylı məktəb"],
    "53 nömrəli məktəb": ["53 nömrəli məktəb", "53 nomreli mekteb", "53 saylı məktəb"],
    "158 nömrəli məktəb": ["158 nömrəli məktəb", "158 nomreli mekteb", "158 saylı məktəb"],
    "286 nömrəli məktəb": ["286 nömrəli məktəb", "286 nomreli mekteb", "286 saylı məktəb"]
}

# Mapping of Universities to Nearest Metro Station
UNIVERSITY_TO_METRO: Dict[str, str] = {
    "Bakı Dövlət Universiteti": "Elmlər Akademiyası",
    "Azərbaycan Dövlət Neft və Sənaye Universiteti": "28 May",
    "Azərbaycan Tibb Universiteti": "Gənclik",
    "ADA Universiteti": "Gənclik",
    "Azərbaycan Texniki Universiteti": "Elmlər Akademiyası",
    "Azərbaycan Memarlıq və İnşaat Universiteti": "Elmlər Akademiyası",
    "Azərbaycan Dövlət İqtisad Universiteti": "İçərişəhər",
    "Azərbaycan Dövlət Pedaqoji Universiteti": "Sahil",
    "Azərbaycan Dillər Universiteti": "28 May",
    "Bakı Slavyan Universiteti": "28 May",
    "Xəzər Universiteti": "Neftçilər",
    "Dövlət İdarəçilik Akademiyası": "İçərişəhər",
    "Bakı Musiqi Akademiyası": "28 May",
    "Azərbaycan Dövlət Mədəniyyət və İncəsənət Universiteti": "Elmlər Akademiyası",
    "Azərbaycan Dövlət Rəssamlıq Akademiyası": "Nəriman Nərimanov",
    "Azərbaycan Dövlət Bədən Tərbiyəsi və İdman Akademiyası": "Gənclik",
    "Bakı Avrasiya Universiteti": "Koroğlu",
    "Azərbaycan Universiteti": "28 May",
    "Qərbi Kaspi Universiteti": "İçərişəhər",
    "Odlar Yurdu Universiteti": "Gənclik",
    "Bakı Qızlar Universiteti": "20 Yanvar",
    "Azərbaycan Kooperasiya Universiteti": "Nəriman Nərimanov",
    "Fransız-Azərbaycan Universiteti": "28 May",
    "MDU Bakı filialı": "Xocəsən"
}

# Mapping of Universities to Parent Administrative Districts
UNIVERSITY_TO_DISTRICT: Dict[str, str] = {
    "Bakı Dövlət Universiteti": "Yasamal",
    "Azərbaycan Dövlət Neft və Sənaye Universiteti": "Nəsimi",
    "Azərbaycan Tibb Universiteti": "Nəsimi",
    "ADA Universiteti": "Nərimanov",
    "Azərbaycan Texniki Universiteti": "Yasamal",
    "Azərbaycan Memarlıq və İnşaat Universiteti": "Yasamal",
    "Azərbaycan Dövlət İqtisad Universiteti": "Səbail",
    "Azərbaycan Dövlət Pedaqoji Universiteti": "Səbail",
    "Azərbaycan Dillər Universiteti": "Nəsimi",
    "Bakı Slavyan Universiteti": "Nəsimi",
    "Milli Aviasiya Akademiyası": "Xəzər",
    "Bakı Mühəndislik Universiteti": "Abşeron",
    "Xəzər Universiteti": "Nizami",
    "Bakı Ali Neft Məktəbi": "Səbail",
    "Dövlət İdarəçilik Akademiyası": "Səbail",
    "Bakı Musiqi Akademiyası": "Nəsimi",
    "Azərbaycan Dövlət Mədəniyyət və İncəsənət Universiteti": "Yasamal",
    "Azərbaycan Dövlət Rəssamlıq Akademiyası": "Nərimanov",
    "Azərbaycan Dövlət Bədən Tərbiyəsi və İdman Akademiyası": "Nərimanov",
    "Dövlət Gömrük Komitəsinin Akademiyası": "Abşeron",
    "Bakı Avrasiya Universiteti": "Nərimanov",
    "Azərbaycan Universiteti": "Nəsimi",
    "Qərbi Kaspi Universiteti": "Səbail",
    "Odlar Yurdu Universiteti": "Nərimanov",
    "Bakı Qızlar Universiteti": "Yasamal",
    "Azərbaycan Kooperasiya Universiteti": "Nərimanov",
    "Fransız-Azərbaycan Universiteti": "Nəsimi",
    "MDU Bakı filialı": "Binəqədi",
    "Seçenov adına MDMU": "Yasamal"
}

# Mapping of Schools to Nearest Metro Station
SCHOOL_TO_METRO: Dict[str, str] = {
    "Bakı Avropa Liseyi": "Elmlər Akademiyası",
    "Akademik Zərifə Əliyeva adına Lisey": "Elmlər Akademiyası",
    "Dünya Məktəbi": "Gənclik",
    "Fizika Riyaziyyat Liseyi": "Elmlər Akademiyası",
    "Bülbül adına Musiqi Məktəbi": "Sahil",
    "Tərəqqi Liseyi": "Nəriman Nərimanov",
    "Elitar Gimnaziya": "28 May",
    "Dəmir Yolu Liseyi": "28 May",
    "Respublika İncəsənət Gimnaziyası": "20 Yanvar",
    "Hədəf Liseyi": "Azadlıq prospekti",
    "The International School of Azerbaijan": "Dərnəgül",
    "Baku International School": "Dərnəgül",
    "Müasir Təhsil Kompleksi": "Nəriman Nərimanov",
    "23 nömrəli məktəb": "Sahil",
    "6 nömrəli məktəb": "İçərişəhər",
    "160 nömrəli klassik gimnaziya": "28 May",
    "134 nömrəli məktəb": "İçərişəhər",
    "189-190 nömrəli məktəb": "Sahil",
    "20 nömrəli məktəb": "Elmlər Akademiyası",
    "46 nömrəli məktəb": "28 May",
    "8 nömrəli məktəb": "28 May",
    "200 nömrəli məktəb": "Nəriman Nərimanov",
    "177 nömrəli məktəb": "Nəriman Nərimanov",
    "258 nömrəli məktəb": "Gənclik",
    "244 nömrəli məktəb": "Azadlıq prospekti",
    "83 nömrəli məktəb": "Azadlıq prospekti",
    "115 nömrəli məktəb": "Dərnəgül",
    "247 nömrəli məktəb": "Memar Əcəmi",
    "95 nömrəli məktəb": "Əhmədli",
    "27 nömrəli məktəb": "Xətai",
    "257 nömrəli məktəb": "Həzi Aslanov",
    "251 nömrəli məktəb": "Qara Qarayev",
    "214 nömrəli məktəb": "Neftçilər",
    "220 nömrəli məktəb": "Neftçilər",
    "272 nömrəli məktəb": "Xalqlar Dostluğu",
    "53 nömrəli məktəb": "Elmlər Akademiyası",
    "158 nömrəli məktəb": "İnşaatçılar"
}

# Mapping of Schools to Parent Administrative Districts
SCHOOL_TO_DISTRICT: Dict[str, str] = {
    "Bakı Oksford Məktəbi": "Səbail",
    "Bakı Avropa Liseyi": "Yasamal",
    "Akademik Zərifə Əliyeva adına Lisey": "Yasamal",
    "Landau School": "Səbail",
    "Baku British School": "Nəsimi",
    "European Azerbaijan School": "Yasamal",
    "The International School of Azerbaijan": "Binəqədi",
    "Baku International School": "Binəqədi",
    "Müasir Təhsil Kompleksi": "Nərimanov",
    "Dünya Məktəbi": "Nərimanov",
    "Kaspi Liseyi": "Xətai",
    "Hədəf Liseyi": "Binəqədi",
    "Fizika Riyaziyyat Liseyi": "Yasamal",
    "Bülbül adına Musiqi Məktəbi": "Səbail",
    "Tərəqqi Liseyi": "Nərimanov",
    "Elitar Gimnaziya": "Nəsimi",
    "Dəmir Yolu Liseyi": "Nəsimi",
    "Respublika İncəsənət Gimnaziyası": "Yasamal",
    "Bakı Fransız Liseyi": "Xətai",
    "23 nömrəli məktəb": "Səbail",
    "6 nömrəli məktəb": "Səbail",
    "160 nömrəli klassik gimnaziya": "Səbail",
    "134 nömrəli məktəb": "Səbail",
    "189-190 nömrəli məktəb": "Səbail",
    "20 nömrəli məktəb": "Yasamal",
    "46 nömrəli məktəb": "Nəsimi",
    "8 nömrəli məktəb": "Nəsimi",
    "200 nömrəli məktəb": "Nərimanov",
    "177 nömrəli məktəb": "Nərimanov",
    "258 nömrəli məktəb": "Nərimanov",
    "244 nömrəli məktəb": "Binəqədi",
    "83 nömrəli məktəb": "Binəqədi",
    "115 nömrəli məktəb": "Binəqədi",
    "247 nömrəli məktəb": "Nəsimi",
    "95 nömrəli məktəb": "Xətai",
    "27 nömrəli məktəb": "Xətai",
    "257 nömrəli məktəb": "Xətai",
    "251 nömrəli məktəb": "Nizami",
    "214 nömrəli məktəb": "Nizami",
    "220 nömrəli məktəb": "Nizami",
    "272 nömrəli məktəb": "Nizami",
    "53 nömrəli məktəb": "Yasamal",
    "158 nömrəli məktəb": "Yasamal",
    "286 nömrəli məktəb": "Yasamal"
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

def normalize_az_location_text(text: str) -> str:
    if not text:
        return ""
    return text.replace('İ', 'i').replace('I', 'ı').lower()

def extract_metro_station(text: str) -> Optional[str]:
    """Extract Baku Metro station name from text input if present."""
    stations = extract_all_metro_stations(text)
    return stations[0] if stations else None

def extract_all_metro_stations(text: str) -> List[str]:
    """Extract all Baku Metro station names mentioned in text in order of appearance."""
    if not text:
        return []
    text_lower = normalize_az_location_text(text)
    found = []
    # Sort by position in text if multiple
    for station_name, aliases in BAKU_METRO_STATIONS.items():
        for alias in aliases:
            if len(alias) <= 4:
                pattern = r'(?<![a-zəıöğşçü0-9])' + re.escape(alias) + r'(?![a-zəıöğşçü0-9])'
            else:
                pattern = r'(?<![a-zəıöğşçü0-9])' + re.escape(alias)
            m = re.search(pattern, text_lower)
            if m:
                if station_name not in [item[1] for item in found]:
                    found.append((m.start(), station_name))
                break

    # Fallback resolution from university and school landmarks
    if not found:
        for u_name in extract_all_baku_universities(text):
            if u_name in UNIVERSITY_TO_METRO:
                m_target = UNIVERSITY_TO_METRO[u_name]
                if m_target not in [item[1] for item in found]:
                    found.append((999, m_target))
        for sc_name in extract_all_baku_schools(text):
            if sc_name in SCHOOL_TO_METRO:
                m_target = SCHOOL_TO_METRO[sc_name]
                if m_target not in [item[1] for item in found]:
                    found.append((999, m_target))

    found.sort(key=lambda x: x[0])
    return [name for _, name in found]

# Mapping of Settlements/Quarters to Parent Baku Administrative Districts
SETTLEMENT_TO_DISTRICT: Dict[str, str] = {
    "Badamdar": "Səbail", "Bayıl": "Səbail", "Şıxov": "Səbail", "Nizami küçəsi": "Səbail", "Torqovaya": "Səbail",
    "Bakıxanov": "Sabunçu", "Zabrat": "Sabunçu", "Maştağa": "Sabunçu", "Nardaran": "Sabunçu", "Bilgəh": "Sabunçu", "Pirşağı": "Sabunçu", "Kürdəxanı": "Sabunçu", "Balaxanı": "Sabunçu", "Ramana": "Sabunçu",
    "Qaraçuxur": "Suraxanı", "Yeni Günəşli": "Suraxanı", "Köhnə Günəşli": "Suraxanı", "Hövsan": "Suraxanı", "Əmircan": "Suraxanı", "Bülbülə": "Suraxanı", "Zığ": "Suraxanı",
    "Biləcəri": "Binəqədi", "Sulutəpə": "Binəqədi", "Rəsulzadə": "Binəqədi", "6-cı mikrorayon": "Binəqədi", "7-ci mikrorayon": "Binəqədi", "8-ci mikrorayon": "Binəqədi", "9-cu mikrorayon": "Binəqədi", "Binəqədi qəs.": "Binəqədi",
    "1-ci mikrorayon": "Nəsimi", "2-ci mikrorayon": "Nəsimi", "3-cü mikrorayon": "Nəsimi", "4-cü mikrorayon": "Nəsimi", "5-ci mikrorayon": "Nəsimi", "Papanin": "Nəsimi", "Kubinka": "Nəsimi",
    "Mərdəkan": "Xəzər", "Şüvəlan": "Xəzər", "Buzovna": "Xəzər", "Binə": "Xəzər", "Qala": "Xəzər", "Zirə": "Xəzər", "Türkan": "Xəzər", "Şaqan": "Xəzər", "Albalılıq": "Xəzər", "Zuğulba": "Xəzər", "Dübəndi": "Xəzər",
    "Xırdalan": "Abşeron", "Masazır": "Abşeron", "Saray": "Abşeron", "Novxanı": "Abşeron", "Mehdiabad": "Abşeron", "Fatmayı": "Abşeron", "Digah": "Abşeron", "Məmmədli": "Abşeron", "Qobu": "Abşeron", "Hökməli": "Abşeron", "Pirəkəşkül": "Abşeron",
    "Ağ Şəhər": "Xətai", "Əhmədli": "Xətai", "Həzi Aslanov": "Xətai", "NZS": "Xətai",
    "Montin": "Nərimanov", "Böyükşor": "Nərimanov",
    "Yeni Yasamal": "Yasamal",
    "Lökbatan": "Qaradağ", "Sahil": "Qaradağ", "Sahil qəs.": "Qaradağ", "Sahil qəsəbəsi": "Qaradağ", "Qobustan": "Qaradağ", "Səngəçal": "Qaradağ",
    "Pirallahi": "Pirallahi", "Gürgən": "Pirallahi"
}

# Mapping of Baku Metro Stations to Parent Administrative Districts
METRO_TO_DISTRICT: Dict[str, str] = {
    "Elmlər Akademiyası": "Yasamal", "İnşaatçılar": "Yasamal", "20 Yanvar": "Yasamal",
    "28 May": "Nəsimi", "Memar Əcəmi": "Nəsimi", "Nəsimi": "Nəsimi", "8 Noyabr": "Nəsimi", "Cəfər Cabbarlı": "Nəsimi",
    "Gənclik": "Nərimanov", "Nəriman Nərimanov": "Nərimanov", "Bakmil": "Nərimanov",
    "Xətai": "Xətai", "Əhmədli": "Xətai", "Həzi Aslanov": "Xətai",
    "Qara Qarayev": "Nizami", "Neftçilər": "Nizami", "Xalqlar Dostluğu": "Nizami",
    "İçərişəhər": "Səbail", "Sahil": "Səbail",
    "Azadlıq prospekti": "Binəqədi", "Dərnəgül": "Binəqədi", "Avtovağzal": "Binəqədi", "Xocəsən": "Binəqədi",
    "Ulduz": "Nərimanov", "Koroğlu": "Nizami", "Nizami": "Yasamal"
}

# Mapping of Baku Locations to Official Bina.az URL Slugs for Targeted Ingestion
BINA_DISTRICT_SLUGS: Dict[str, str] = {
    "Nizami": "nizami-r",
    "Yasamal": "yasamal-r",
    "Nəsimi": "nasimi-r",
    "Nərimanov": "narimanov-r",
    "Xətai": "khatai-r",
    "Binəqədi": "binaqadi-r",
    "Sabunçu": "sabunchu-r",
    "Səbail": "sabayil-r",
    "Suraxanı": "surakhani-r",
    "Xəzər": "khazar-r",
    "Qaradağ": "qaradaq-r",
    "Abşeron": "absheron-r",
    "Sumqayıt": "sumqayit"
}

BINA_METRO_SLUGS: Dict[str, str] = {
    "28 May": "28-may-m",
    "Gənclik": "ganjlik-m",
    "Nəriman Nərimanov": "nariman-narimanov-m",
    "Elmlər Akademiyası": "elmlar-akademiyasi-m",
    "İnşaatçılar": "inshaatchilar-m",
    "20 Yanvar": "20-yanvar-m",
    "Memar Əcəmi": "memar-ajami-m",
    "Nəsimi": "nasimi-m",
    "Azadlıq prospekti": "azadliq-prospekti-m",
    "Dərnəgül": "dernegul-m",
    "İçərişəhər": "icherisheher-m",
    "Sahil": "sahil-m",
    "Nizami": "nizami-m",
    "Xətai": "khatai-m",
    "Qara Qarayev": "qara-qarayev-m",
    "Neftçilər": "neftchilar-m",
    "Xalqlar Dostluğu": "xalqlar-dostluqu-m",
    "Əhmədli": "ahmadli-m",
    "Həzi Aslanov": "hazi-aslanov-m",
    "Avtovağzal": "avtovagzal-m",
    "8 Noyabr": "8-noyabr-m",
    "Koroğlu": "koroglu-m",
    "Ulduz": "ulduz-m",
    "Bakmil": "bakmil-m",
    "Xocəsən": "khodjasan-m"
}

BINA_SETTLEMENT_SLUGS: Dict[str, str] = {
    "Xırdalan": "khirdalan",
    "Masazır": "masazir-q",
    "Badamdar": "badamdar-q",
    "Yeni Günəşli": "yeni-gunashli-q",
    "Bakıxanov": "bakikhanov-q",
    "Biləcəri": "bilajari-q",
    "Mərdəkan": "mardakan-q",
    "Şüvəlan": "shuvelan-q",
    "Buzovna": "buzovna-q",
    "Binə": "bina-q",
    "Qaraçuxur": "qarachukhur-q",
    "Hövsan": "hovsan-q",
    "Ağ Şəhər": "ag-sheher-q",
    "Montin": "montin-q",
    "8-ci mikrorayon": "8-ci-mikrorayon-q",
    "7-ci mikrorayon": "7-ci-mikrorayon-q",
    "9-cu mikrorayon": "9-cu-mikrorayon-q",
    "6-cı mikrorayon": "6-ci-mikrorayon-q",
    "5-ci mikrorayon": "5-ci-mikrorayon-q",
    "4-cü mikrorayon": "4-cu-mikrorayon-q",
    "3-cü mikrorayon": "3-cu-mikrorayon-q",
    "2-ci mikrorayon": "2-ci-mikrorayon-q",
    "1-ci mikrorayon": "1-ci-mikrorayon-q",
    "Yeni Yasamal": "yeni-yasamal-q",
    "Bayıl": "bayil-q",
    "Şaqan": "shaqan-q",
    "Qobu": "qobu-q",
    "Hökməli": "hokmali-q",
    "Bilgəh": "bilgah-q",
    "Nardaran": "nardaran-q",
    "Zabrat": "zabrat-q",
    "Maştağa": "mashtaga-q",
    "Pirşağı": "pirshagi-q",
    "Kürdəxanı": "kurdakhani-q",
    "Balaxanı": "balakhani-q",
    "Ramana": "ramana-q",
    "Saray": "saray-q",
    "Novxanı": "novkhani-q",
    "Mehdiabad": "mehdiabad-q"
}

def get_bina_location_slug(district: Optional[str] = None, metro: Optional[str] = None) -> List[str]:
    """Resolves specific Bina.az URL location slugs according to district, metro, and settlement criteria."""
    slugs = []
    if district:
        for p in re.split(r'[,;/|\+]', district):
            clean_p = p.strip().lower()
            if not clean_p:
                continue
            for d_name, slug in BINA_DISTRICT_SLUGS.items():
                if clean_p == d_name.lower() or clean_p in d_name.lower():
                    slugs.append(slug)
            for s_name, slug in BINA_SETTLEMENT_SLUGS.items():
                if clean_p == s_name.lower() or clean_p in s_name.lower():
                    slugs.append(slug)
    if metro:
        for p in re.split(r'[,;/|\+]', metro):
            clean_p = p.strip().lower()
            if not clean_p:
                continue
            for m_name, slug in BINA_METRO_SLUGS.items():
                if clean_p == m_name.lower() or clean_p in m_name.lower():
                    slugs.append(slug)
    return list(dict.fromkeys(slugs))

def get_all_aliases_for_location(loc_name: str, is_metro_focus: bool = False) -> List[str]:
    """
    Returns comprehensive keywords & aliases for a search location.
    If loc_name is a district, includes all metro stations, settlements, universities, schools, and micro-locations situated within that district.
    If is_metro_focus is True, prioritizes metro station keywords even if a district shares the same name (e.g. Nizami).
    """
    if not loc_name:
        return []
    
    loc_clean = loc_name.strip()
    is_district = (not is_metro_focus) and any(d_name.lower() == loc_clean.lower() for d_name in BAKU_DISTRICTS.keys())
    
    aliases = []
    if is_district:
        # Match official district keywords
        for d_name, d_aliases in BAKU_DISTRICTS.items():
            if d_name.lower() == loc_clean.lower():
                aliases.extend(d_aliases)
        
        # Add all child settlements belonging to this district
        for s_name, parent_dist in SETTLEMENT_TO_DISTRICT.items():
            if parent_dist.lower() == loc_clean.lower():
                aliases.extend(BAKU_SETTLEMENTS.get(s_name, []))
                aliases.append(s_name.lower())
                
        # Add all child metro stations belonging to this district
        for m_name, parent_dist in METRO_TO_DISTRICT.items():
            if parent_dist.lower() == loc_clean.lower():
                aliases.extend(BAKU_METRO_STATIONS.get(m_name, []))
                aliases.append(m_name.lower())

        # Add all universities located in this district
        for u_name, parent_dist in UNIVERSITY_TO_DISTRICT.items():
            if parent_dist.lower() == loc_clean.lower():
                aliases.extend(BAKU_UNIVERSITIES.get(u_name, []))
                aliases.append(u_name.lower())

        # Add all schools located in this district
        for sc_name, parent_dist in SCHOOL_TO_DISTRICT.items():
            if parent_dist.lower() == loc_clean.lower():
                aliases.extend(BAKU_SCHOOLS.get(sc_name, []))
                aliases.append(sc_name.lower())
    elif is_metro_focus:
        # Metro station focus: return only metro aliases + universities and schools near this metro
        for m_name, m_aliases in BAKU_METRO_STATIONS.items():
            if m_name.lower() == loc_clean.lower():
                aliases.extend(m_aliases)
        for u_name, m_target in UNIVERSITY_TO_METRO.items():
            if m_target.lower() == loc_clean.lower():
                aliases.extend(BAKU_UNIVERSITIES.get(u_name, []))
        for sc_name, m_target in SCHOOL_TO_METRO.items():
            if m_target.lower() == loc_clean.lower():
                aliases.extend(BAKU_SCHOOLS.get(sc_name, []))
        if not aliases:
            aliases = list(BAKU_METRO_STATIONS.get(loc_clean, []))
        if loc_clean.lower() not in ["sahil", "nizami", "xətai", "nəsimi", "ulduz", "avtovağzal"]:
            aliases.append(loc_clean.lower())
    else:
        # Non-district location (e.g. Metro station, Settlement, University, or School)
        aliases = (
            list(BAKU_SETTLEMENTS.get(loc_clean, [])) +
            list(BAKU_METRO_STATIONS.get(loc_clean, [])) +
            list(BAKU_UNIVERSITIES.get(loc_clean, [])) +
            list(BAKU_SCHOOLS.get(loc_clean, []))
        )
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
    text_lower = normalize_az_location_text(text)
    found = []
    for s_name, keywords in BAKU_SETTLEMENTS.items():
        for kw in keywords:
            if len(kw) <= 4:
                pattern = r'(?<![a-zəıöğşçü0-9])' + re.escape(kw) + r'(?![a-zəıöğşçü0-9])'
            else:
                pattern = r'(?<![a-zəıöğşçü0-9])' + re.escape(kw)
            m = re.search(pattern, text_lower)
            if m:
                if s_name not in [item[1] for item in found]:
                    found.append((m.start(), s_name))
                break
    found.sort(key=lambda x: x[0])
    return [name for _, name in found]

def extract_baku_university(text: str) -> Optional[str]:
    """Extract primary Baku university or higher education institution from text."""
    unis = extract_all_baku_universities(text)
    return unis[0] if unis else None

def extract_all_baku_universities(text: str) -> List[str]:
    """Extract all Baku universities and academies mentioned in text."""
    if not text:
        return []
    text_lower = normalize_az_location_text(text)
    found = []
    for u_name, keywords in BAKU_UNIVERSITIES.items():
        for kw in keywords:
            if len(kw) <= 4:
                pattern = r'(?<![a-zəıöğşçü0-9])' + re.escape(kw) + r'(?![a-zəıöğşçü0-9])'
            else:
                pattern = r'(?<![a-zəıöğşçü0-9])' + re.escape(kw)
            m = re.search(pattern, text_lower)
            if m:
                if u_name not in [item[1] for item in found]:
                    found.append((m.start(), u_name))
                break
    found.sort(key=lambda x: x[0])
    return [name for _, name in found]

def extract_baku_school(text: str) -> Optional[str]:
    """Extract primary Baku school, lyceum, gymnasium or international school from text."""
    schools = extract_all_baku_schools(text)
    return schools[0] if schools else None

def extract_all_baku_schools(text: str) -> List[str]:
    """Extract all Baku schools, lyceums, and gymnasiums mentioned in text."""
    if not text:
        return []
    text_lower = normalize_az_location_text(text)
    found = []
    for s_name, keywords in BAKU_SCHOOLS.items():
        for kw in keywords:
            if len(kw) <= 4:
                pattern = r'(?<![a-zəıöğşçü0-9])' + re.escape(kw) + r'(?![a-zəıöğşçü0-9])'
            else:
                pattern = r'(?<![a-zəıöğşçü0-9])' + re.escape(kw)
            m = re.search(pattern, text_lower)
            if m:
                if s_name not in [item[1] for item in found]:
                    found.append((m.start(), s_name))
                break
    found.sort(key=lambda x: x[0])
    return [name for _, name in found]

def extract_all_educational_institutions(text: str) -> List[str]:
    """Extract all educational landmarks (universities, colleges, schools, lyceums)."""
    return list(dict.fromkeys(extract_all_baku_universities(text) + extract_all_baku_schools(text)))

def extract_baku_district(text: str) -> Optional[str]:
    """Extract official Baku district name from text input. Returns None if no district found."""
    districts = extract_all_baku_districts(text)
    return districts[0] if districts else None

def extract_all_baku_districts(text: str) -> List[str]:
    """Extract all official Baku district names mentioned in text in order of appearance."""
    if not text:
        return []
    text_lower = normalize_az_location_text(text)
    found = []
    for dist_name, keywords in BAKU_DISTRICTS.items():
        for kw in keywords:
            if len(kw) <= 4:
                pattern = r'(?<![a-zəıöğşçü0-9])' + re.escape(kw) + r'(?![a-zəıöğşçü0-9])'
            else:
                pattern = r'(?<![a-zəıöğşçü0-9])' + re.escape(kw)
            m = re.search(pattern, text_lower)
            if m:
                if dist_name not in [item[1] for item in found]:
                    found.append((m.start(), dist_name))
                break

    # Check if a university or school indicates a parent district
    if not found:
        for u_name in extract_all_baku_universities(text):
            if u_name in UNIVERSITY_TO_DISTRICT:
                d_target = UNIVERSITY_TO_DISTRICT[u_name]
                if d_target not in [item[1] for item in found]:
                    found.append((999, d_target))
        for sc_name in extract_all_baku_schools(text):
            if sc_name in SCHOOL_TO_DISTRICT:
                d_target = SCHOOL_TO_DISTRICT[sc_name]
                if d_target not in [item[1] for item in found]:
                    found.append((999, d_target))

    found.sort(key=lambda x: x[0])
    return [name for _, name in found]

def extract_all_locations(text: str) -> List[str]:
    """Extract all distinct locations (settlements, metro stations, universities, schools, districts) with maximum precision."""
    settlements = extract_all_baku_settlements(text)
    metros = extract_all_metro_stations(text)
    unis = extract_all_baku_universities(text)
    schools = extract_all_baku_schools(text)
    districts = extract_all_baku_districts(text)
    return list(dict.fromkeys(unis + schools + settlements + metros + districts))

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

PORTAL_HOTLINES = {
    "+994125269494", "+994125261919", "+994125990805", "+994125990801", "+994124997700",
    "0125269494", "0125261919", "0125990805", "0125990801", "0124997700"
}

def extract_az_phone(text: str) -> Optional[tuple[str, str]]:
    """
    Extract Azerbaijani phone number from text, ignoring portal customer service hotlines.
    Returns (formatted_display, raw_digits_for_tel_url) or None.
    Example: ('+994 50 123 45 67', '+994501234567')
    """
    import re
    if not text:
        return None
    matches = re.finditer(r'(?:\+?994\s*|0)?\s*\(?\s*(50|51|55|70|77|99|12|10|60|18)\s*\)?\s*[\s.-]?\s*(\d{3})\s*[\s.-]?\s*(\d{2})\s*[\s.-]?\s*(\d{2})', text)
    for m in matches:
        prefix, p1, p2, p3 = m.group(1), m.group(2), m.group(3), m.group(4)
        formatted = f"+994 {prefix} {p1} {p2} {p3}"
        raw_digits = f"+994{prefix}{p1}{p2}{p3}"
        if raw_digits not in PORTAL_HOTLINES and f"0{prefix}{p1}{p2}{p3}" not in PORTAL_HOTLINES:
            return formatted, raw_digits
    return None
