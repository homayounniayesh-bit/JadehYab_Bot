"""دادههای استانها/شهرها/جادههای شمال ایران و منطق تطبیق متن آزاد."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Road:
    id: str
    name: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class City:
    id: str
    name: str
    roads: tuple[Road, ...] = ()
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class Province:
    id: str
    name: str
    cities: tuple[City, ...] = ()
    aliases: tuple[str, ...] = ()


def _r(rid: str, name: str, *aliases: str) -> Road:
    return Road(rid, name, aliases)


PROVINCES: tuple[Province, ...] = (
    Province(
        "gil",
        "گیلان",
        (
            City(
                "rasht",
                "رشت",
                (
                    _r("rasht-ghasemabad", "جاده رشت–قاسمآباد", "قاسم آباد"),
                    _r("rasht-manjeel", "محور رشت–منجیل", "منجیل"),
                    _r("rasht-tehran", "بزرگراه رشت–تهران"),
                    _r("rasht-azadi", "خیابان آزادی رشت", "آزادی"),
                ),
            ),
            City(
                "lahijan",
                "لاهیجان",
                (
                    _r("lahijan-roodser", "جاده لاهیجان–رودسر"),
                    _r("lahijan-amol", "جاده لاهیجان–آمل"),
                    _r("lahijan-taleghani", "خیابان طالقانی لاهیجان"),
                ),
            ),
            City(
                "anzali",
                "بندر انزلی",
                (
                    _r("anzali-rasht", "جاده بندرانزلی–رشت"),
                    _r("anzali-sahli", "خیابان ساحلی انزلی"),
                ),
                ("انزلی",),
            ),
            City(
                "astara",
                "آستارا",
                (
                    _r("astara-ardabil", "جاده آستارا–اردبیل"),
                    _r("astara-talesh", "محور آستارا–تالش"),
                    _r("astara-marzi", "خیابان مرزی آستارا"),
                ),
            ),
            City(
                "roodser",
                "رودسر",
                (
                    _r("roodser-chalus", "جاده رودسر–چالوس"),
                    _r("roodser-lahijan", "جاده رودسر–لاهیجان"),
                ),
            ),
            City(
                "manjeel",
                "منجیل",
                (
                    _r("manjeel-rasht", "محور منجیل–رشت"),
                    _r("manjeel-lowshan", "جاده منجیل–لوشان"),
                ),
            ),
            City(
                "talesh",
                "تالش",
                (
                    _r("talesh-astara", "جاده تالش–آستارا"),
                    _r("talesh-foman", "جاده تالش–فومن"),
                ),
            ),
            City(
                "foman",
                "فومن",
                (
                    _r("foman-rasht", "جاده فومن–رشت"),
                    _r("foman-masal", "جاده فومن–ماسال"),
                ),
            ),
        ),
    ),
    Province(
        "maz",
        "مازندران",
        (
            City(
                "chalus",
                "چالوس",
                (
                    _r("chalus-karaj", "محور کرج–چالوس (جاده چالوس)", "جاده چالوس", "محور کرج–چالوس", "چالوس"),
                    _r("chalus-marzanabad", "محور چالوس–مرزنآباد", "مرزن آباد"),
                    _r("chalus-kolardasht", "جاده چالوس–کلاردشت", "کلاردشت"),
                    _r("chalus-noshahr", "جاده چالوس–نوشهر"),
                ),
            ),
            City(
                "amol",
                "آمل",
                (
                    _r("amol-haraz", "محور هراز (آمل–امامزاده هاشم)", "هراز"),
                    _r("amol-sari", "جاده آمل–ساری"),
                    _r("amol-emamreza", "خیابان امام رضا آمل"),
                ),
            ),
            City(
                "sari",
                "ساری",
                (
                    _r("sari-tehran", "جاده ساری–تهران (محور هراز)"),
                    _r("sari-neka", "جاده ساری–نکا"),
                    _r("sari-ghaemshahr", "بزرگراه ساری–قائمشهر"),
                    _r("sari-farhang", "خیابان فرهنگ ساری"),
                ),
            ),
            City(
                "noshahr",
                "نوشهر",
                (
                    _r("noshahr-chalus", "جاده نوشهر–چالوس"),
                    _r("noshahr-kojoor", "جاده نوشهر–کجور"),
                ),
            ),
            City(
                "mahmoudabad",
                "محمودآباد",
                (
                    _r("mahmoudabad-noshahr", "جاده محمودآباد–نوشهر"),
                    _r("mahmoudabad-sahli", "جاده ساحلی محمودآباد"),
                ),
            ),
            City(
                "babol",
                "بابُل",
                (
                    _r("babol-amol", "جاده بابل–آمل"),
                    _r("babol-ghaemshahr", "جاده بابل–قائمشهر"),
                    _r("babol-taleghani", "خیابان طالقانی بابل"),
                ),
            ),
            City(
                "babolsar",
                "بابلسر",
                (
                    _r("babolsar-babol", "جاده بابلسر–بابل"),
                    _r("babolsar-sahli", "خیابان ساحلی بابلسر"),
                ),
            ),
            City(
                "ghaemshahr",
                "قائمشهر",
                (
                    _r("ghaemshahr-sari", "جاده قائمشهر–ساری"),
                    _r("ghaemshahr-shirgah", "جاده قائمشهر–شیرگاه"),
                ),
            ),
            City(
                "ramsar",
                "رامسر",
                (
                    _r("ramsar-tonekabon", "جاده رامسر–تنکابن"),
                    _r("ramsar-chalus", "جاده رامسر–چالوس"),
                ),
            ),
            City(
                "tonekabon",
                "تنکابن",
                (
                    _r("tonekabon-chalus", "محور تنکابن–چالوس"),
                    _r("tonekabon-ramsar", "جاده تنکابن–رامسر"),
                ),
            ),
            City(
                "behshahr",
                "بهشهر",
                (
                    _r("behshahr-sari", "جاده بهشهر–ساری"),
                    _r("behshahr-gorgan", "جاده بهشهر–گرگان"),
                ),
            ),
            City(
                "savadkuh",
                "سوادکوه",
                (
                    _r("savadkuh-firoozkooh", "جاده سوادکوه–فیروزکوه"),
                    _r("savadkuh-tunnel", "تونل سوادکوه"),
                ),
            ),
        ),
    ),
    Province(
        "gol",
        "گلستان",
        (
            City(
                "gorgan",
                "گرگان",
                (
                    _r("gorgan-mashhad", "جاده گرگان–مشهد"),
                    _r("gorgan-sari", "جاده گرگان–ساری"),
                    _r("gorgan-valiasr", "خیابان ولیعصر گرگان"),
                ),
            ),
            City(
                "gonbad",
                "گنبدکاووس",
                (
                    _r("gonbad-gorgan", "جاده گنبد–گرگان"),
                    _r("gonband-torkaman", "جاده گنبد–بندرترکمن"),
                ),
                ("گنبد کاووس", "گنبد"),
            ),
            City(
                "bandartorkaman",
                "بندرترکمن",
                (
                    _r("torkaman-gorgan", "جاده بندرترکمن–گرگان"),
                    _r("torkaman-gonbad", "جاده بندرترکمن–گنبد"),
                ),
                ("ترکمن",),
            ),
            City(
                "aliabad",
                "علیآباد کتول",
                (
                    _r("aliabad-gorgan", "جاده علیآباد–گرگان"),
                    _r("aliabad-azadshahr", "جاده علیآباد–آزادشهر"),
                ),
            ),
            City(
                "minoodasht",
                "مینودشت",
                (
                    _r("minoodasht-gonbad", "جاده مینودشت–گنبد"),
                    _r("minoodasht-kalaleh", "جاده مینودشت–کلاله"),
                ),
            ),
            City(
                "kalaleh",
                "کلاله",
                (_r("kalaleh-gonbad", "جاده کلاله–گنبد"),),
            ),
        ),
    ),
    Province(
        "sem",
        "سمنان",
        (
            City(
                "semnan",
                "سمنان",
                (
                    _r("semnan-mashhad", "جاده سمنان–مشهد"),
                    _r("semnan-tehran", "جاده سمنان–تهران"),
                    _r("semnan-emam", "خیابان امام خمینی سمنان"),
                ),
            ),
            City(
                "shahrood",
                "شاهرود",
                (
                    _r("shahrood-semnan", "جاده شاهرود–سمنان"),
                    _r("shahrood-mashhad", "جاده شاهرود–مشهد"),
                ),
            ),
            City(
                "damghan",
                "دامغان",
                (
                    _r("damghan-semnan", "جاده دامغان–سمنان"),
                    _r("damghan-shahrood", "جاده دامغان–شاهرود"),
                ),
            ),
            City(
                "garmsar",
                "گرمسار",
                (
                    _r("garmsar-tehran", "جاده گرمسار–تهران"),
                    _r("garmsar-semnan", "جاده گرمسار–سمنان"),
                ),
            ),
            City(
                "firoozkooh",
                "فیروزکوه",
                (
                    _r("firoozkooh-tehran", "محور فیروزکوه–تهران", "فیروزکوه"),
                    _r("firoozkooh-semnan", "محور فیروزکوه–سمنان"),
                ),
            ),
        ),
    ),
    Province(
        "qaz",
        "قزوین",
        (
            City(
                "qazvin",
                "قزوین",
                (
                    _r("qazvin-rasht", "محور قزوین–رشت"),
                    _r("qazvin-tehran", "جاده قزوین–تهران"),
                    _r("qazvin-emam", "خیابان امام خمینی قزوین"),
                ),
            ),
            City(
                "takestan",
                "تاکستان",
                (
                    _r("takestan-qazvin", "جاده تاکستان–قزوین"),
                    _r("takestan-buyin", "جاده تاکستان–بوئینزهرا"),
                ),
            ),
            City(
                "abik",
                "آبیک",
                (
                    _r("abik-qazvin", "جاده آبیک–قزوین"),
                    _r("abik-tehran", "جاده آبیک–تهران"),
                ),
            ),
            City(
                "buyinzahra",
                "بوئینزهرا",
                (_r("buyinzahra-qazvin", "جاده بوئینزهرا–قزوین"),),
            ),
        ),
    ),
    Province(
        "alb",
        "البرز",
        (
            City(
                "karaj",
                "کرج",
                (
                    _r("karaj-chalus", "محور کرج–چالوس", "جاده چالوس"),
                    _r("karaj-tehran", "بزرگراه کرج–تهران"),
                    _r("karaj-azadi", "خیابان آزادی کرج"),
                    _r("karaj-eshtehard", "جاده کرج–اشتهارد"),
                ),
            ),
            City(
                "fardis",
                "فردیس",
                (
                    _r("fardis-karaj", "جاده فردیس–کرج"),
                    _r("fardis-mahdasht", "خیابان مهدشت فردیس"),
                ),
            ),
            City(
                "hashtgerd",
                "هشتگرد",
                (
                    _r("hashtgerd-karaj", "جاده هشتگرد–کرج"),
                    _r("hashtgerd-qazvin", "جاده هشتگرد–قزوین"),
                ),
            ),
            City(
                "savojbolagh",
                "ساوجبلاغ",
                (_r("savojbolagh-karaj", "جاده ساوجبلاغ–کرج"),),
            ),
            City(
                "eshtehard",
                "اشتهارد",
                (
                    _r("eshtehard-karaj", "جاده اشتهارد–کرج"),
                    _r("eshtehard-buyin", "جاده اشتهارد–بوئینزهرا"),
                ),
            ),
        ),
    ),
    Province(
        "teh",
        "تهران",
        (
            City(
                "tehran",
                "تهران",
                (
                    _r("tehran-karaj", "بزرگراه تهران–کرج"),
                    _r("tehran-damavand", "جاده تهران–دماوند"),
                    _r("tehran-firoozkooh", "جاده تهران–فیروزکوه"),
                    _r("tehran-valiasr", "خیابان ولیعصر تهران"),
                ),
            ),
            City(
                "shemiranat",
                "شمیرانات",
                (
                    _r("loavasan", "جاده لواسان"),
                    _r("fasham-migoon", "جاده فشم–میگون"),
                    _r("roodbare", "جاده رودبارک"),
                ),
            ),
            City(
                "damavand",
                "دماوند",
                (
                    _r("damavand-tehran", "جاده دماوند–تهران"),
                    _r("damavand-firoozkooh", "جاده دماوند–فیروزکوه"),
                ),
            ),
            City(
                "rey",
                "ری",
                (
                    _r("rey-qom", "جاده ری–قم"),
                    _r("rey-tehran", "جاده ری–تهران"),
                ),
            ),
        ),
    ),
    Province(
        "ard",
        "اردبیل",
        (
            City(
                "ardabil",
                "اردبیل",
                (
                    _r("ardabil-sareyn", "جاده اردبیل–سرعین"),
                    _r("ardabil-meshgin", "جاده اردبیل–مشگینشهر"),
                    _r("ardabil-emam", "خیابان امام خمینی اردبیل"),
                ),
            ),
            City(
                "meshginshahr",
                "مشگینشهر",
                (
                    _r("meshgin-ardabil", "جاده مشگینشهر–اردبیل"),
                    _r("meshgin-kalkhal", "جاده مشگینشهر–خلخال", "خلخال"),
                ),
            ),
            City(
                "kalkhal",
                "خلخال",
                (
                    _r("kalkhal-ardabil", "جاده خلخال–اردبیل"),
                    _r("kalkhal-zanjan", "جاده خلخال–زنجان"),
                ),
            ),
            City(
                "parsabad",
                "پارسآباد",
                (
                    _r("parsabad-ardabil", "جاده پارسآباد–اردبیل"),
                    _r("parsabad-bilehsavar", "جاده پارسآباد–بیلهسوار"),
                ),
            ),
            City(
                "sareyn",
                "سرعین",
                (_r("sareyn-ardabil", "جاده سرعین–اردبیل"),),
            ),
        ),
    ),
)


PROVINCE_BY_ID = {p.id: p for p in PROVINCES}
CITY_BY_ID = {c.id: c for p in PROVINCES for c in p.cities}
ROAD_BY_ID = {r.id: r for p in PROVINCES for c in p.cities for r in c.roads}


@dataclass
class Location:
    province: str | None = None
    city: str | None = None
    road: str | None = None
    free_query: str | None = None

    @property
    def target(self) -> str:
        return self.free_query or self.road or self.city or self.province or "جاده"

    @property
    def breadcrumb(self) -> str:
        parts = [p for p in (self.road, self.city, self.province) if p]
        return "، ".join(parts) if parts else self.target


_PREFIX_RE = re.compile(r"^(استان|شهرستان|شهر|جاده|محور|خیابان|خيابان|بلوار|بزرگراه)\s+")


def norm(value: str) -> str:
    """یکدستسازی متن فارسی برای تطبیق."""
    value = (value or "").strip().lower()
    value = value.replace("ی", "ي").replace("ک", "ك").replace("آ", "ا")
    value = value.replace("ـ", "")
    value = value.replace("â", "a")
    value = _PREFIX_RE.sub("", value)
    value = re.sub(r"[\s\u200c\u200d]+", " ", value)
    value = re.sub(r"[()\[\]،,.;:!؟?\-–_/\\]+", " ", value)
    return value.strip()


def _match(value: str, candidates: Iterable[str]) -> bool:
    v = norm(value)
    if not v:
        return False
    words = v.split()
    # عبارتهای طولانیتر از ۴ کلمه احتمالاً یک جستجوی آزادند، نه نام مکان
    if len(words) > 4 or len(v) > 38:
        return False
    for candidate in candidates:
        c = norm(candidate)
        if not c:
            continue
        if v == c or c == v:
            return True
        # تطبیق تقریبی فقط برای تککلمهها؛ جملات چندکلمهای نباید به نامها بچسبند
        if len(words) == 1 and len(v) <= 26 and (v in c or c in v) and min(len(v), len(c)) >= 6:
            return True
    return False


def get_province(pid: str | None) -> Province | None:
    return PROVINCE_BY_ID.get(pid or "")


def get_city(pid: str | None, cid: str | None) -> City | None:
    province = get_province(pid)
    if not province:
        return None
    return next((c for c in province.cities if c.id == cid), None)


def get_road(pid: str | None, cid: str | None, rid: str | None) -> Road | None:
    city = get_city(pid, cid)
    if not city:
        return None
    return next((r for r in city.roads if r.id == rid), None)


def find_province(text: str) -> Province | None:
    for p in PROVINCES:
        if _match(text, (p.name, *p.aliases)):
            return p
    return None


def find_city(text: str, province_name: str | None = None) -> City | None:
    provinces = [p for p in PROVINCES if not province_name or p.name == province_name]
    if not provinces:
        provinces = list(PROVINCES)
    for p in provinces:
        for c in p.cities:
            if _match(text, (c.name, *c.aliases)):
                return c
    return None


def find_road(
    text: str, province_name: str | None = None, city_name: str | None = None
) -> Road | None:
    provinces = [p for p in PROVINCES if not province_name or p.name == province_name]
    if not provinces:
        provinces = list(PROVINCES)
    for p in provinces:
        for c in p.cities:
            if city_name and c.name != city_name:
                continue
            for r in c.roads:
                if _match(text, (r.name, *r.aliases)):
                    return r
    return None


_SPLIT_RE = re.compile(r"[\/|،,؛;]+")
_ROAD_PREFIX_RE = re.compile(r"^(جاده|محور|خیابان|خيابان|بلوار|بزرگراه)\s+")


def _assign_chunk(chunk: str, loc: Location) -> bool:
    """یک قطعه متن را به استان/شهر/جاده موجود تطبیق میدهد."""
    chunk = chunk.strip()
    if not chunk:
        return False
    if _ROAD_PREFIX_RE.match(chunk):
        if road := find_road(chunk, loc.province, loc.city):
            loc.road = road.name
            return True
    if province := find_province(chunk):
        loc.province, loc.city, loc.road = province.name, None, None
        return True
    if city := (find_city(chunk, loc.province) or find_city(chunk)):
        loc.city, loc.road = city.name, None
        return True
    if road := find_road(chunk, loc.province, loc.city):
        loc.road = road.name
        return True
    return False


def _assign_custom(chunk: str, loc: Location) -> None:
    """نام کوتاه ناشناخته را بهعنوان نام سفارشی ذخیره میکند."""
    if len(chunk) > 40 or len(chunk.split()) > 3:
        return
    if loc.road is None and loc.city:
        loc.road = chunk
    elif loc.city is None and loc.province:
        loc.city = chunk
    elif loc.province is None:
        loc.province = chunk


def parse_location(text: str, data: dict | None = None) -> Location:
    """متن آزاد مثل «مازندران/چالوس/جاده چالوس» را به مکان تبدیل میکند."""
    data = data or {}
    loc = Location()
    if province := get_province(data.get("province_id")):
        loc.province = province.name
    if city := get_city(data.get("province_id"), data.get("city_id")):
        loc.city = city.name
    if road := get_road(data.get("province_id"), data.get("city_id"), data.get("road_id")):
        loc.road = road.name

    raw = (text or "").strip()
    if not raw:
        return loc

    # تقسیم به جملهها، سپس به کلمات؛ «مازندران چالوس جاده چالوس» هم کار میکند
    tokens: list[str] = []
    for part in _SPLIT_RE.split(raw):
        tokens.extend(part.split())

    matched_any = False
    index = 0
    while index < len(tokens):
        found = False
        for size in range(min(8, len(tokens) - index), 0, -1):
            chunk = " ".join(tokens[index : index + size])
            if _assign_chunk(chunk, loc):
                matched_any = True
                found = True
                index += size
                break
        if not found:
            break

    if not matched_any:
        if len(tokens) <= 2 and len(raw) <= 25:
            _assign_custom(raw, loc)
        if not (loc.province or loc.city or loc.road):
            loc.free_query = raw
    return loc
