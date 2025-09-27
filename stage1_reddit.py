import os, json, time, argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import praw
import requests

# ========= 設定 =========
WORK = Path("workspace"); WORK.mkdir(exist_ok=True)
INPUTS = Path("inputs"); INPUTS.mkdir(exist_ok=True)
RAW_JSON = WORK / "latest.json"
DRAFT_MD = INPUTS / "draft.md"

DEFAULT_SUBS = ["ipad", "apple", "ipados", "mac", "gadgets"]

# ========= ENV 読み込み =========
load_dotenv(dotenv_path=".env")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "my-reddit-app/0.1 by you")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_PROJECT = os.getenv("OPENAI_PROJECT", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

def translate_keyword_if_needed(keyword: str, disable=False) -> str:
    """日本語っぽければ英訳。失敗時や無効化時はそのまま返す。"""
    if disable or not OPENAI_API_KEY:
        return keyword
    # ひらがな・カタカナ・漢字が含まれていれば翻訳候補
    if not any("\u3040" <= ch <= "\u30ff" or "\u4e00" <= ch <= "\u9fff" for ch in keyword):
        return keyword
    try:
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        if OPENAI_PROJECT:
            headers["OpenAI-Project"] = OPENAI_PROJECT
        payload = {
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": "You translate Japanese search keywords into concise English search terms (1-3 words). Output English only."},
                {"role": "user", "content": keyword}
            ],
            "temperature": 0.2
        }
        r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"].strip()
        # カンマや改行を消して短く
        return " ".join(text.replace(",", " ").split())[:60]
    except Exception:
        return keyword

def reddit_client():
    if not (REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET):
        raise RuntimeError("Reddit 認証情報が不足しています（.env の REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET / REDDIT_USER_AGENT を確認）")
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
        ratelimit_seconds=5,
    )

def collect(keyword:str, subs:list, limit:int=12, max_comments:int=12):
    reddit = reddit_client()
    sub_union = "+".join(subs)
    results = {
        "keyword_input": keyword,
        "subs": subs,
        "collected_at": datetime.now().isoformat(),
        "posts": []
    }
    # relevance を優先、複数サブを横断
    for submission in reddit.subreddit(sub_union).search(keyword, sort="relevance", limit=limit):
        post = {
            "subreddit": str(submission.subreddit),
            "title": submission.title,
            "url": f"https://www.reddit.com{submission.permalink}",
            "score": int(submission.score or 0),
            "comments": []
        }
        # 上位コメントを取得（スパム/短文は軽くフィルタ）
        submission.comments.replace_more(limit=0)
        comments = sorted(submission.comments, key=lambda c: getattr(c, "score", 0), reverse=True)[:max_comments]
        for c in comments:
            body = getattr(c, "body", "") or ""
            if len(body.strip()) < 40: 
                continue
            post["comments"].append({
                "score": int(getattr(c, "score", 0) or 0),
                "text": body.strip()
            })
        if post["comments"]:
            results["posts"].append(post)
    return results

def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def build_draft_md(data:dict, keyword:str, keyword_en:str):
    lines = []
    lines.append(f"# 叩き台（{keyword} / {keyword_en}）")
    lines.append("")
    lines.append("※ このファイルは Reddit の生の声を種にした“下書き”です。固有名詞の出典は本文でぼかして扱ってください（例：「ネットの声では」）。")
    lines.append("")
    # 簡易ハイライト抽出（超ざっくり）
    pros, cons, use = [], [], []
    quotes = []
    for p in data.get("posts", []):
        for c in p.get("comments", []):
            t = c["text"]
            if any(w in t.lower() for w in ["light", "portable", "battery", "workflow", "seamless", "love", "perfect"]):
                pros.append(t[:220].replace("\n"," "))
            if any(w in t.lower() for w in ["heavy", "weight", "bug", "issue", "problem", "price"]):
                cons.append(t[:220].replace("\n"," "))
            if any(w in t.lower() for w in ["use", "reading", "note", "sketch", "edit", "work", "study"]):
                use.append(t[:220].replace("\n"," "))
            if len(quotes) < 8 and len(t) > 120:
                quotes.append(t.strip())
    lines += ["## ざっくり要点", ""]
    lines += ["- 強み: " + (", ".join(list(dict.fromkeys(pros))[:5]) if pros else "（これから追記）")]
    lines += ["- 弱み: " + (", ".join(list(dict.fromkeys(cons))[:5]) if cons else "（これから追記）")]
    lines += ["- 使い道: " + (", ".join(list(dict.fromkeys(use))[:5]) if use else "（これから追記）"), ""]
    lines += ["## 引用メモ（抜粋・意訳OK）", ""]
    for q in quotes:
        lines.append(f"> {q}\n")
    lines += ["## 叩き台アウトライン", ""]
    lines += [
        "### 導入メモ",
        "- 何に悩んで何を試したか。最初の違和感やつまずき。",
        "",
        "### 魅力（所有感・連携・手軽さ）",
        "- 感情ベースの良さ + 小さな気づき。",
        "",
        "### 比較と揺らぎ",
        "- 数字や使用感（重量/価格/電池）を入れつつ、心が揺れる瞬間。",
        "",
        "### デメリットと対処",
        "- 正面から課題に触れて、現実的な解決案。",
        "",
        "### 活用法（ユースケース）",
        "- 読書 / 会議メモ / クリエイティブ下書き など1日の流れで。",
        ""
    ]
    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword", required=True, help="日本語でもOK。必要に応じて英訳して検索")
    ap.add_argument("--subs", default=",".join(DEFAULT_SUBS), help="カンマ区切り subreddit")
    ap.add_argument("--limit", type=int, default=12)
    ap.add_argument("--no-translate", action="store_true", help="英訳を行わない")
    args = ap.parse_args()

    subs = [s.strip() for s in args.subs.split(",") if s.strip()]
    keyword_en = translate_keyword_if_needed(args.keyword, disable=args.no_translate)

    print(f"🔎 keyword_ja='{args.keyword}' | keyword_en='{keyword_en}' | subs={subs}")
    data = collect(keyword_en, subs, limit=args.limit)
    save_json(RAW_JSON, data)
    print(f"💾 原データ保存: {RAW_JSON}")

    draft = build_draft_md(data, args.keyword, keyword_en)
    DRAFT_MD.write_text(draft, encoding="utf-8")
    print(f"📝 叩き台を作成: {DRAFT_MD}")

if __name__ == "__main__":
    main()