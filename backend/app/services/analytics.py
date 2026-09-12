"""访问数据解析:User-Agent 归类、Referer 来源分类、IP 归属。

PRD 模块二 F2.2(来源分析)/ F2.3(地理分布)/ F2.4(设备分析)依赖这里的规则。

刻意不引入第三方 UA / GeoIP 库:
  - UA 规则够用且零依赖,要新增识别只需往下面的规则表里加一条;
  - 地理归属需要一份 IP 库,项目内目前没有数据源,见 lookup_ip() 的说明。

所有函数都是纯函数,不碰 DB / Redis,方便单测。
"""

import ipaddress
import re
from typing import Optional
from urllib.parse import urlparse

# ---------- F2.4 设备分析 ----------

# 判定顺序很重要:爬虫 → 平板 → 手机 → 桌面。
# 例:iPad 的 UA 含 "Mobile"(老版本)也含 "iPad",必须先命中平板规则。
_BOT_RE = re.compile(
    r"bot|crawler|spider|slurp|bingpreview|headlesschrome|"
    r"python-requests|python-urllib|curl/|wget|okhttp|go-http-client|"
    r"java/|libwww-perl|scrapy|facebookexternalhit|whatsapp/",
    re.I,
)
_TABLET_RE = re.compile(r"ipad|tablet|kindle|playbook|silk|nexus 7|nexus 10|sm-t\d", re.I)
_MOBILE_RE = re.compile(
    r"mobile|iphone|ipod|windows phone|blackberry|opera mini|opera mobi|"
    r"micromessenger/.*mobile",
    re.I,
)
_ANDROID_RE = re.compile(r"android", re.I)

_DEVICE_UNKNOWN = "未知"
_DEVICE_BOT = "爬虫"
_DEVICE_TABLET = "平板"
_DEVICE_MOBILE = "手机"
_DEVICE_DESKTOP = "桌面"

# (归类结果, 正则)。顺序即优先级,先命中者胜出。
_OS_RULES = [
    ("Windows", re.compile(r"windows nt|windows phone", re.I)),
    ("HarmonyOS", re.compile(r"harmonyos|openharmony", re.I)),
    ("Android", re.compile(r"android", re.I)),
    # iOS 必须排在 macOS 之前:iPad 的 UA 同时含 "Mac OS X"
    ("iOS", re.compile(r"iphone|ipad|ipod", re.I)),
    ("macOS", re.compile(r"mac os x|macintosh", re.I)),
    ("Linux", re.compile(r"linux|x11|cros ", re.I)),
]

_BROWSER_RULES = [
    ("微信", re.compile(r"micromessenger", re.I)),
    ("QQ", re.compile(r"qqbrowser|qq/|qzone", re.I)),
    ("支付宝", re.compile(r"alipayclient", re.I)),
    ("抖音", re.compile(r"aweme|bytedance", re.I)),
    ("小红书", re.compile(r"xiaohongshu|xhs", re.I)),
    ("微博", re.compile(r"weibo", re.I)),
    ("UC", re.compile(r"ucbrowser|ucweb", re.I)),
    ("夸克", re.compile(r"quark", re.I)),
    ("Edge", re.compile(r"edg/|edge/|edgios|edga", re.I)),
    # Chrome 规则要在 Safari 之前:CriOS / Chrome 的 UA 里都带 Safari/
    ("Chrome", re.compile(r"chrome/|crios/|chromium", re.I)),
    ("Firefox", re.compile(r"firefox/|fxios/", re.I)),
    ("Opera", re.compile(r"opr/|opera", re.I)),
    ("Safari", re.compile(r"safari/", re.I)),
    ("IE", re.compile(r"msie|trident", re.I)),
]


def classify_device(ua: Optional[str]) -> str:
    """UA → 设备类型。无法识别归「未知」(PRD F2.4 规则)。"""
    if not ua or not ua.strip():
        return _DEVICE_UNKNOWN
    if _BOT_RE.search(ua):
        return _DEVICE_BOT
    if _TABLET_RE.search(ua):
        return _DEVICE_TABLET
    if _MOBILE_RE.search(ua):
        return _DEVICE_MOBILE
    # Android 平板 UA 里没有 "Mobile",按平板处理
    if _ANDROID_RE.search(ua):
        return _DEVICE_TABLET
    return _DEVICE_DESKTOP


def classify_os(ua: Optional[str]) -> str:
    """UA → 操作系统。无法识别归「其他」。"""
    if not ua or not ua.strip():
        return "未知"
    for name, pattern in _OS_RULES:
        if pattern.search(ua):
            return name
    return "其他"


def classify_browser(ua: Optional[str]) -> str:
    """UA → 浏览器 / 内置 WebView 来源。无法识别归「其他」。"""
    if not ua or not ua.strip():
        return "未知"
    if _BOT_RE.search(ua):
        return _DEVICE_BOT
    for name, pattern in _BROWSER_RULES:
        if pattern.search(ua):
            return name
    return "其他"


def parse_ua(ua: Optional[str]) -> dict:
    """一次性返回 {device, os, browser},供 breakdown 接口按维度取值。"""
    return {
        "device": classify_device(ua),
        "os": classify_os(ua),
        "browser": classify_browser(ua),
    }


# ---------- F2.2 来源分析 ----------

REFERER_DIRECT = "直接访问"
REFERER_SEARCH = "搜索引擎"
REFERER_SOCIAL = "社交媒体"
REFERER_OTHER = "其他"

# 用「域名里的品牌片段」而不是完整域名,这样 google.com.hk / google.co.jp 也能命中。
_SEARCH_TOKENS = (
    "baidu.", "google.", "bing.", "sogou.", "so.com", "sm.cn", "yandex.",
    "duckduckgo.", "ecosia.", "naver.", "yahoo.", "qihoo.", "so360", "shenma.",
)
_SOCIAL_TOKENS = (
    "weixin.", "wechat.", "qq.com", "weibo.", "zhihu.", "douyin.", "toutiao.",
    "xiaohongshu.", "xhslink.", "douban.", "bilibili.", "kuaishou.", "tieba.",
    "juejin.", "twitter.", "x.com", "t.co", "facebook.", "fb.com", "linkedin.",
    "telegram.", "t.me", "whatsapp.", "instagram.", "youtube.", "reddit.",
    "pinterest.", "tiktok.",
)


def _host_of(url: Optional[str]) -> str:
    if not url:
        return ""
    try:
        host = urlparse(url if "://" in url else f"http://{url}").hostname or ""
    except ValueError:
        return ""
    return host.lower()


def classify_referer(referer: Optional[str]) -> str:
    """Referer → 来源分类(PRD F2.2)。Referer 为空归「直接访问」。"""
    host = _host_of(referer)
    if not host:
        # 空 / 非法(如仅一个相对路径)都算直接访问
        return REFERER_DIRECT if not referer or not referer.strip() else REFERER_OTHER
    if any(tok in host for tok in _SEARCH_TOKENS):
        return REFERER_SEARCH
    if any(tok in host for tok in _SOCIAL_TOKENS):
        return REFERER_SOCIAL
    return REFERER_OTHER


# ---------- F2.3 地理分布 ----------

GEO_UNKNOWN = "未知"
GEO_INTERNAL = "内网"


def geo_available() -> bool:
    """是否有可用的 IP 地理库。

    当前项目未接入任何 IP 库(MaxMind GeoLite2 / 纯真 IP 库等),
    因此只有内网/保留地址能被识别,公网 IP 一律归「未知」。
    接库时把 lookup_ip 的实现换成真实查询即可,接口契约不变。
    """
    return False


def lookup_ip(ip: Optional[str], level: str = "country") -> str:
    """IP → 地理归属(单级)。

    没有 IP 库时:
      - 内网 / 回环 / 链路本地 / 保留地址 → 「内网」
      - 公网地址 → 「未知」
    PRD F2.3 要求「内网或未知归为未知」,这里把内网单独标出以便排查本地调试流量。
    """
    if not ip:
        return GEO_UNKNOWN
    try:
        addr = ipaddress.ip_address(ip.strip())
    except ValueError:
        return GEO_UNKNOWN
    if (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    ):
        return GEO_INTERNAL
    return GEO_UNKNOWN
