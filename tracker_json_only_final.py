import json
import os
import re
import sys
import time
import shutil
from datetime import datetime
from typing import Optional, Set, Tuple, List, Dict

try:
    from colorama import init, Fore, Style
except ImportError:
    print("Module colorama belum terinstall.")
    print("Install dulu dengan: pip install colorama")
    sys.exit(1)

init(autoreset=True)

FOLLOWING_JSON = "following.json"
CURRENT_FILE = "snapshot_new.json"
BASELINE_FILE = "snapshot_old.json"

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

STEP_DELAY = 0.01
LOW_FOLLOWERS_THRESHOLD = 200


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
{RS}{MG}{BR}                 VALOSINT • JSON ONLY MODE{RS}
{BL}               followers_*.json + following.json only{RS}
""")
    print(f"{CY}{'═' * 86}{RS}")


def section(title: str):
    print()
    print(f"{MG}{'┏' + '━' * 82 + '┓'}{RS}")
    print(f"{MG}┃{RS} {BR}{WH}{title.center(80)}{RS} {MG}┃{RS}")
    print(f"{MG}{'┗' + '━' * 82 + '┛'}{RS}")


def ok(msg: str):
    print(f"{GR}[+]{RS} {msg}")


def warn(msg: str):
    print(f"{YL}[!]{RS} {msg}")


def err(msg: str):
    print(f"{RD}[-]{RS} {msg}")


def info(msg: str):
    print(f"{BL}[*]{RS} {msg}")


def scan_line(label: str, username: str, color: str):
    print(f"{color}[{now()}] [{label}] @{username}{RS}")


def normalize_username(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = str(value).strip().lower()
    if value.startswith("@"):
        value = value[1:]
    return value or None


def ig_link(username: str) -> str:
    return f"https://instagram.com/{username}"


def load_json(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"File tidak ditemukan: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_any_json_block(data) -> Set[str]:
    users: Set[str] = set()

    def from_href(href: str) -> Optional[str]:
        if not href or not isinstance(href, str):
            return None
        match = re.search(r"instagram\.com/(?:_u/)?([A-Za-z0-9._]+)/?", href, flags=re.IGNORECASE)
        if match:
            return normalize_username(match.group(1))
        return None

    def extract(item: dict):
        title = normalize_username(item.get("title"))
        if title:
            users.add(title)

        sld = item.get("string_list_data", [])
        if isinstance(sld, list):
            for entry in sld:
                if not isinstance(entry, dict):
                    continue

                value = normalize_username(entry.get("value"))
                if value:
                    users.add(value)

                href_user = from_href(entry.get("href"))
                if href_user:
                    users.add(href_user)

                entry_title = normalize_username(entry.get("title"))
                if entry_title:
                    users.add(entry_title)

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                extract(item)
                for value in item.values():
                    if isinstance(value, (list, dict)):
                        users.update(parse_any_json_block(value))
            elif isinstance(item, (list, dict)):
                users.update(parse_any_json_block(item))

    elif isinstance(data, dict):
        extract(data)
        for value in data.values():
            if isinstance(value, (list, dict)):
                users.update(parse_any_json_block(value))

    return users


def parse_json_file(path: str) -> Set[str]:
    data = load_json(path)
    if isinstance(data, dict) and "relationships_following" in data:
        return parse_any_json_block(data["relationships_following"])
    return parse_any_json_block(data)


def followers_json_files() -> List[str]:
    files = [f for f in os.listdir(".") if re.fullmatch(r"followers_\d+\.json", f)]
    files.sort(key=lambda x: int(re.search(r"(\d+)", x).group(1)))
    return files


def load_followers_json_only() -> Tuple[Set[str], str]:
    files = followers_json_files()
    if not files:
        raise FileNotFoundError("followers_*.json tidak ditemukan")

    users: Set[str] = set()
    for file in files:
        users.update(parse_json_file(file))

    return users, f"{', '.join(files)} (JSON merged)"


def load_following_json_only() -> Tuple[Set[str], str]:
    if not os.path.exists(FOLLOWING_JSON):
        raise FileNotFoundError("following.json tidak ditemukan")
    users = parse_json_file(FOLLOWING_JSON)
    return users, f"{FOLLOWING_JSON} (JSON)"


def load_current_data() -> Tuple[Set[str], Set[str], str, str]:
    followers, followers_src = load_followers_json_only()
    following, following_src = load_following_json_only()
    return followers, following, followers_src, following_src


def save_snapshot(path: str, followers: Set[str], following: Set[str]):
    save_json(path, {
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "followers": sorted(followers),
        "following": sorted(following),
    })


def load_snapshot(path: str) -> Tuple[Set[str], Set[str]]:
    data = load_json(path)
    return set(data.get("followers", [])), set(data.get("following", []))


def update_current_snapshot() -> Tuple[Set[str], Set[str]]:
    followers, following, followers_src, following_src = load_current_data()
    ok(f"Followers source : {followers_src}")
    ok(f"Following source : {following_src}")
    save_snapshot(CURRENT_FILE, followers, following)
    ok(f"Snapshot disimpan ke: {CURRENT_FILE}")
    ok(f"Followers : {len(followers)}")
    ok(f"Following : {len(following)}")
    return followers, following


def set_baseline_manual():
    if not os.path.exists(CURRENT_FILE):
        update_current_snapshot()
    shutil.copyfile(CURRENT_FILE, BASELINE_FILE)
    ok(f"Baseline diset manual -> {BASELINE_FILE}")


def compare_from_baseline() -> Optional[Dict[str, Set[str]]]:
    if not os.path.exists(BASELINE_FILE):
        warn("Baseline belum ada. Pilih menu 7 dulu buat set baseline.")
        return None
    if not os.path.exists(CURRENT_FILE):
        warn("Snapshot terbaru belum ada. Pilih menu 1 dulu.")
        return None

    old_followers, old_following = load_snapshot(BASELINE_FILE)
    new_followers, new_following = load_snapshot(CURRENT_FILE)

    return {
        "unfollowed": old_followers - new_followers,
        "new_followers": new_followers - old_followers,
        "new_following": new_following - old_following,
        "not_following_back": new_following - new_followers,
    }


def print_users(title: str, label: str, users: Set[str], color: str):
    banner()
    section(title)

    if not users:
        warn("Kosong")
        print()
        return

    info(f"Scanning {len(users)} akun...\n")
    for username in sorted(users):
        scan_line(label, username, color)
        print(f"    Link : {ig_link(username)}")
        print(f"{DIM}{'-' * 84}{RS}")
        time.sleep(STEP_DELAY)

    print()
    ok(f"Total {title.lower()} : {len(users)}")
    print()


def diagnostics():
    banner()
    section("DIAGNOSTICS JSON ONLY")

    visible = sorted(
        f for f in os.listdir(".")
        if re.fullmatch(r"followers_\d+\.json", f) or f in {FOLLOWING_JSON, CURRENT_FILE, BASELINE_FILE}
    )
    if not visible:
        warn("Belum ada file JSON yang relevan di folder ini.")
    else:
        for filename in visible:
            ok(f"Detected: {filename}")

    print()
    try:
        followers, following, followers_src, following_src = load_current_data()
        ok(f"Followers source aktif : {followers_src}")
        ok(f"Following source aktif : {following_src}")
        ok(f"Quick parse -> followers: {len(followers)} | following: {len(following)}")
        if len(followers) < LOW_FOLLOWERS_THRESHOLD:
            warn("Followers JSON kebaca kecil. Berarti data dari Instagram memang kecil / tidak lengkap.")
    except Exception as e:
        err(str(e))
    print()


def settings_menu():
    global STEP_DELAY
    banner()
    section("SETTINGS DELAY")
    print(f"Delay sekarang : {STEP_DELAY}")
    value = input("Masukkan delay baru (contoh 0.02): ").strip()
    try:
        STEP_DELAY = float(value)
        ok(f"Delay diubah jadi {STEP_DELAY}")
    except Exception:
        err("Format delay tidak valid.")


def menu():
    while True:
        banner()
        print(f"{MG}┌──────────────────────────────────────────────────────────────────────────────────────────┐{RS}")
        print(f"{MG}│{RS} {BR}{WH}VALOSINT JSON ONLY MENU{RS}                                                           {MG}│{RS}")
        print(f"{MG}├──────────────────────────────────────────────────────────────────────────────────────────┤{RS}")
        print(f"{MG}│{RS} {GR}[1]{RS} Update current snapshot JSON only                                               {MG}│{RS}")
        print(f"{MG}│{RS} {GR}[2]{RS} Yang follow saya (current followers)                                              {MG}│{RS}")
        print(f"{MG}│{RS} {GR}[3]{RS} Yang saya ikuti (current following)                                               {MG}│{RS}")
        print(f"{MG}│{RS} {GR}[4]{RS} Unfollow kamu (banding baseline)                                                 {MG}│{RS}")
        print(f"{MG}│{RS} {GR}[5]{RS} Followers baru (banding baseline)                                                {MG}│{RS}")
        print(f"{MG}│{RS} {GR}[6]{RS} Follow baru (banding baseline)                                                   {MG}│{RS}")
        print(f"{MG}│{RS} {GR}[7]{RS} Set current snapshot jadi baseline                                                {MG}│{RS}")
        print(f"{MG}│{RS} {GR}[8]{RS} Yang tidak follow balik kamu                                                      {MG}│{RS}")
        print(f"{MG}│{RS} {GR}[9]{RS} Diagnostics source + quick parse                                                  {MG}│{RS}")
        print(f"{MG}│{RS} {GR}[10]{RS} Settings delay live scan                                                         {MG}│{RS}")
        print(f"{MG}│{RS} {GR}[0]{RS} Keluar                                                                             {MG}│{RS}")
        print(f"{MG}└──────────────────────────────────────────────────────────────────────────────────────────┘{RS}")

        choice = input(f"\n{BL}Pilih menu{RS}: ").strip()

        try:
            if choice == "1":
                banner()
                section("UPDATE CURRENT SNAPSHOT JSON ONLY")
                update_current_snapshot()
                input("Enter untuk kembali ke menu...")
            elif choice == "2":
                followers, _, _, _ = load_current_data()
                print_users("YANG FOLLOW SAYA (CURRENT)", "FOLLOWER", followers, GR)
                input("Enter untuk kembali ke menu...")
            elif choice == "3":
                _, following, _, _ = load_current_data()
                print_users("YANG SAYA IKUTI (CURRENT)", "FOLLOWING", following, CY)
                input("Enter untuk kembali ke menu...")
            elif choice == "4":
                result = compare_from_baseline()
                if result is not None:
                    print_users("UNFOLLOW KAMU", "LOST", result["unfollowed"], RD)
                input("Enter untuk kembali ke menu...")
            elif choice == "5":
                result = compare_from_baseline()
                if result is not None:
                    print_users("FOLLOWERS BARU", "NEW", result["new_followers"], GR)
                input("Enter untuk kembali ke menu...")
            elif choice == "6":
                result = compare_from_baseline()
                if result is not None:
                    print_users("FOLLOW BARU", "FOLLOW", result["new_following"], CY)
                input("Enter untuk kembali ke menu...")
            elif choice == "7":
                banner()
                section("SET BASELINE MANUAL")
                set_baseline_manual()
                input("Enter untuk kembali ke menu...")
            elif choice == "8":
                result = compare_from_baseline()
                if result is not None:
                    print_users("YANG TIDAK FOLLOW BALIK KAMU", "NO-BACK", result["not_following_back"], YL)
                input("Enter untuk kembali ke menu...")
            elif choice == "9":
                diagnostics()
                input("Enter untuk kembali ke menu...")
            elif choice == "10":
                settings_menu()
                input("Enter untuk kembali ke menu...")
            elif choice == "0":
                ok("Keluar dari VALOSINT.")
                break
            else:
                warn("Pilihan tidak valid.")
                time.sleep(1)
        except KeyboardInterrupt:
            print()
            warn("Dibatalkan user.")
            time.sleep(0.8)
        except Exception as e:
            err(str(e))
            input("Enter untuk kembali ke menu...")


if __name__ == "__main__":
    menu()
