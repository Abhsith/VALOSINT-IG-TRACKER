import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from typing import Dict, Set, Tuple, Optional, List

try:
    from colorama import init, Fore, Style
except ImportError:
    print("Module colorama belum terinstall.")
    print("Install dulu dengan: pip install colorama")
    sys.exit(1)

init(autoreset=True)

FOLLOWERS_JSON = "followers_1.json"
FOLLOWERS_HTML = "followers_1.html"
FOLLOWING_JSON = "following.json"
FOLLOWING_HTML = "following.html"

PREVIOUS_SNAPSHOT = "snapshot_old.json"
CURRENT_SNAPSHOT = "snapshot_new.json"
RESULT_FILE = "result.txt"
UNFOLLOWED_FILE = "unfollowed.txt"
NOT_FOLLOW_BACK_FILE = "not_following_back.txt"
NEW_FOLLOWERS_FILE = "new_followers.txt"
NEW_FOLLOWING_FILE = "new_following.txt"
PROFILE_CACHE_FILE = "profile_cache.json"
PROFILES_TO_REVIEW_FILE = "profiles_to_review.txt"
TELEGRAM_CONFIG_FILE = "telegram_config.json"

ACCOUNT_NAME = "Abdul Bhasit"
ACCOUNT_USERNAME = "abhsith"
ACCOUNT_PROFILE_URL = f"https://instagram.com/{ACCOUNT_USERNAME}"

ENABLE_TELEGRAM = False
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""

B = Fore.LIGHTBLUE_EX
M = Fore.LIGHTMAGENTA_EX
G = Fore.GREEN
Y = Fore.YELLOW
R = Fore.RED
W = Fore.WHITE
DIM = Style.DIM
BR = Style.BRIGHT
RS = Style.RESET_ALL

STEP_DELAY = 0.06


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def status(msg: str, level: str = "info"):
    color = B
    icon = "[~]"
    if level == "ok":
        color, icon = G, "[+]"
    elif level == "warn":
        color, icon = Y, "[!]"
    elif level == "err":
        color, icon = R, "[-]"
    print(f"{color}{icon}{RS} {msg}")


def loading(text: str, steps: int = 20, delay: float = 0.02):
    print(f"\n{B}[~]{RS} {text}")
    bar_len = 28
    for i in range(steps + 1):
        filled = int((i / steps) * bar_len)
        bar = f"{M}{'█' * filled}{DIM}{'░' * (bar_len - filled)}{RS}"
        pct = int(i / steps * 100)
        print(f"\r{B}[~]{RS} [{bar}] {G}{pct:3d}%{RS}", end="", flush=True)
        time.sleep(delay)
    print("\n")


def cyber_header(title: str):
    print()
    print(f"{M}{'┏' + '━' * 74 + '┓'}{RS}")
    print(f"{M}┃{RS} {BR}{W}{title.center(72)}{RS} {M}┃{RS}")
    print(f"{M}{'┗' + '━' * 74 + '┛'}{RS}")


def show_logo():
    clear()
    print(f"""{B}{BR}
██╗   ██╗ █████╗ ██╗      ██████╗ ███████╗██╗███╗   ██╗████████╗
██║   ██║██╔══██╗██║     ██╔═══██╗██╔════╝██║████╗  ██║╚══██╔══╝
██║   ██║███████║██║     ██║   ██║███████╗██║██╔██╗ ██║   ██║
╚██╗ ██╔╝██╔══██║██║     ██║   ██║╚════██║██║██║╚██╗██║   ██║
 ╚████╔╝ ██║  ██║███████╗╚██████╔╝███████║██║██║ ╚████║   ██║
  ╚═══╝  ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚══════╝╚═╝╚═╝  ╚═══╝   ╚═╝
{RS}{M}{BR}                LIVE CHECKER MODE • JSON + HTML + TELEGRAM{RS}
{B}             LOST / NEW / NO-BACK • Real-Time Output • Result Files{RS}
""")
    print(f"{B}{'═' * 78}{RS}")
    print(f"{G}[SYSTEM]{RS} VALOSINT initialized")
    print(f"{G}[USER  ]{RS} @{ACCOUNT_USERNAME}")
    print(f"{G}[TIME  ]{RS} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{B}{'═' * 78}{RS}")


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
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_telegram_config():
    global ENABLE_TELEGRAM, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    if not os.path.exists(TELEGRAM_CONFIG_FILE):
        return
    try:
        data = load_json(TELEGRAM_CONFIG_FILE)
        ENABLE_TELEGRAM = data.get("enabled", False)
        TELEGRAM_BOT_TOKEN = data.get("bot_token", "")
        TELEGRAM_CHAT_ID = data.get("chat_id", "")
    except Exception as e:
        status(f"Gagal load config Telegram: {e}", "err")


def save_telegram_config():
    save_json(TELEGRAM_CONFIG_FILE, {
        "enabled": ENABLE_TELEGRAM,
        "bot_token": TELEGRAM_BOT_TOKEN,
        "chat_id": TELEGRAM_CHAT_ID,
    })


def setup_telegram():
    cyber_header("TELEGRAM SETUP")
    global ENABLE_TELEGRAM, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    print(f"Status sekarang : {'ON' if ENABLE_TELEGRAM else 'OFF'}")
    print(f"Bot Token       : {'SUDAH DIISI' if TELEGRAM_BOT_TOKEN else 'KOSONG'}")
    print(f"Chat ID         : {TELEGRAM_CHAT_ID if TELEGRAM_CHAT_ID else 'KOSONG'}\n")
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
            return True, response.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return False, str(e)


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


def extract_usernames_from_instagram_html(path: str) -> Set[str]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    parser = InstagramHTMLParser()
    parser.feed(html)
    usernames: Set[str] = set()

    for href, text in parser.links:
        candidate = None
        if href:
            match = re.search(r"instagram\.com/([A-Za-z0-9._]+)/?", href, flags=re.IGNORECASE)
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

    return usernames


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
            elif isinstance(item, (list, dict)):
                usernames.update(extract_usernames_from_any_block(item))

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


def resolve_input_files() -> Tuple[str, str, str, str]:
    followers_path = FOLLOWERS_JSON if os.path.exists(FOLLOWERS_JSON) else FOLLOWERS_HTML if os.path.exists(FOLLOWERS_HTML) else None
    followers_type = "json" if followers_path == FOLLOWERS_JSON else "html" if followers_path else None
    following_path = FOLLOWING_JSON if os.path.exists(FOLLOWING_JSON) else FOLLOWING_HTML if os.path.exists(FOLLOWING_HTML) else None
    following_type = "json" if following_path == FOLLOWING_JSON else "html" if following_path else None

    if not followers_path:
        raise FileNotFoundError(f"Tidak menemukan {FOLLOWERS_JSON} atau {FOLLOWERS_HTML}")
    if not following_path:
        raise FileNotFoundError(f"Tidak menemukan {FOLLOWING_JSON} atau {FOLLOWING_HTML}")
    return followers_path, followers_type, following_path, following_type


def load_followers_data(path: str, file_type: str) -> Set[str]:
    return extract_usernames_from_followers_json(load_json(path)) if file_type == "json" else extract_usernames_from_instagram_html(path)


def load_following_data(path: str, file_type: str) -> Set[str]:
    return extract_usernames_from_following_json(load_json(path)) if file_type == "json" else extract_usernames_from_instagram_html(path)


def save_snapshot(path: str, followers: Set[str], following: Set[str]) -> None:
    save_json(path, {
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_followers": len(followers),
        "total_following": len(following),
        "followers": sorted(followers),
        "following": sorted(following),
    })


def load_snapshot(path: str) -> Tuple[Set[str], Set[str]]:
    data = load_json(path)
    return set(data.get("followers", [])), set(data.get("following", []))


def compare_snapshots(old_followers: Set[str], old_following: Set[str], new_followers: Set[str], new_following: Set[str]) -> Dict[str, Set[str]]:
    return {
        "unfollowed_you": old_followers - new_followers,
        "not_following_back": new_following - new_followers,
        "new_followers_gained": new_followers - old_followers,
        "new_following_added": new_following - old_following,
        "mutuals": new_followers & new_following,
    }


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


def add_or_update_profile_cache():
    cyber_header("PROFILE CACHE EDITOR")
    cache = load_profile_cache()
    username = normalize_username(input(f"{B}Username IG{RS}: ").strip())
    if not username:
        status("Username tidak valid.", "err")
        return
    name = input(f"{B}Nama akun{RS}: ").strip() or "N/A"
    followers = input(f"{B}Jumlah followers{RS}: ").strip() or "N/A"
    following = input(f"{B}Jumlah following{RS}: ").strip() or "N/A"
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


def save_simple_list(path: str, usernames: Set[str]):
    with open(path, "w", encoding="utf-8") as f:
        if not usernames:
            f.write("- kosong -\n")
            return
        for i, username in enumerate(sorted(usernames), start=1):
            f.write(f"{i}. @{username} -> {instagram_link(username)}\n")


def save_result_files(result: Dict[str, Set[str]]):
    save_simple_list(UNFOLLOWED_FILE, result["unfollowed_you"])
    save_simple_list(NOT_FOLLOW_BACK_FILE, result["not_following_back"])
    save_simple_list(NEW_FOLLOWERS_FILE, result["new_followers_gained"])
    save_simple_list(NEW_FOLLOWING_FILE, result["new_following_added"])


def save_review_file(all_targets: Set[str], cache: Dict[str, dict]):
    with open(PROFILES_TO_REVIEW_FILE, "w", encoding="utf-8") as f:
        f.write("VALOSINT - Profiles To Review\n")
        f.write("=" * 40 + "\n")
        count = 0
        for username in sorted(all_targets):
            profile = get_profile_info(username, cache)
            if profile["source"] == "FALLBACK":
                count += 1
                f.write(f"{count}. @{profile['username']} -> {profile['profile_url']}\n")


def write_result_txt(result: Dict[str, Set[str]], cache: Dict[str, dict], followers_count: int, following_count: int):
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        f.write("VALOSINT REPORT\n")
        f.write("=" * 60 + "\n")
        f.write(f"Nama Akun       : {ACCOUNT_NAME}\n")
        f.write(f"Username IG     : @{ACCOUNT_USERNAME}\n")
        f.write(f"Followers       : {followers_count}\n")
        f.write(f"Following       : {following_count}\n")
        f.write(f"Link Instagram  : {ACCOUNT_PROFILE_URL}\n")
        f.write(f"Waktu Report    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        for title, key in [
            ("ORANG YANG UNFOLLOW KAMU", "unfollowed_you"),
            ("KAMU FOLLOW TAPI MEREKA TIDAK FOLLOW BALIK", "not_following_back"),
            ("FOLLOWERS BARU", "new_followers_gained"),
            ("AKUN BARU YANG KAMU FOLLOW", "new_following_added"),
        ]:
            data = sorted(result[key])
            f.write(f"{title} ({len(data)})\n")
            f.write("-" * 50 + "\n")
            if not data:
                f.write("- kosong -\n\n")
                continue
            for i, username in enumerate(data, start=1):
                profile = get_profile_info(username, cache)
                f.write(f"{i}. Nama      : {profile['name']}\n")
                f.write(f"   Username  : @{profile['username']}\n")
                f.write(f"   Followers : {profile['followers']}\n")
                f.write(f"   Following : {profile['following']}\n")
                f.write(f"   Link      : {profile['profile_url']}\n")
                f.write(f"   Source    : {profile['source']}\n")
                if profile.get("note"):
                    f.write(f"   Note      : {profile['note']}\n")
                f.write("\n")


def build_telegram_lines(title: str, usernames: Set[str], cache: Dict[str, dict]) -> List[str]:
    data = sorted(usernames)
    lines = [f"{title} ({len(data)})", "-" * 35]
    if not data:
        lines.append("- kosong -")
        return lines
    for i, username in enumerate(data, start=1):
        profile = get_profile_info(username, cache)
        lines.extend([
            f"{i}. Nama      : {profile['name']}",
            f"   Username  : @{profile['username']}",
            f"   Followers : {profile['followers']}",
            f"   Following : {profile['following']}",
            f"   Link      : {profile['profile_url']}",
            f"   Source    : {profile['source']}",
        ])
        if profile.get("note"):
            lines.append(f"   Note      : {profile['note']}")
        lines.append("")
    return lines


def send_telegram_chunks(lines: List[str], header: str, chunk_size: int = 14):
    if not ENABLE_TELEGRAM or not lines:
        return
    chunks, current = [], []
    for line in lines:
        current.append(line)
        if len(current) >= chunk_size:
            chunks.append(current)
            current = []
    if current:
        chunks.append(current)
    for i, chunk in enumerate(chunks, start=1):
        text = f"{header}\nPart {i}/{len(chunks)}\n\n" + "\n".join(chunk)
        ok, info = send_telegram_message(text)
        if ok:
            status(f"Telegram part {i}/{len(chunks)} terkirim", "ok")
        else:
            status(f"Telegram gagal: {info}", "err")


def process_live_section(title: str, usernames: Set[str], cache: Dict[str, dict], label: str, color: str):
    cyber_header(title)
    data = sorted(usernames)
    if not data:
        status("Kosong", "warn")
        return
    for i, username in enumerate(data, start=1):
        profile = get_profile_info(username, cache)
        print(f"{color}[{label} {i}/{len(data)}]{RS} @{profile['username']}")
        print(f"   Nama      : {profile['name']}")
        print(f"   Followers : {profile['followers']}")
        print(f"   Following : {profile['following']}")
        print(f"   Link      : {profile['profile_url']}")
        print(f"   Source    : {profile['source']}")
        if profile.get("note"):
            print(f"   Note      : {profile['note']}")
        print(f"{DIM}{'-' * 72}{RS}")
        time.sleep(STEP_DELAY)


def create_current_snapshot():
    cyber_header("CREATE SNAPSHOT")
    followers_path, followers_type, following_path, following_type = resolve_input_files()
    status(f"Followers source : {followers_path} ({followers_type.upper()})", "ok")
    status(f"Following source : {following_path} ({following_type.upper()})", "ok")

    followers = load_followers_data(followers_path, followers_type)
    following = load_following_data(following_path, following_type)

    if not followers and not following:
        status("Data followers/following kosong atau format file tidak cocok.", "err")
        return

    loading("Building snapshot", 24, 0.02)
    save_snapshot(CURRENT_SNAPSHOT, followers, following)
    status(f"Snapshot berhasil dibuat: {CURRENT_SNAPSHOT}", "ok")
    print(f"{B}Followers   {RS}: {len(followers)}")
    print(f"{B}Following   {RS}: {len(following)}")
    print(f"{B}Mutuals     {RS}: {len(followers & following)}")
    print(f"{B}Not Follow B{RS}: {len(following - followers)}")


def compare_old_and_new(send_to_telegram: bool = False):
    cyber_header("LIVE CHECKER RESULT")
    if not os.path.exists(PREVIOUS_SNAPSHOT):
        status(f"File {PREVIOUS_SNAPSHOT} tidak ditemukan.", "err")
        status("Rename snapshot lama kamu menjadi snapshot_old.json dulu.", "warn")
        return
    if not os.path.exists(CURRENT_SNAPSHOT):
        status(f"File {CURRENT_SNAPSHOT} tidak ditemukan.", "err")
        status("Jalankan menu 'Buat snapshot baru' dulu.", "warn")
        return

    loading("Comparing datasets", 28, 0.02)
    old_followers, old_following = load_snapshot(PREVIOUS_SNAPSHOT)
    new_followers, new_following = load_snapshot(CURRENT_SNAPSHOT)
    result = compare_snapshots(old_followers, old_following, new_followers, new_following)
    cache = load_profile_cache()

    process_live_section("UNFOLLOWED YOU", result["unfollowed_you"], cache, "LOST", R)
    process_live_section("NOT FOLLOWING BACK", result["not_following_back"], cache, "NO-BACK", Y)
    process_live_section("NEW FOLLOWERS", result["new_followers_gained"], cache, "NEW", G)
    process_live_section("NEW FOLLOWING", result["new_following_added"], cache, "FOLLOW", B)

    write_result_txt(result, cache, len(new_followers), len(new_following))
    save_result_files(result)
    save_review_file(result["unfollowed_you"] | result["not_following_back"] | result["new_followers_gained"] | result["new_following_added"], cache)

    status(f"Hasil berhasil disimpan ke: {RESULT_FILE}", "ok")
    status(f"List unfollowed disimpan ke: {UNFOLLOWED_FILE}", "ok")
    status(f"List not follow back disimpan ke: {NOT_FOLLOW_BACK_FILE}", "ok")
    status(f"List followers baru disimpan ke: {NEW_FOLLOWERS_FILE}", "ok")
    status(f"List following baru disimpan ke: {NEW_FOLLOWING_FILE}", "ok")
    status(f"File review dibuat: {PROFILES_TO_REVIEW_FILE}", "ok")

    if send_to_telegram:
        summary = [
            "VALOSINT REPORT", "",
            f"Nama Akun      : {ACCOUNT_NAME}",
            f"Username IG    : @{ACCOUNT_USERNAME}",
            f"Followers      : {len(new_followers)}",
            f"Following      : {len(new_following)}",
            f"Link Instagram : {ACCOUNT_PROFILE_URL}",
            f"Waktu Report   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "",
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

        send_telegram_chunks(build_telegram_lines("ORANG YANG UNFOLLOW KAMU", result["unfollowed_you"], cache), "VALOSINT - UNFOLLOWED YOU")
        send_telegram_chunks(build_telegram_lines("KAMU FOLLOW TAPI MEREKA TIDAK FOLLOW BALIK", result["not_following_back"], cache), "VALOSINT - NOT FOLLOWING BACK")
        send_telegram_chunks(build_telegram_lines("FOLLOWERS BARU", result["new_followers_gained"], cache), "VALOSINT - NEW FOLLOWERS")
        send_telegram_chunks(build_telegram_lines("AKUN BARU YANG KAMU FOLLOW", result["new_following_added"], cache), "VALOSINT - NEW FOLLOWING")


def show_help():
    cyber_header("HELP / USAGE")
    print(f"{B}- Support file followers_1.json atau followers_1.html{RS}")
    print(f"{B}- Support file following.json atau following.html{RS}")
    print(f"{B}- JSON akan diprioritaskan kalau keduanya ada{RS}")
    print(f"{B}- Menu 1 buat snapshot baru{RS}")
    print(f"{B}- Rename snapshot_new.json jadi snapshot_old.json untuk baseline awal{RS}")
    print(f"{B}- Menu 2 compare live checker di Termux{RS}")
    print(f"{B}- Menu 3 compare + kirim result ke Telegram{RS}")
    print(f"{B}- Menu 5 setup Telegram langsung dari terminal{RS}")


def main():
    show_logo()
    load_telegram_config()
    loading("Starting VALOSINT core", 18, 0.02)
    while True:
        print()
        print(f"{M}┌──────────────────────────────────────────────────────────────────────────┐{RS}")
        print(f"{M}│{RS} {BR}{W}VALOSINT MAIN MENU{RS}                                                   {M}│{RS}")
        print(f"{M}├──────────────────────────────────────────────────────────────────────────┤{RS}")
        print(f"{M}│{RS} {G}[1]{RS} Buat snapshot baru                                                    {M}│{RS}")
        print(f"{M}│{RS} {G}[2]{RS} LIVE checker result di Termux                                         {M}│{RS}")
        print(f"{M}│{RS} {G}[3]{RS} LIVE checker + kirim result ke Telegram                               {M}│{RS}")
        print(f"{M}│{RS} {G}[4]{RS} Tambah / update profile cache                                        {M}│{RS}")
        print(f"{M}│{RS} {G}[5]{RS} Setup Telegram                                                       {M}│{RS}")
        print(f"{M}│{RS} {G}[6]{RS} Bantuan                                                              {M}│{RS}")
        print(f"{M}│{RS} {G}[7]{RS} Keluar                                                               {M}│{RS}")
        print(f"{M}└──────────────────────────────────────────────────────────────────────────┘{RS}")

        choice = input(f"\n{B}Pilih menu{RS}: ").strip()
        try:
            if choice == "1":
                create_current_snapshot()
            elif choice == "2":
                compare_old_and_new(False)
            elif choice == "3":
                compare_old_and_new(True)
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
