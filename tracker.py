import json
import os
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Dict, Set, Tuple, Optional

FOLLOWERS_FILE = "followers_1.json"
FOLLOWING_FILE = "following.json"
PREVIOUS_SNAPSHOT = "snapshot_old.json"
CURRENT_SNAPSHOT = "snapshot_new.json"
RESULT_FILE = "result.txt"
PROFILE_CACHE_FILE = "profile_cache.json"
PROFILES_TO_REVIEW_FILE = "profiles_to_review.txt"

# =========================
# INFO AKUN KAMU
# =========================
ACCOUNT_NAME = "Abdul Bhasit"
ACCOUNT_USERNAME = "abhsith"
ACCOUNT_PROFILE_URL = f"https://instagram.com/{ACCOUNT_USERNAME}"

# =========================
# TELEGRAM CONFIG
# =========================
ENABLE_TELEGRAM = False
TELEGRAM_BOT_TOKEN = "ISI_BOT_TOKEN"
TELEGRAM_CHAT_ID = "ISI_CHAT_ID"


def show_logo() -> None:
    logo = r"""
██╗   ██╗ █████╗ ██╗      ██████╗ ███████╗██╗███╗   ██╗████████╗
██║   ██║██╔══██╗██║     ██╔═══██╗██╔════╝██║████╗  ██║╚══██╔══╝
██║   ██║███████║██║     ██║   ██║███████╗██║██╔██╗ ██║   ██║
╚██╗ ██╔╝██╔══██║██║     ██║   ██║╚════██║██║██║╚██╗██║   ██║
 ╚████╔╝ ██║  ██║███████╗╚██████╔╝███████║██║██║ ╚████║   ██║
  ╚═══╝  ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚══════╝╚═╝╚═╝  ╚═══╝   ╚═╝

        Instagram Intelligence Tracker • Telegram Edition
"""
    print(logo)


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


def extract_usernames_from_followers(data) -> Set[str]:
    return extract_usernames_from_any_block(data)


def extract_usernames_from_following(data) -> Set[str]:
    if isinstance(data, dict) and "relationships_following" in data:
        return extract_usernames_from_any_block(data["relationships_following"])
    return extract_usernames_from_any_block(data)


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


def print_profile_list(title: str, usernames: Set[str], cache: Dict[str, dict], limit: Optional[int] = None) -> None:
    usernames_sorted = sorted(usernames)
    print(f"\n=== {title} ({len(usernames_sorted)}) ===")

    if not usernames_sorted:
        print("- kosong -")
        return

    display = usernames_sorted if limit is None else usernames_sorted[:limit]

    for i, username in enumerate(display, start=1):
        profile = get_profile_info(username, cache)
        print(f"\n{i}. Nama Akun  : {profile['name']}")
        print(f"   Username   : @{profile['username']}")
        print(f"   Followers  : {profile['followers']}")
        print(f"   Following  : {profile['following']}")
        print(f"   Link       : {profile['profile_url']}")
        print(f"   Source     : {profile['source']}")
        if profile.get("note"):
            print(f"   Note       : {profile['note']}")

    if limit is not None and len(usernames_sorted) > limit:
        print(f"\n... dan {len(usernames_sorted) - limit} akun lainnya")


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

    print(f"[+] File review dibuat: {PROFILES_TO_REVIEW_FILE}")


def send_telegram_message(text: str) -> Tuple[bool, str]:
    if not ENABLE_TELEGRAM:
        return False, "Telegram nonaktif"

    if TELEGRAM_BOT_TOKEN == "ISI_BOT_TOKEN" or not TELEGRAM_BOT_TOKEN:
        return False, "Bot token belum diisi"

    if TELEGRAM_CHAT_ID == "ISI_CHAT_ID" or not TELEGRAM_CHAT_ID:
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


def send_telegram_chunks(lines, header="VALOSINT REPORT", chunk_size=10):
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
            print(f"[+] Telegram part {i}/{len(chunks)} terkirim")
        else:
            print(f"[!] Telegram gagal: {info}")


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


def create_current_snapshot() -> None:
    followers_data = load_json(FOLLOWERS_FILE)
    following_data = load_json(FOLLOWING_FILE)

    followers = extract_usernames_from_followers(followers_data)
    following = extract_usernames_from_following(following_data)

    if not followers and not following:
        print("Data followers/following kosong atau format export tidak cocok.")
        return

    save_snapshot(CURRENT_SNAPSHOT, followers, following)

    print("\n[+] Snapshot baru berhasil dibuat")
    print(f"    File            : {CURRENT_SNAPSHOT}")
    print(f"    Total followers : {len(followers)}")
    print(f"    Total following : {len(following)}")
    print(f"    Mutuals         : {len(followers & following)}")
    print(f"    Not follow back : {len(following - followers)}")


def compare_old_and_new(send_to_telegram=False) -> None:
    if not os.path.exists(PREVIOUS_SNAPSHOT):
        print(f"File {PREVIOUS_SNAPSHOT} tidak ditemukan.")
        print("Rename snapshot lama kamu menjadi snapshot_old.json dulu.")
        return

    if not os.path.exists(CURRENT_SNAPSHOT):
        print(f"File {CURRENT_SNAPSHOT} tidak ditemukan.")
        print("Jalankan menu 'Buat snapshot baru' dulu.")
        return

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

    print(f"\n[+] Hasil berhasil disimpan ke: {RESULT_FILE}")

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
            print("[+] Ringkasan berhasil dikirim ke Telegram")
        else:
            print(f"[!] Gagal kirim ringkasan Telegram: {info}")

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
    cache = load_profile_cache()

    username = normalize_username(input("Username IG: ").strip())
    if not username:
        print("Username tidak valid.")
        return

    name = input("Nama akun: ").strip() or "N/A"
    followers = input("Jumlah followers: ").strip() or "N/A"
    following = input("Jumlah following: ").strip() or "N/A"

    cache[username] = {
        "name": name,
        "followers": followers,
        "following": following,
        "profile_url": instagram_link(username),
        "source": "MANUAL",
        "note": "",
    }

    save_profile_cache(cache)
    print(f"[+] Profile cache untuk @{username} berhasil disimpan.")


def show_help() -> None:
    print("\nCatatan penggunaan:")
    print(f"- Letakkan {FOLLOWERS_FILE} dan {FOLLOWING_FILE} di folder yang sama")
    print(f"- Buat snapshot baru ke {CURRENT_SNAPSHOT}")
    print(f"- Rename snapshot lama ke {PREVIOUS_SNAPSHOT}")
    print("- Compare untuk melihat hasil perubahan")
    print("- Isi profile cache manual untuk akun yang ingin tampil full info")
    print("- Aktifkan Telegram jika ingin hasil dikirim ke bot")


def main() -> None:
    show_logo()

    while True:
        print("\n=== MENU ===")
        print("1. Buat snapshot baru")
        print("2. Bandingkan snapshot lama vs baru")
        print("3. Bandingkan + kirim ke Telegram")
        print("4. Tambah/update profile cache manual")
        print("5. Bantuan")
        print("6. Keluar")

        choice = input("\nPilih (1/2/3/4/5/6): ").strip()

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
                show_help()
            elif choice == "6":
                print("Keluar dari VALOSINT Tracker.")
                break
            else:
                print("Pilihan tidak valid.")
        except Exception as e:
            print(f"\n[!] Error: {e}")


if __name__ == "__main__":
    main()
