import os
import praw
from dotenv import load_dotenv

# .env ファイルを読み込む
load_dotenv()

client_id = os.getenv("REDDIT_CLIENT_ID")
client_secret = os.getenv("REDDIT_CLIENT_SECRET")
user_agent = os.getenv("REDDIT_USER_AGENT")

# Reddit インスタンスを作成
reddit = praw.Reddit(
    client_id=client_id,
    client_secret=client_secret,
    user_agent=user_agent
)

# サンプル: "iPad" で検索して、最初の投稿タイトルを表示
for submission in reddit.subreddit("all").search("iPad", limit=5):
    print("📝", submission.title)
