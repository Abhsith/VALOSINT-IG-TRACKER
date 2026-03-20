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
    print("Module colorama belum terinstall. Install: pip install colorama")
    sys.exit(1)

init(autoreset=True)

# FILE CONFIG
FOLLOWERS_JSON = "followers_1.json"
FOLLOWERS_HTML = "followers_1.html"
FOLLOWING_JSON = "following.json"
FOLLOWING_HTML = "following.html"

SNAPSHOT_NEW = "snapshot_new.json"
SNAPSHOT_OLD = "snapshot_old.json"
RESULT_FILE = "result.txt"

C = Fore.CYAN
G = Fore.GREEN
R = Fore.RED
Y = Fore.YELLOW

def log(msg, t="info"):
    if t=="ok": print(f"{G}[+]{msg}")
    elif t=="err": print(f"{R}[-]{msg}")
    else: print(f"{C}[~]{msg}")

# HTML PARSER
class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.users = set()

    def handle_data(self, data):
        data = data.strip().replace("@","")
        if re.match(r"^[a-zA-Z0-9._]+$", data):
            self.users.add(data.lower())

def parse_html(file):
    with open(file,"r",encoding="utf-8",errors="ignore") as f:
        p = Parser()
        p.feed(f.read())
    return p.users

def parse_json(file):
    with open(file,"r") as f:
        data = json.load(f)

    users=set()
    def walk(d):
        if isinstance(d,list):
            for x in d: walk(x)
        elif isinstance(d,dict):
            if "string_list_data" in d:
                for i in d["string_list_data"]:
                    users.add(i["value"].lower())
            else:
                for v in d.values(): walk(v)
    walk(data)
    return users

def load_data():
    if os.path.exists(FOLLOWERS_JSON):
        followers=parse_json(FOLLOWERS_JSON)
        log("Followers JSON loaded","ok")
    else:
        followers=parse_html(FOLLOWERS_HTML)
        log("Followers HTML loaded","ok")

    if os.path.exists(FOLLOWING_JSON):
        following=parse_json(FOLLOWING_JSON)
        log("Following JSON loaded","ok")
    else:
        following=parse_html(FOLLOWING_HTML)
        log("Following HTML loaded","ok")

    return followers,following

def save_snapshot(name,f1,f2):
    data={
        "time":str(datetime.now()),
        "followers":list(f1),
        "following":list(f2)
    }
    with open(name,"w") as f:
        json.dump(data,f,indent=2)

def load_snapshot(name):
    with open(name) as f:
        d=json.load(f)
    return set(d["followers"]),set(d["following"])

def compare():
    if not os.path.exists(SNAPSHOT_OLD):
        log("snapshot_old.json belum ada","err")
        return

    f_old,fo_old=load_snapshot(SNAPSHOT_OLD)
    f_new,fo_new=load_snapshot(SNAPSHOT_NEW)

    unfollow=f_old-f_new
    not_back=fo_new-f_new

    print("\nUNFOLLOW:")
    for u in unfollow: print("-",u)

    print("\nNOT FOLLOW BACK:")
    for u in not_back: print("-",u)

def main():
    print("VALOSINT TRACKER FULL VERSION\n")

    while True:
        print("1. Create snapshot")
        print("2. Compare")
        print("3. Exit")
        c=input("> ")

        if c=="1":
            f1,f2=load_data()
            save_snapshot(SNAPSHOT_NEW,f1,f2)
            log("Snapshot dibuat","ok")

        elif c=="2":
            compare()

        elif c=="3":
            break

if __name__=="__main__":
    main()
