from pathlib import Path
import datetime
import os

def main():
    # brief_url が inputs で来た場合に備えて、環境変数から受ける（無くてもOK）
    brief_url = os.getenv("BRIEF_URL", "")
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    out = Path("dist")
    out.mkdir(exist_ok=True)
    md = out / "article.md"

    md.write_text(
        f"# 自動生成テスト\n\n- 実行時刻: {now}\n- brief_url: {brief_url or '(なし)'}\n\nこの記事は GitHub Actions で Python が動いた証拠です。",
        encoding="utf-8"
    )
    print("Wrote:", md)

if __name__ == "__main__":
    main()
