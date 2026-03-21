import json
import os
import re
import sys
import time
import shutil
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

# =========================================================
# FILE CONFIG
# =========================================================
FOLLOWERS_JSON = "followers_1.json"
FOLLOWERS_HTML = "followers_1.html"
FOLLOWING_JSON = "following.json"
FOLLOWING_HTML = "following.html"

BASELINE_FILE = "snapshot_old.json"
CURRENT_FILE = "snapshot_new.json"

RESULT_FILE = "result.txt"
UNFOLLOWED_FILE = "unfollowed.txt"
NOT_FOLLOW_BACK_FILE = "not_following_back.txt"
NEW_FOLLOWERS_FILE = "new_followers.txt"
NEW_FOLLOWING_FILE = "new_following.txt"
PROFILE_CACHE_FILE = "profile_cache.json"
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
# UI
# =========================================================
CY = Fore.CYAN
BL = Fore.LIGHTBLUE_EX
MG = Fore.LIGHTMAGENTA_EX
GR = Fore.GREEN
YL = Fore.YELLOW
RD = Fore.RED
WH = Fore.WHITE
DIM = Style.DIM
BR = Style.BRIGHT
RS = Style.RESET_ALL

STEP_DELAY = 0.03


# =========================================================
# BASIC UI HELPERS
# =========================================================
def now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def banner():
    clear()
    print(f"""{CY}{BR}
██╗   ██╗ █████╗ ██╗      ██████╗ ███████╗██╗███╗   ██╗████████╗
██║   ██║██╔══██╗██║     ██╔═══██╗██╔════╝██║████╗  ██║╚══██╔══╝
██║   ██║███████║██║     ██║   ██║███████╗██║██╔██╗ ██║   ██║
╚██╗ ██╔╝██╔══██║██║     ██║   ██║╚════██║██║██║╚██╗██║   ██║
 ╚████╔╝ ██║  ██║███████╗╚██████╔╝███████║██║██║ ╚████║   ██║
  ╚═══╝  ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚══════╝╚═╝╚═╝  ╚═══╝   ╚═╝
{RS}{MG}{BR}                  VALOSINT • DEWA MODE • FULL FITUR{RS}
{BL}      LIVE CHECKER • AUTO BASELINE • RESULT FILE • TELEGRAM OPTIONAL{RS}
""")
    print(f"{CY}{'═' * 86}{RS}")
    print(f"{GR}[SYSTEM]{RS} VALOSINT initialized")
    print(f"{GR}[USER  ]{RS} @{ACCOUNT_USERNAME}")
    print(f"{GR}[TIME  ]{RS} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{CY}{'═' * 86}{RS}")


def section(title: str):
    print()
    print(f"{MG}{'┏' + '━' * 82 + '┓'}{RS}")
    print(f"{MG}┃{RS} {BR}{WH}{title.center(80)}{RS} {MG}┃{RS}")
    print(f"{MG}{'┗' + '━' * 82 + '┛'}{RS}")


def info(msg: str):
    print(f"{BL}[*]{RS} {msg}")


def ok(msg: str):
    print(f"{GR}[+]{RS} {msg}")


def warn(msg: str):
    print(f"{YL}[!]{RS} {msg}")


def err(msg: str):
    print(f"{RD}[-]{RS} {msg}")


def checker_line(label: str, value: str, color: str):
    print(f"{color}[{now()}] [{label}] {value}{RS}")


def loading(text: str, steps: int = 20, delay: float = 0.02):
    print(f"\n{BL}[*]{RS} {text}")
    bar_len = 30
    for i in range(steps + 1):
        filled = int((i / steps) * bar_len)
        bar = f"{MG}{'█' * filled}{DIM}{'░' * (bar_len - filled)}{RS}"
        pct = int(i / steps * 100)
        print(f"\r{BL}[*]{RS} [{bar}] {GR}{pct:3d}%{RS}", end="", flush=True)
        time.sleep(delay)
    print("\n")


# =========================================================
# DATA HELPERS
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
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class InstagramHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.in_a = False
        self.href = ""
        self.text = ""

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self.in_a = True
            self.href = ""
            self.text = ""
            for key, value in attrs:
                if key.lower() == "href":
                    self.href = value or ""

    def handle_data(self, data):
        if self.in_a:
            self.text += data

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.in_a:
            self.links.append((self.href.strip(), self.text.strip()))
            self.in_a = False
            self.href = ""
            self.text = ""


def parse_html(path: str) -> Set[str]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    parser = InstagramHTMLParser()
    parser.feed(html)
    users: Set[str] = set()

    for href, text in parser.links:
        candidate = None

        if href:
            match = re.search(r"instagram\.com/([A-Za-z0-9._]+)/?", href, flags=re.IGNORECASE)
            if match:
                candidate = match.group(1)

        if not candidate and text:
            t = text.strip().lstrip("@")
            if re.fullmatch(r"[A-Za-z0-9._]+", t):
                candidate = t

        candidate = normalize_username(candidate)
        if candidate:
            users.add(candidate)

    return users


def parse_any_json_block(data) -> Set[str]:
    users: Set[str] = set()

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                sld = item.get("string_list_data", [])
                if isinstance(sld, list):
                    for entry in sld:
                        if isinstance(entry, dict):
                            value = normalize_username(entry.get("value"))
                            if value:
                                users.add(value)
            elif isinstance(item, (list, dict)):
                users.update(parse_any_json_block(item))

    elif isinstance(data, dict):
        for value in data.values():
            if isinstance(value, (list, dict)):
                users.update(parse_any_json_block(value))

    return users


def parse_followers_json(path: str) -> Set[str]:
    return parse_any_json_block(load_json(path))


def parse_following_json(path: str) -> Set[str]:
    data = load_json(path)
    if isinstance(data, dict) and "relationships_following" in data:
        return parse_any_json_block(data["relationships_following"])
    return parse_any_json_block(data)


def resolve_input_files() -> Tuple[str, str, str, str]:
    followers_path = None
    following_path = None

    if os.path.exists(FOLLOWERS_JSON):
        followers_path = FOLLOWERS_JSON
    elif os.path.exists(FOLLOWERS_HTML):
        followers_path = FOLLOWERS_HTML

    if os.path.exists(FOLLOWING_JSON):
        following_path = FOLLOWING_JSON
    elif os.path.exists(FOLLOWING_HTML):
        following_path = FOLLOWING_HTML

    if not followers_path:
        raise FileNotFoundError("followers_1.json atau followers_1.html tidak ditemukan")
    if not following_path:
        raise FileNotFoundError("following.json atau following.html tidak ditemukan")

    followers_type = "JSON" if followers_path.endswith(".json") else "HTML"
    following_type = "JSON" if following_path.endswith(".json") else "HTML"
    return followers_path, followers_type, following_path, following_type


def load_current_data() -> Tuple[Set[str], Set[str]]:
    followers_path, followers_type, following_path, following_type = resolve_input_files()

    ok(f"Followers source : {followers_path} ({followers_type})")
    ok(f"Following source : {following_path} ({following_type})")

    followers = parse_followers_json(followers_path) if followers_path.endswith(".json") else parse_html(followers_path)
    following = parse_following_json(following_path) if following_path.endswith(".json") else parse_html(following_path)
    return followers, following


# =========================================================
# SNAPSHOT
# =========================================================
def save_snapshot(path: str, followers: Set[str], following: Set[str]):
    save_json(path, {
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "followers": sorted(followers),
        "following": sorted(following),
    })


def load_snapshot(path: str) -> Tuple[Set[str], Set[str]]:
    data = load_json(path)
    return set(data.get("followers", [])), set(data.get("following", []))


def auto_update_baseline():
    if os.path.exists(CURRENT_FILE):
        shutil.copyfile(CURRENT_FILE, BASELINE_FILE)
        ok(f"Auto baseline updated -> {BASELINE_FILE}")


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


def add_or_update_profile_cache():
    banner()
    section("PROFILE CACHE EDITOR")
    cache = load_profile_cache()

    username = normalize_username(input(f"{BL}Username IG{RS}: ").strip())
    if not username:
        err("Username tidak valid.")
        return

    name = input(f"{BL}Nama akun{RS}: ").strip() or "N/A"
    followers = input(f"{BL}Jumlah followers{RS}: ").strip() or "N/A"
    following = input(f"{BL}Jumlah following{RS}: ").strip() or "N/A"

    cache[username] = {
        "name": name,
        "followers": followers,
        "following": following,
        "profile_url": instagram_link(username),
        "source": "MANUAL",
        "note": "",
    }
    save_profile_cache(cache)
    ok(f"Profile cache untuk @{username} berhasil disimpan.")


# =========================================================
# RESULT FILES
# =========================================================
def save_simple_list(path: str, usernames: Set[str]):
    with open(path, "w", encoding="utf-8") as f:
        if not usernames:
            f.write("- kosong -\n")
            return
        for i, username in enumerate(sorted(usernames), start=1):
            f.write(f"{i}. @{username} -> {instagram_link(username)}\n")


def save_result_files(unfollowed: Set[str], no_back: Set[str], new_followers: Set[str], new_following: Set[str]):
    save_simple_list(UNFOLLOWED_FILE, unfollowed)
    save_simple_list(NOT_FOLLOW_BACK_FILE, no_back)
    save_simple_list(NEW_FOLLOWERS_FILE, new_followers)
    save_simple_list(NEW_FOLLOWING_FILE, new_following)


def write_result_txt(unfollowed: Set[str], no_back: Set[str], new_followers: Set[str], new_following: Set[str]):
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        f.write("VALOSINT REPORT\n")
        f.write("=" * 60 + "\n")
        f.write(f"Akun          : {ACCOUNT_NAME}\n")
        f.write(f"Username IG   : @{ACCOUNT_USERNAME}\n")
        f.write(f"Link          : {ACCOUNT_PROFILE_URL}\n")
        f.write(f"Waktu         : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        sections = [
            ("UNFOLLOWED YOU", unfollowed),
            ("NOT FOLLOWING BACK", no_back),
            ("NEW FOLLOWERS", new_followers),
            ("NEW FOLLOWING", new_following),
        ]
        for title, data in sections:
            f.write(f"{title} ({len(data)})\n")
            f.write("-" * 40 + "\n")
            if not data:
                f.write("- kosong -\n\n")
                continue
            for i, username in enumerate(sorted(data), start=1):
                f.write(f"{i}. @{username} -> {instagram_link(username)}\n")
            f.write("\n")


# =========================================================
# TELEGRAM
# =========================================================
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
        err(f"Gagal load config Telegram: {e}")


def save_telegram_config():
    save_json(TELEGRAM_CONFIG_FILE, {
        "enabled": ENABLE_TELEGRAM,
        "bot_token": TELEGRAM_BOT_TOKEN,
        "chat_id": TELEGRAM_CHAT_ID,
    })


def setup_telegram():
    banner()
    section("TELEGRAM SETUP")

    global ENABLE_TELEGRAM, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

    print(f"Status sekarang : {'ON' if ENABLE_TELEGRAM else 'OFF'}")
    print(f"Bot Token       : {'SUDAH DIISI' if TELEGRAM_BOT_TOKEN else 'KOSONG'}")
    print(f"Chat ID         : {TELEGRAM_CHAT_ID if TELEGRAM_CHAT_ID else 'KOSONG'}\n")

    token = input("Masukkan Bot Token : ").strip()
    chat_id = input("Masukkan Chat ID   : ").strip()

    if not token or not chat_id:
        err("Bot Token dan Chat ID wajib diisi.")
        return

    TELEGRAM_BOT_TOKEN = token
    TELEGRAM_CHAT_ID = chat_id
    ENABLE_TELEGRAM = True
    save_telegram_config()
    ok("Telegram berhasil disimpan dan diaktifkan.")


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


def send_telegram_block(title: str, users: Set[str]):
    if not users:
        send_telegram_message(f"{title}\n\n- kosong -")
        return

    lines = [title, ""]
    for i, username in enumerate(sorted(users), start=1):
        lines.append(f"{i}. @{username}")
    send_telegram_message("\n".join(lines))


# =========================================================
# LIVE OUTPUT
# =========================================================
def print_live_group(title: str, label: str, users: Set[str], color: str, cache: Dict[str, dict]):
    section(title)

    if not users:
        warn("Kosong")
        return

    users_sorted = sorted(users)
    info(f"Scanning {len(users_sorted)} accounts...\n")

    for username in users_sorted:
        profile = get_profile_info(username, cache)
        checker_line(label, f"@{profile['username']}", color)
        print(f"    Name      : {profile['name']}")
        print(f"    Followers : {profile['followers']}")
        print(f"    Following : {profile['following']}")
        print(f"    Link      : {profile['profile_url']}")
        print(f"    Source    : {profile['source']}")
        if profile.get("note"):
            print(f"    Note      : {profile['note']}")
        print(f"{DIM}{'-' * 80}{RS}")
        time.sleep(STEP_DELAY)


def print_summary(unfollowed: Set[str], no_back: Set[str], new_followers: Set[str], new_following: Set[str]):
    print()
    print(f"{CY}{'═' * 86}{RS}")
    ok(f"Unfollowed You : {len(unfollowed)}")
    ok(f"Not Follow Back: {len(no_back)}")
    ok(f"New Followers  : {len(new_followers)}")
    ok(f"New Following  : {len(new_following)}")
    print(f"{CY}{'═' * 86}{RS}")
    print()


# =========================================================
# MAIN MODES
# =========================================================
def create_snapshot():
    banner()
    section("CREATE SNAPSHOT")

    followers, following = load_current_data()

    loading("Building snapshot", 22, 0.02)
    save_snapshot(CURRENT_FILE, followers, following)

    ok(f"Snapshot disimpan ke: {CURRENT_FILE}")
    ok(f"Followers : {len(followers)}")
    ok(f"Following : {len(following)}")
    ok(f"Mutuals   : {len(followers & following)}")
    ok(f"No-Back   : {len(following - followers)}")

    if not os.path.exists(BASELINE_FILE):
        shutil.copyfile(CURRENT_FILE, BASELINE_FILE)
        ok(f"Baseline awal otomatis dibuat -> {BASELINE_FILE}")


def live_check(send_telegram: bool = False):
    banner()
    section("LIVE CHECK RESULT")

    if not os.path.exists(CURRENT_FILE):
        warn("Snapshot terbaru belum ada.")
        info("Jalankan menu 1 dulu.")
        return

    if not os.path.exists(BASELINE_FILE):
        warn("Baseline belum ada.")
        info("Membuat baseline otomatis dari snapshot terbaru...")
        shutil.copyfile(CURRENT_FILE, BASELINE_FILE)
        ok(f"Baseline dibuat -> {BASELINE_FILE}")
        warn("Belum ada data pembanding. Jalankan menu 1 lagi saat data berubah, lalu check lagi.")
        return

    old_followers, old_following = load_snapshot(BASELINE_FILE)
    new_followers, new_following = load_snapshot(CURRENT_FILE)

    info("Comparing baseline vs current data...")
    time.sleep(0.4)

    unfollowed = old_followers - new_followers
    no_back = new_following - new_followers
    new_followers_gained = new_followers - old_followers
    new_following_added = new_following - old_following

    cache = load_profile_cache()

    print_live_group("UNFOLLOWED YOU", "LOST", unfollowed, RD, cache)
    print_live_group("NOT FOLLOWING BACK", "NO-BACK", no_back, YL, cache)
    print_live_group("NEW FOLLOWERS", "NEW", new_followers_gained, GR, cache)
    print_live_group("NEW FOLLOWING", "FOLLOW", new_following_added, CY, cache)

    print_summary(unfollowed, no_back, new_followers_gained, new_following_added)

    write_result_txt(unfollowed, no_back, new_followers_gained, new_following_added)
    save_result_files(unfollowed, no_back, new_followers_gained, new_following_added)
    ok(f"Result file dibuat -> {RESULT_FILE}")

    if send_telegram:
        summary = "\n".join([
            "VALOSINT REPORT",
            "",
            f"Akun            : {ACCOUNT_NAME}",
            f"Username IG     : @{ACCOUNT_USERNAME}",
            f"Unfollowed You  : {len(unfollowed)}",
            f"Not Follow Back : {len(no_back)}",
            f"New Followers   : {len(new_followers_gained)}",
            f"New Following   : {len(new_following_added)}",
        ])
        ok_send, msg = send_telegram_message(summary)
        if ok_send:
            ok("Ringkasan berhasil dikirim ke Telegram.")
            send_telegram_block("UNFOLLOWED YOU", unfollowed)
            send_telegram_block("NOT FOLLOWING BACK", no_back)
            send_telegram_block("NEW FOLLOWERS", new_followers_gained)
            send_telegram_block("NEW FOLLOWING", new_following_added)
        else:
            err(f"Gagal kirim Telegram: {msg}")

    shutil.copyfile(CURRENT_FILE, BASELINE_FILE)
    ok(f"Baseline otomatis diupdate -> {BASELINE_FILE}")


def show_status():
    banner()
    section("STATUS FILE")

    for filename in [
        FOLLOWERS_JSON,
        FOLLOWERS_HTML,
        FOLLOWING_JSON,
        FOLLOWING_HTML,
        CURRENT_FILE,
        BASELINE_FILE,
        PROFILE_CACHE_FILE,
        TELEGRAM_CONFIG_FILE,
    ]:
        if os.path.exists(filename):
            ok(f"Detected: {filename}")
        else:
            warn(f"Missing : {filename}")

    print()


def settings_menu():
    global STEP_DELAY
    banner()
    section("SETTINGS")
    print(f"Delay sekarang : {STEP_DELAY} detik")
    value = input("Masukkan delay baru (contoh 0.02): ").strip()
    try:
        STEP_DELAY = float(value)
        ok(f"Delay diubah jadi {STEP_DELAY}")
    except Exception:
        err("Format delay tidak valid.")


def menu():
    load_telegram_config()
    while True:
        banner()
        print(f"{MG}┌────────────────────────────────────────────────────────────────────────────────────┐{RS}")
        print(f"{MG}│{RS} {BR}{WH}VALOSINT DEWA MENU{RS}                                                           {MG}│{RS}")
        print(f"{MG}├────────────────────────────────────────────────────────────────────────────────────┤{RS}")
        print(f"{MG}│{RS} {GR}[1]{RS} Buat / update snapshot terbaru                                                {MG}│{RS}")
        print(f"{MG}│{RS} {GR}[2]{RS} Live check transparan di Termux                                                {MG}│{RS}")
        print(f"{MG}│{RS} {GR}[3]{RS} Live check + kirim hasil ke Telegram                                            {MG}│{RS}")
        print(f"{MG}│{RS} {GR}[4]{RS} Tambah / update profile cache                                                   {MG}│{RS}")
        print(f"{MG}│{RS} {GR}[5]{RS} Setup Telegram                                                                  {MG}│{RS}")
        print(f"{MG}│{RS} {GR}[6]{RS} Lihat status file                                                              {MG}│{RS}")
        print(f"{MG}│{RS} {GR}[7]{RS} Settings delay live scan                                                       {MG}│{RS}")
        print(f"{MG}│{RS} {GR}[8]{RS} Keluar                                                                         {MG}│{RS}")
        print(f"{MG}└────────────────────────────────────────────────────────────────────────────────────┘{RS}")

        choice = input(f"\n{BL}Pilih menu{RS}: ").strip()

        try:
            if choice == "1":
                create_snapshot()
                input("Enter untuk kembali ke menu...")
            elif choice == "2":
                live_check(False)
                input("Enter untuk kembali ke menu...")
            elif choice == "3":
                live_check(True)
                input("Enter untuk kembali ke menu...")
            elif choice == "4":
                add_or_update_profile_cache()
                input("Enter untuk kembali ke menu...")
            elif choice == "5":
                setup_telegram()
                input("Enter untuk kembali ke menu...")
            elif choice == "6":
                show_status()
                input("Enter untuk kembali ke menu...")
            elif choice == "7":
                settings_menu()
                input("Enter untuk kembali ke menu...")
            elif choice == "8":
                ok("Keluar dari VALOSINT.")
                break
            else:
                warn("Pilihan tidak valid.")
                time.sleep(1)
        except Exception as e:
            err(str(e))
            input("Enter untuk kembali ke menu...")


if __name__ == "__main__":
    menu()
