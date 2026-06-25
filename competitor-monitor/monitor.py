import os
import hashlib
import difflib
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
NOTIFY_EMAIL = os.environ["NOTIFY_EMAIL"]
SMTP_HOST = os.environ["SMTP_HOST"]
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ["SMTP_USER"]
SMTP_PASS = os.environ["SMTP_PASS"]

db = create_client(SUPABASE_URL, SUPABASE_KEY)


def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return " ".join(soup.get_text().split())


def change_pct(old: str, new: str) -> float:
    matcher = difflib.SequenceMatcher(None, old, new)
    return round((1 - matcher.ratio()) * 100, 2)


def fetch(url: str) -> str | None:
    try:
        r = httpx.get(url, timeout=15, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (compatible; ContentMonitor/1.0)"
        })
        r.raise_for_status()
        return extract_text(r.text)
    except Exception as e:
        print(f"  error fetching {url}: {e}")
        return None


def send_email(label: str, url: str, pct: float, old: str, new: str):
    diff = difflib.unified_diff(
        old.split(), new.split(), lineterm="", n=5
    )
    diff_text = " ".join(list(diff)[:200])

    body = f"""Content change detected on {label or url}

URL: {url}
Change: {pct}%
Time: {datetime.now(timezone.utc).isoformat()}

--- Diff (first 200 tokens) ---
{diff_text}
"""
    msg = MIMEText(body)
    msg["Subject"] = f"[Monitor] {pct}% change on {label or url}"
    msg["From"] = SMTP_USER
    msg["To"] = NOTIFY_EMAIL

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(SMTP_USER, NOTIFY_EMAIL, msg.as_string())
    print(f"  notified: {pct}% change")


def due_urls():
    # returns URLs where last_checked_at is null or overdue
    rows = db.rpc("due_urls").execute()
    return rows.data


def run():
    urls = due_urls()
    print(f"checking {len(urls)} due URL(s)")

    for row in urls:
        uid, url, label, threshold = (
            row["id"], row["url"], row["label"], row["threshold_pct"]
        )
        print(f"  {url}")

        content = fetch(url)
        if content is None:
            continue

        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # get last snapshot
        last = (
            db.table("snapshots")
            .select("content, content_hash")
            .eq("url_id", uid)
            .order("checked_at", desc=True)
            .limit(1)
            .execute()
            .data
        )

        pct = 0.0
        if last:
            if last[0]["content_hash"] == content_hash:
                print("  no change")
                _update_checked(uid)
                continue
            pct = change_pct(last[0]["content"], content)
            print(f"  {pct}% change")
            if pct >= threshold:
                send_email(label, url, pct, last[0]["content"], content)

        db.table("snapshots").insert({
            "url_id": uid,
            "content": content,
            "content_hash": content_hash,
            "change_pct": pct,
        }).execute()

        _update_checked(uid)


def _update_checked(uid: str):
    db.table("monitored_urls").update(
        {"last_checked_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", uid).execute()


if __name__ == "__main__":
    run()
