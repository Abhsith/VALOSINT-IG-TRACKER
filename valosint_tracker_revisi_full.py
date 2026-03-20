import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from typing import Dict, Set, Tuple, Optional

try:
    from colorama import init, Fore, Style
except ImportError:
    print("Module colorama belum terinstall.")
    print("Install dulu dengan: pip install colorama")
    sys.exit(1)

init(autoreset=True)

# =========================================================
# FILE CONFIG
# =========================================================
FOLLOWERS_JSON = "followers_1.json"
FOLLOWERS_HTML = "followers_1.html"
FOLLOWING_JSON = "following.json"
FOLLOWING_HTML = "following.html"

PREVIOUS_SNAPSHOT = "snapshot_old.json"
CURRENT_SNAPSHOT = "snapshot_new.json"
RESULT_FILE = "result.txt"
PROFILE_CACHE_FILE = "profile_cache.json"
PROFILES_TO_REVIEW_FILE = "profiles_to_review.txt"
TELEGRAM_CONFIG_FILE = "telegram_config.json"

# =========================================================
# ACCOUNT INFO
# =========================================================
ACCOUNT_NAME = "Abdul Bhasit"
ACCOUNT_USERNAME = "abhsith"
ACCOUNT_PROFILE_URL = f"https://instagram.com/{ACCOUNT_USERNAME}"

# =========================================================
# TELEGRAM CONFIG
# =========================================================
ENABLE_TELEGRAM = False
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""

# =========================================================
# UI / STYLE
# =========================================================
C2 = Fore.LIGHTBLUE_EX
C3 = Fore.LIGHTMAGENTA_EX
C4 = Fore.GREEN
C5 = Fore.YELLOW
C6 = Fore.RED
CW = Fore.WHITE
DIM = Style.DIM
BR = Style.BRIGHT
RS = Style.RESET_ALL


# =========================================================
# UI HELPERS
# =========================================================
def clear():
    os.system("cls" if os.name == "nt" else "clear")


def loading(text: str = "Initializing VALOSINT", steps: int = 24, delay: float = 0.03):
    print()
    print(f"{C2}[~]{RS} {text}")
    bar_len = 28
    for i in range(steps + 1):
        filled = int((i / steps) * bar_len)
        bar = f"{C3}{'█' * filled}{DIM}{'░' * (bar_len - filled)}{RS}"
        percent = int((i / steps) * 100)
        print(f"\r{C2}[~]{RS} [{bar}] {C4}{percent:3d}%{RS}", end="", flush=True)
        time.sleep(delay)
    print("\n")


def pulse(text: str = "Loading modules", cycles: int = 2, delay: float = 0.15):
    dots = ["   ", ".  ", ".. ", "..."]
    for _ in range(cycles):
        for d in dots:
            print(f"\r{C2}[~]{RS} {text}{d}", end="", flush=True)
            time.sleep(delay)
    print("\r" + " " * 60, end="\r")


def show_logo() -> None:
    clear()
    logo = rf"""
{C2}{BR}
██╗   ██╗ █████╗ ██╗      ██████╗ ███████╗██╗███╗   ██╗████████╗
██║   ██║██╔══██╗██║     ██╔═══██╗██╔════╝██║████╗  ██║╚══██╔══╝
██║   ██║███████║██║     ██║   ██║███████╗██║██╔██╗ ██║   ██║
╚██╗ ██╔╝██╔══██║██║     ██║   ██║╚════██║██║██║╚██╗██║   ██║
 ╚████╔╝ ██║  ██║███████╗╚██████╔╝███████║██║██║ ╚████║   ██║
  ╚═══╝  ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚══════╝╚═╝╚═╝  ╚═══╝   ╚═╝
{RS}
{C3}{BR}                 Instagram OSINT Tracker • Hybrid Edition{RS}
{C2}         JSON + HTML Support • Telegram Setup • Cyber UI{RS}
"""
    print(logo)
    print(f"{C2}{'═' * 74}{RS}")
    print(f"{C4}[SYSTEM]{RS} VALOSINT initialized")
    print(f"{C4}[USER  ]{RS} @{ACCOUNT_USERNAME}")
    print(f"{C4}[TIME  ]{RS} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{C2}{'═' * 74}{RS}")


def cyber_header(title: str):
    print()
    print(f"{C3}{'┏' + '━' * 70 + '┓'}{RS}")
    print(f"{C3}┃{RS} {BR}{CW}{title.center(68)}{RS} {C3}┃{RS}")
    print(f"{C3}{'┗' + '━' * 70 + '┛'}{RS}")


def status(msg: str, level: str = "info"):
    color = C2
    icon = "[~]"
    if level == "ok":
        color, icon = C4, "[+]"
    elif level == "warn":
        color, icon = C5, "[!]"
    elif level == "err":
        color, icon = C6, "[-]"
    print(f"{color}{icon}{RS} {msg}")


# =========================================================
# GENERAL HELPERS
# =========================================================
def normalize_username(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = str(value).strip().lower()
    if value.startswith("@"):
        value = value[1:]
    return value or None


def instagram_link(username: str) -> str:
    return f"https://instagram.com/{username}"


def load_json(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"File tidak ditemukan: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON tidak valid pada file {path}: {e}")


def save_json(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =========================================================
# TELEGRAM CONFIG HELPERS
# =========================================================
def load_telegram_config():
    global ENABLE_TELEGRAM, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

    if not os.path.exists(TELEGRAM_CONFIG_FILE):
        return

    try:
        with open(TELEGRAM_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        ENABLE_TELEGRAM = data.get("enabled", False)
        TELEGRAM_BOT_TOKEN = data.get("bot_token", "")
        TELEGRAM_CHAT_ID = data.get("chat_id", "")
    except Exception as e:
        status(f"Gagal load config Telegram: {e}", "err")


def save_telegram_config():
    data = {
        "enabled": ENABLE_TELEGRAM,
        "bot_token": TELEGRAM_BOT_TOKEN,
        "chat_id": TELEGRAM_CHAT_ID,
    }

    with open(TELEGRAM_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def setup_telegram():
    cyber_header("TELEGRAM SETUP")

    global ENABLE_TELEGRAM, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

    current_status = "ON" if ENABLE_TELEGRAM else "OFF"
    print(f"Status sekarang : {current_status}")
    print(f"Bot Token       : {'SUDAH DIISI' if TELEGRAM_BOT_TOKEN else 'KOSONG'}")
    print(f"Chat ID         : {TELEGRAM_CHAT_ID if TELEGRAM_CHAT_ID else 'KOSONG'}")
    print()

    token = input("Masukkan Bot Token : ").strip()
    chat_id = input("Masukkan Chat ID   : ").strip()

    if not token or not chat_id:
        status("Bot Token dan Chat ID wajib diisi.", "err")
        return

    TELEGRAM_BOT_TOKEN = token
    TELEGRAM_CHAT_ID = chat_id
    ENABLE_TELEGRAM = True

    save_telegram_config()
    status("Telegram berhasil disimpan dan diaktifkan.", "ok")


# =========================================================
# HTML PARSER
# =========================================================
class InstagramHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.in_a_tag = False
        self.current_href = ""
        self.current_text = ""

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self.in_a_tag = True
            self.current_href = ""
            self.current_text = ""
            for attr, value in attrs:
                if attr.lower() == "href":
                    self.current_href = value or ""

    def handle_data(self, data):
        if self.in_a_tag:
            self.current_text += data

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.in_a_tag:
            self.links.append((self.current_href.strip(), self.current_text.strip()))
            self.in_a_tag = False
            self.current_href = ""
            self.current_text = ""


def extract_usernames_from_instagram_html(path: str) -> Set[str]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    parser = InstagramHTMLParser()
    parser.feed(html)

    usernames: Set[str] = set()

    for href, text in parser.links:
        candidate = None

        if href:
            match = re.search(r"instagram\.com/([A-Za-z0-9._]+)/?", href)
            if match:
                candidate = match.group(1)
            else:
                href_clean = href.strip("/")
                if href_clean and "/" not in href_clean and href_clean not in {"#", "javascript:void(0)"}:
                    candidate = href_clean

        if not candidate and text:
            text_clean = text.strip().lstrip("@")
            if re.fullmatch(r"[A-Za-z0-9._]+", text_clean):
                candidate = text_clean

        candidate = normalize_username(candidate)
        if candidate:
            usernames.add(candidate)

    regex_hits = re.findall(r"instagram\.com/([A-Za-z0-9._]+)/?", html, flags=re.IGNORECASE)
    for hit in regex_hits:
        username = normalize_username(hit)
        if username:
            usernames.add(username)

    return usernames


# =========================================================
# JSON PARSER
# =========================================================
def extract_usernames_from_any_block(data) -> Set[str]:
    usernames: Set[str] = set()

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                string_list_data = item.get("string_list_data", [])
                if isinstance(string_list_data, list):
                    for entry in string_list_data:
                        if isinstance(entry, dict):
                            username = normalize_username(entry.get("value"))
                            if username:
                                usernames.add(username)

    elif isinstance(data, dict):
        for value in data.values():
            if isinstance(value, (list, dict)):
                usernames.update(extract_usernames_from_any_block(value))

    return usernames


def extract_usernames_from_followers_json(data) -> Set[str]:
    return extract_usernames_from_any_block(data)


def extract_usernames_from_following_json(data) -> Set[str]:
    if isinstance(data, dict) and "relationships_following" in data:
        return extract_usernames_from_any_block(data["relationships_following"])
    return extract_usernames_from_any_block(data)


# =========================================================
# HYBRID FILE RESOLVER
# =========================================================
def resolve_input_files() -> Tuple[str, str, str, str]:
    followers_path = None
    followers_type = None
    following_path = None
    following_type = None

    if os.path.exists(FOLLOWERS_JSON):
        followers_path = FOLLOWERS_JSON
        followers_type = "json"
    elif os.path.exists(FOLLOWERS_HTML):
        followers_path = FOLLOWERS_HTML
        followers_type = "html"

    if os.path.exists(FOLLOWING_JSON):
        following_path = FOLLOWING_JSON
        following_type = "json"
    elif os.path.exists(FOLLOWING_HTML):
        following_path = FOLLOWING_HTML
        following_type = "html"

    if not followers_path:
        raise FileNotFoundError(f"Tidak menemukan {FOLLOWERS_JSON} atau {FOLLOWERS_HTML}")
    if not following_path:
        raise FileNotFoundError(f"Tidak menemukan {FOLLOWING_JSON} atau {FOLLOWING_HTML}")

    return followers_path, followers_type, following_path, following_type


def load_followers_data(path: str, file_type: str) -> Set[str]:
    if file_type == "json":
        data = load_json(path)
        return extract_usernames_from_followers_json(data)
    return extract_usernames_from_instagram_html(path)


def load_following_data(path: str, file_type: str) -> Set[str]:
    if file_type == "json":
        data = load_json(path)
        return extract_usernames_from_following_json(data)
    return extract_usernames_from_instagram_html(path)


# =========================================================
# SNAPSHOT / COMPARE
# =========================================================
def save_snapshot(path: str, followers: Set[str], following: Set[str]) -> None:
    data = {
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_followers": len(followers),
        "total_following": len(following),
        "followers": sorted(followers),
        "following": sorted(following),
    }
    save_json(path, data)


def load_snapshot(path: str) -> Tuple[Set[str], Set[str]]:
    data = load_json(path)
    return set(data.get("followers", [])), set(data.get("following", []))


def compare_snapshots(
    old_followers: Set[str],
    old_following: Set[str],
    new_followers: Set[str],
    new_following: Set[str],
) -> Dict[str, Set[str]]:
    return {
        "not_following_back": new_following - new_followers,
        "unfollowed_you": old_followers - new_followers,
        "new_followers_gained": new_followers - old_followers,
        "new_following_added": new_following - old_following,
        "mutuals": new_followers & new_following,
    }


# =========================================================
# PROFILE CACHE
# =========================================================
def load_profile_cache() -> Dict[str, dict]:
    if not os.path.exists(PROFILE_CACHE_FILE):
        return {}
    try:
        data = load_json(PROFILE_CACHE_FILE)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_profile_cache(cache: Dict[str, dict]) -> None:
    save_json(PROFILE_CACHE_FILE, cache)


def build_profile_stub(username: str) -> dict:
    return {
        "name": "N/A",
        "username": username,
        "followers": "N/A",
        "following": "N/A",
        "profile_url": instagram_link(username),
        "source": "FALLBACK",
        "note": "Profile info unavailable",
    }


def get_profile_info(username: str, cache: Dict[str, dict]) -> dict:
    username = normalize_username(username)
    if not username:
        return build_profile_stub("unknown")

    if username in cache:
        item = cache[username]
        return {
            "name": item.get("name", "N/A"),
            "username": username,
            "followers": item.get("followers", "N/A"),
            "following": item.get("following", "N/A"),
            "profile_url": item.get("profile_url", instagram_link(username)),
            "source": item.get("source", "MANUAL"),
            "note": item.get("note", ""),
        }

    return build_profile_stub(username)


# =========================================================
# OUTPUT
# =========================================================
def print_profile_list(title: str, usernames: Set[str], cache: Dict[str, dict], limit: Optional[int] = None) -> None:
    cyber_header(title)
    usernames_sorted = sorted(usernames)

    if not usernames_sorted:
        status("Kosong", "warn")
        return

    display = usernames_sorted if limit is None else usernames_sorted[:limit]

    for i, username in enumerate(display, start=1):
        profile = get_profile_info(username, cache)
        print(f"{C3}{i}.{RS} {BR}{profile['name']}{RS}")
        print(f"   {C2}Username {RS}: @{profile['username']}")
        print(f"   {C2}Followers{RS}: {profile['followers']}")
        print(f"   {C2}Following{RS}: {profile['following']}")
        print(f"   {C2}Link     {RS}: {profile['profile_url']}")
        print(f"   {C2}Source   {RS}: {profile['source']}")
        if profile.get("note"):
            print(f"   {C5}Note     {RS}: {profile['note']}")
        print(f"{DIM}{'-' * 68}{RS}")

    if limit is not None and len(usernames_sorted) > limit:
        status(f"... dan {len(usernames_sorted) - limit} akun lainnya", "warn")


def write_profile_section(file, title: str, usernames: Set[str], cache: Dict[str, dict]) -> None:
    usernames_sorted = sorted(usernames)
    file.write(f"\n=== {title} ({len(usernames_sorted)}) ===\n")

    if not usernames_sorted:
        file.write("- kosong -\n")
        return

    for i, username in enumerate(usernames_sorted, start=1):
        profile = get_profile_info(username, cache)
        file.write(f"\n{i}. Nama Akun  : {profile['name']}\n")
        file.write(f"   Username   : @{profile['username']}\n")
        file.write(f"   Followers  : {profile['followers']}\n")
        file.write(f"   Following  : {profile['following']}\n")
        file.write(f"   Link       : {profile['profile_url']}\n")
        file.write(f"   Source     : {profile['source']}\n")
        if profile.get("note"):
            file.write(f"   Note       : {profile['note']}\n")


def write_profiles_to_review(usernames: Set[str], cache: Dict[str, dict]) -> None:
    usernames_sorted = sorted(usernames)

    with open(PROFILES_TO_REVIEW_FILE, "w", encoding="utf-8") as f:
        f.write("VALOSINT - Profiles To Review\n")
        f.write("=" * 50 + "\n")
        f.write(f"Dibuat pada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        count = 0
        for username in usernames_sorted:
            profile = get_profile_info(username, cache)
            if profile["source"] == "FALLBACK":
                count += 1
                f.write(f"{count}. @{profile['username']} -> {profile['profile_url']}\n")

    status(f"File review dibuat: {PROFILES_TO_REVIEW_FILE}", "ok")


# =========================================================
# TELEGRAM
# =========================================================
def send_telegram_message(text: str) -> Tuple[bool, str]:
    if not ENABLE_TELEGRAM:
        return False, "Telegram nonaktif"

    if not TELEGRAM_BOT_TOKEN:
        return False, "Bot token belum diisi"

    if not TELEGRAM_CHAT_ID:
        return False, "Chat ID belum diisi"

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
    }

    encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=encoded, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8", errors="ignore")
            return True, body
    except Exception as e:
        return False, str(e)


def send_telegram_chunks(lines, header="VALOSINT REPORT", chunk_size=12):
    if not ENABLE_TELEGRAM or not lines:
        return

    current_chunk = []
    chunks = []

    for line in lines:
        current_chunk.append(line)
        if len(current_chunk) >= chunk_size:
            chunks.append(current_chunk)
            current_chunk = []

    if current_chunk:
        chunks.append(current_chunk)

    for i, chunk in enumerate(chunks, start=1):
        text = f"{header}\nPart {i}/{len(chunks)}\n\n" + "\n".join(chunk)
        ok, info = send_telegram_message(text)
        if ok:
            status(f"Telegram part {i}/{len(chunks)} terkirim", "ok")
        else:
            status(f"Telegram gagal: {info}", "err")


def build_profile_lines(title: str, usernames: Set[str], cache: Dict[str, dict]):
    lines = [f"{title} ({len(usernames)})", "-" * 40]
    usernames_sorted = sorted(usernames)

    if not usernames_sorted:
        lines.append("- kosong -")
        return lines

    for i, username in enumerate(usernames_sorted, start=1):
        profile = get_profile_info(username, cache)
        lines.append(f"{i}. Nama      : {profile['name']}")
        lines.append(f"   Username  : @{profile['username']}")
        lines.append(f"   Followers : {profile['followers']}")
        lines.append(f"   Following : {profile['following']}")
        lines.append(f"   Link      : {profile['profile_url']}")
        lines.append(f"   Source    : {profile['source']}")
        if profile.get("note"):
            lines.append(f"   Note      : {profile['note']}")
        lines.append("")

    return lines


# =========================================================
# MAIN FEATURES
# =========================================================
def create_current_snapshot() -> None:
    cyber_header("CREATE SNAPSHOT")
    pulse("Resolving input files", cycles=2)

    followers_path, followers_type, following_path, following_type = resolve_input_files()

    status(f"Followers source : {followers_path} ({followers_type.upper()})", "ok")
    status(f"Following source : {following_path} ({following_type.upper()})", "ok")

    followers = load_followers_data(followers_path, followers_type)
    following = load_following_data(following_path, following_type)

    if not followers and not following:
        status("Data followers/following kosong atau format file tidak cocok.", "err")
        return

    loading("Building snapshot", steps=24, delay=0.02)
    save_snapshot(CURRENT_SNAPSHOT, followers, following)

    status(f"Snapshot berhasil dibuat: {CURRENT_SNAPSHOT}", "ok")
    print(f"{C2}Followers   {RS}: {len(followers)}")
    print(f"{C2}Following   {RS}: {len(following)}")
    print(f"{C2}Mutuals     {RS}: {len(followers & following)}")
    print(f"{C2}Not Follow B{RS}: {len(following - followers)}")


def compare_old_and_new(send_to_telegram=False) -> None:
    cyber_header("COMPARE SNAPSHOT")

    if not os.path.exists(PREVIOUS_SNAPSHOT):
        status(f"File {PREVIOUS_SNAPSHOT} tidak ditemukan.", "err")
        status("Rename snapshot lama kamu menjadi snapshot_old.json dulu.", "warn")
        return

    if not os.path.exists(CURRENT_SNAPSHOT):
        status(f"File {CURRENT_SNAPSHOT} tidak ditemukan.", "err")
        status("Jalankan menu 'Buat snapshot baru' dulu.", "warn")
        return

    loading("Comparing datasets", steps=28, delay=0.02)

    old_followers, old_following = load_snapshot(PREVIOUS_SNAPSHOT)
    new_followers, new_following = load_snapshot(CURRENT_SNAPSHOT)
    result = compare_snapshots(old_followers, old_following, new_followers, new_following)
    cache = load_profile_cache()

    print_profile_list("ORANG YANG UNFOLLOW KAMU", result["unfollowed_you"], cache, limit=20)
    print_profile_list("KAMU FOLLOW TAPI MEREKA TIDAK FOLLOW BALIK", result["not_following_back"], cache, limit=20)
    print_profile_list("FOLLOWERS BARU", result["new_followers_gained"], cache, limit=20)
    print_profile_list("AKUN BARU YANG KAMU FOLLOW", result["new_following_added"], cache, limit=20)

    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        f.write("VALOSINT - Instagram Intelligence Tracker\n")
        f.write("=" * 60 + "\n")
        f.write(f"Dibuat pada     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Nama Akun       : {ACCOUNT_NAME}\n")
        f.write(f"Username IG     : @{ACCOUNT_USERNAME}\n")
        f.write(f"Followers       : {len(new_followers)}\n")
        f.write(f"Following       : {len(new_following)}\n")
        f.write(f"Link Instagram  : {ACCOUNT_PROFILE_URL}\n")
        f.write(f"Snapshot lama   : {PREVIOUS_SNAPSHOT}\n")
        f.write(f"Snapshot baru   : {CURRENT_SNAPSHOT}\n")

        write_profile_section(f, "ORANG YANG UNFOLLOW KAMU", result["unfollowed_you"], cache)
        write_profile_section(f, "KAMU FOLLOW TAPI MEREKA TIDAK FOLLOW BALIK", result["not_following_back"], cache)
        write_profile_section(f, "FOLLOWERS BARU", result["new_followers_gained"], cache)
        write_profile_section(f, "AKUN BARU YANG KAMU FOLLOW", result["new_following_added"], cache)

    status(f"Hasil berhasil disimpan ke: {RESULT_FILE}", "ok")

    review_targets = (
        result["unfollowed_you"]
        | result["not_following_back"]
        | result["new_followers_gained"]
        | result["new_following_added"]
    )
    write_profiles_to_review(review_targets, cache)

    if send_to_telegram:
        summary = [
            "VALOSINT REPORT",
            "",
            f"Nama Akun      : {ACCOUNT_NAME}",
            f"Username IG    : @{ACCOUNT_USERNAME}",
            f"Followers      : {len(new_followers)}",
            f"Following      : {len(new_following)}",
            f"Link Instagram : {ACCOUNT_PROFILE_URL}",
            f"Waktu Report   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"Unfollowed You : {len(result['unfollowed_you'])}",
            f"Not Follow Back: {len(result['not_following_back'])}",
            f"New Followers  : {len(result['new_followers_gained'])}",
            f"New Following  : {len(result['new_following_added'])}",
        ]
        ok, info = send_telegram_message("\n".join(summary))
        if ok:
            status("Ringkasan berhasil dikirim ke Telegram", "ok")
        else:
            status(f"Gagal kirim ringkasan Telegram: {info}", "err")

        send_telegram_chunks(
            build_profile_lines("ORANG YANG UNFOLLOW KAMU", result["unfollowed_you"], cache),
            header="VALOSINT - UNFOLLOWED YOU",
            chunk_size=12,
        )
        send_telegram_chunks(
            build_profile_lines("KAMU FOLLOW TAPI MEREKA TIDAK FOLLOW BALIK", result["not_following_back"], cache),
            header="VALOSINT - NOT FOLLOWING BACK",
            chunk_size=12,
        )


def add_or_update_profile_cache() -> None:
    cyber_header("PROFILE CACHE EDITOR")
    cache = load_profile_cache()

    username = normalize_username(input(f"{C2}Username IG{RS}: ").strip())
    if not username:
        status("Username tidak valid.", "err")
        return

    name = input(f"{C2}Nama akun{RS}: ").strip() or "N/A"
    followers = input(f"{C2}Jumlah followers{RS}: ").strip() or "N/A"
    following = input(f"{C2}Jumlah following{RS}: ").strip() or "N/A"

    cache[username] = {
        "name": name,
        "followers": followers,
        "following": following,
        "profile_url": instagram_link(username),
        "source": "MANUAL",
        "note": "",
    }

    save_profile_cache(cache)
    status(f"Profile cache untuk @{username} berhasil disimpan.", "ok")


def show_help() -> None:
    cyber_header("HELP / USAGE")
    print(f"{C2}- Support file followers_1.json atau followers_1.html{RS}")
    print(f"{C2}- Support file following.json atau following.html{RS}")
    print(f"{C2}- JSON akan diprioritaskan kalau keduanya ada{RS}")
    print(f"{C2}- Buat snapshot baru ke {CURRENT_SNAPSHOT}{RS}")
    print(f"{C2}- Rename snapshot lama ke {PREVIOUS_SNAPSHOT}{RS}")
    print(f"{C2}- Compare untuk melihat perubahan unfollow / followers{RS}")
    print(f"{C2}- Isi profile cache manual untuk akun yang ingin tampil full info{RS}")
    print(f"{C2}- Setup Telegram langsung dari menu 5{RS}")


def boot_sequence():
    show_logo()
    pulse("Loading cyber modules", cycles=2, delay=0.12)
    loading("Starting VALOSINT core", steps=18, delay=0.02)


def main() -> None:
    boot_sequence()
    load_telegram_config()

    while True:
        print()
        print(f"{C3}┌──────────────────────────────────────────────────────────────────────┐{RS}")
        print(f"{C3}│{RS} {BR}{CW}VALOSINT MAIN MENU{RS}                                               {C3}│{RS}")
        print(f"{C3}├──────────────────────────────────────────────────────────────────────┤{RS}")
        print(f"{C3}│{RS} {C4}[1]{RS} Buat snapshot baru                                                {C3}│{RS}")
        print(f"{C3}│{RS} {C4}[2]{RS} Bandingkan snapshot lama vs baru                                 {C3}│{RS}")
        print(f"{C3}│{RS} {C4}[3]{RS} Bandingkan + kirim ke Telegram                                   {C3}│{RS}")
        print(f"{C3}│{RS} {C4}[4]{RS} Tambah / update profile cache                                    {C3}│{RS}")
        print(f"{C3}│{RS} {C4}[5]{RS} Setup Telegram                                                   {C3}│{RS}")
        print(f"{C3}│{RS} {C4}[6]{RS} Bantuan                                                          {C3}│{RS}")
        print(f"{C3}│{RS} {C4}[7]{RS} Keluar                                                           {C3}│{RS}")
        print(f"{C3}└──────────────────────────────────────────────────────────────────────┘{RS}")

        choice = input(f"\n{C2}Pilih menu{RS}: ").strip()

        try:
            if choice == "1":
                create_current_snapshot()
            elif choice == "2":
                compare_old_and_new(send_to_telegram=False)
            elif choice == "3":
                compare_old_and_new(send_to_telegram=True)
            elif choice == "4":
                add_or_update_profile_cache()
            elif choice == "5":
                setup_telegram()
            elif choice == "6":
                show_help()
            elif choice == "7":
                status("Keluar dari VALOSINT Tracker.", "ok")
                break
            else:
                status("Pilihan tidak valid.", "warn")
        except Exception as e:
            status(f"Error: {e}", "err")


if __name__ == "__main__":
    main()
