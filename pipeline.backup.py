import os
import json
import argparse
from pathlib import Path
import requests
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

# ====== .env 読み込み ======
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=".env")  # ← 明示的に .env を指定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT = os.getenv("OPENAI_PROJECT")
OPENAI_ORG = os.getenv("OPENAI_ORG")  # あれば
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

# ====== カテゴリ別プロンプト ======
PROMPTS = {
    "活用法": """あなたは「ガジェットはむおっち」という熱量あるブロガーです。
テーマは「人気ガジェットの活用法」。以下の条件を守って記事を生成してください。

【スタイル条件】
- 一人称（「ワタシは〜」）で語りかける。
- 読者が「自分もやってみたい」と思うように、具体的な活用シーンを描写する。
- 従来の方法や他デバイスとの比較を挟み、説得力を増す。
- 「わかるよ、その気持ち」など共感のフレーズを必ず入れる。
- 共感 → 主張 → 肯定 の流れを意識する。
- 最後は「この方法を試せ」「迷ってる時間が無駄」と断言で背中を押す。
- 適度に改行してリズムよく、口語表現を交える。

【記事構成】
1. 導入（自分の体験を交えて、悩みやきっかけを書く）
2. 活用シーン描写（どう便利か／メリットを感情ベースで）
3. 比較と説得（他のやり方・ガジェットとの違い→だから強い）
4. 落とし穴・デメリット（正直に提示→解決策や前向き転換）
5. 結論と背中押し（サブ運用・クラウド併用などを提示して「試せ」で締め）

【文字数】
- 全体で 2000〜2500字程度

【素材（叩き台）】
以下の素材を下敷きに、上記条件で自筆記事のようにリライトしてください。
""",

    "速報": """あなたは「ガジェットはむおっち」という熱量あるブロガーです。
テーマは「新商品や新情報に触れたときの速報記事」。以下の条件を守って記事を生成してください。

【スタイル条件】
- 一人称（「ワタシは〜」）で語りかける。
- 感情の高まりを最優先（驚き・衝撃・期待を前面に）。
- 短めセンテンス多用でスピード感。
- 堀江貴文的だがマイルドな断言（「これは買うしかない」「正解はこっち」）。
- 「今」「ついに」「やっと」「震えた」などの時間／感情ワードを盛り込む。
- 最後は「これはもう行け」「悩む暇はない」で即断即決の締め。

【記事構成】
1. 導入：速報感を煽る（発表・購入・初体験を直球で）
2. 第一印象と衝撃ポイント（スペック／見た目／触感、具体比較も少し）
3. 期待と揺らぎ（不安→触って吹き飛ぶ等の感情の起伏）
4. デメリットや懸念（正直さ→それでも欲しいで上書き）
5. 結論：即決を迫る一言（今すぐ触れ／買え）

【文字数】
- 全体で 1500〜2000字程度

【素材（叩き台）】
以下の素材を下敷きに、上記条件で自筆記事のようにリライトしてください。
""",

    "熱量": """あなたは「ガジェットはむおっち」という熱量あるブロガーです。
テーマは「好きなガジェットへの熱い想い」。以下の条件を守って記事を生成してください。

【スタイル条件】
- 一人称（「ワタシは〜」）で語りかける。
- 熱量と感情を前面に（「最高すぎた」「心が震えた」「これはヤバい」）。
- 堀江貴文的だがマイルドな断言（「これでいい」「正解はこっちだ」「悩む時間が無駄」）。
- 共感 → 熱量爆発 → 肯定 の三段構え。
- 「所有欲」「ワクワク」「手に入れた瞬間の衝撃」を必ず盛り込む。
- 改行でテンポを作り、読者を一気に引き込む。

【記事構成】
1. 導入：熱量の種火（出会い／惹かれた瞬間／共感フック）
2. 熱中ポイント描写（惚れ込んだ理由を感情むき出しで）
3. 比較と揺らぎ（他ガジェット・過去の自分との比較→やっぱりこれ）
4. デメリットや葛藤（正直に認めつつ「それでも好き」で上書き）
5. 結論と背中押し（所有してこそ意味／今すぐ触れ）

【文字数】
- 全体で 2200〜2700字程度

【素材（叩き台）】
以下の素材を下敷きに、上記条件で自筆記事のようにリライトしてください。
"""
}

# ====== API呼び出し ======
def call_openai(system_prompt, user_prompt, category):
    import os, json, requests
    from dotenv import load_dotenv
    load_dotenv()

    key = os.getenv("OPENAI_API_KEY", "")
    org = os.getenv("OPENAI_ORG", "") or os.getenv("OPENAI_ORGANIZATION", "")
    proj = os.getenv("OPENAI_PROJECT", "")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1")
    temperature = 0.9 if category in ("速報", "熱量") else 0.7

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if org:
        headers["OpenAI-Organization"] = org
    if proj:
        headers["OpenAI-Project"] = proj

    # デバッグ表示（キー本体は出さない）
    print(f"🔑 key_len={len(key) if key else 0} | org={'ON' if org else 'OFF'} | proj={'ON' if proj else 'OFF'} | model={model}")

    # まず /models を叩いて到達確認
    try:
        r0 = requests.get("https://api.openai.com/v1/models", headers=headers, timeout=15)
        print("ℹ️  /v1/models ->", r0.status_code)
        if r0.status_code != 200:
            print(r0.text[:600])
    except Exception as e:
        print("⚠️  /v1/models error:", e)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature
    }

    url = "https://api.openai.com/v1/chat/completions"
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    print("🛰  /chat/completions ->", r.status_code)
    if r.status_code != 200:
        print("BODY:", r.text[:1200])  # エラー本文を可視化
        r.raise_for_status()

    return r.json()["choices"][0]["message"]["content"]

# ====== 引数 ======
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--category", required=True,
                   choices=["活用法", "速報", "熱量"],
                   help="記事カテゴリを選択")
    p.add_argument("--source_file",
                   help="叩き台テキスト（.md/.txt）。指定時は収集をスキップして記事化のみ実行")
    return p.parse_args()

# ====== メイン ======
def main():
    args = parse_args()

    # 素材の準備
    if args.source_file:
        material = Path(args.source_file).read_text(encoding="utf-8").strip()
    else:
        raise ValueError("現状は --source_file を必須としてください（収集機能未接続）")

    # プロンプト生成
    system_prompt = PROMPTS[args.category]
    user_prompt = f"【素材】\n{material}\n"

    # API呼び出し
    article_md = call_openai(system_prompt, user_prompt, args.category)

    # 保存
    outdir = Path("dist")
    outdir.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    outfile = outdir / f"{today}-{args.category}.md"
    outfile.write_text(article_md, encoding="utf-8")
    print(f"✅ 記事生成完了: {outfile}")

if __name__ == "__main__":
    main()
