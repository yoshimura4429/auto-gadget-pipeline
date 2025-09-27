import os
import json
import argparse
from pathlib import Path
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT = os.getenv("OPENAI_PROJECT")
OPENAI_ORG = os.getenv("OPENAI_ORG")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

# ====== 外部ファイルからプロンプトを読む関数 ======
def load_prompt(name: str) -> str:
    path = Path("prompts") / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"プロンプトファイルが見つかりません: {path}")
    return path.read_text(encoding="utf-8")

# ====== カテゴリ別プロンプト ======
PROMPTS = {
    "活用法": load_prompt("活用法"),
    "速報": load_prompt("速報"),
    "熱量": load_prompt("熱量"),
}

# ====== API呼び出し ======
def call_openai(system_prompt, user_prompt, category, angle=None):
    import os, json, requests, re
    from dotenv import load_dotenv
    load_dotenv(".env")

    key  = os.getenv("OPENAI_API_KEY", "")
    org  = os.getenv("OPENAI_ORG", "") or os.getenv("OPENAI_ORGANIZATION", "")
    proj = os.getenv("OPENAI_PROJECT", "")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature = 0.9 if category in ("速報", "熱量") else 0.7

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if org:
        headers["OpenAI-Organization"] = org
    if proj:
        headers["OpenAI-Project"] = proj

    # 角度(方向性)の前置き
    angle_prefix = f"【記事の方向性】{angle}\n" if angle else ""

    # === ここから chat/completions 形式に戻す ===
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",    "content": angle_prefix + user_prompt},
        ],
        "temperature": temperature,
    }

    r = requests.post(url, headers=headers, json=payload, timeout=60)
    print("* /v1/chat/completions ->", r.status_code)
    if r.status_code != 200:
        print("BODY:", r.text[:1200])
        r.raise_for_status()

    data = r.json()
    out = data["choices"][0]["message"]["content"]
    return out

# ==== 引数 ====
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", required=True,
                        choices=["活用法", "速報", "熱量"],
                        help="記事カテゴリを選択")
    parser.add_argument("--source_file", required=True,
                        help="叩き台テキスト（.md/.txt）。指定時は収集をスキップして記事化のみ実行")
    parser.add_argument("--angle", default="",
                        help="記事の方向性（例: 'それでもiPadが欲しい'）")
    return parser.parse_args()

# ====== メイン ======
def main():
    args = parse_args()

    # 素材の読み込み
    if args.source_file:
        material = Path(args.source_file).read_text(encoding="utf-8").strip()
    else:
        raise ValueError("--source_file を指定してください（現状は収集機能未接続）")

    # ベースのシステムプロンプト（カテゴリ別）
    system_prompt = PROMPTS[args.category]

    # ユーザープロンプト（素材 + 方向性）
    angle_line = f"\n【記事の方向性】{args.angle}\n" if args.angle else ""
    user_prompt = f"【素材】\n{material}\n{angle_line}".strip()

    # 生成
    article_md = call_openai(system_prompt, user_prompt, args.category)

    # 保存
    outdir = Path("dist"); outdir.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    suffix = f"-{args.category}" + (f"-angle" if args.angle else "")
    outfile = outdir / f"{today}{suffix}.md"
    outfile.write_text(article_md, encoding="utf-8")
    print(f"✅ 記事生成完了: {outfile}")

if __name__ == "__main__":
    main()