import discord
from discord.ext import commands
import os
import datetime
import openrouter
import tiktoken
import asyncio
import requests

# ボットの設定
bot = commands.Bot(command_prefix="!")  # コマンドプレフィックスを「!」に設定
processing_queue = asyncio.Queue(maxsize=3)  # 同時リクエストを3件に制限
send_count = {}  # チャンネルごとの送信回数とタイムスタンプ
used_tokens = 0  # トークン使用量の追跡
is_rate_limited = False  # レート制限状態
bot.first_summary = True  # 初回要約フラグ
bot.notify_enabled = True  # 通知デフォルトオン

# 環境変数から設定を読み込む
TOKEN = os.getenv("TOKEN")  # Discord Botトークン
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))  # 特定チャンネルID
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")  # DeepSeek APIキー
HF_API_KEY = os.getenv("HF_API_KEY")  # Hugging Face APIキー
DAILY_TOKEN_LIMIT = 7500  # DeepSeek R1のトークン上限（7,500トークン/日）
MAX_SIZE = 20 * 1024  # 20KBでログを要約
DEEPSEEK_TIMEOUT = 60  # DeepSeek APIのタイムアウト（秒）

# 東北弁のプロンプト
zunda_base = (
    "ずんだもんは東北弁で可愛く、元気いっぱいで答えるAIチャットBotなのだ。\n"
    "全ての答えを一人称「ぼく」で、語尾を「～のだ」か「～なのだ」に必ずして、敬語を使わず、楽しく明るく話すのだ。"
)

normal_instruction = "質問への回答を最大130トークン以内で簡潔に答えるのだ。\n必要に応じて推論を加えて答えるのだ。\n長くなりそうな場合は「続きがあるのでもう一度話しかけてほしいのだ！」と付けるのだ。\n回答外は削除して、純粋な回答だけにするのだ。"
long_instruction = "質問への回答を最大2000トークン以内で詳しく答えるのだ。\n必要に応じて推論を加えて答えるのだ。\n長くなりそうな場合は「続きがあるのでもう一度話しかけてほしいのだ！」と付けるのだ。\n回答外は削除して、純粋な回答だけにするのだ。"

# トークンカウント関数
def get_token_count(text):
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

# トークンリセットチェック
def check_token_reset():
    global used_tokens, is_rate_limited
    current_time = datetime.datetime.now()
    if current_time.hour == 0 and current_time.minute == 0:  # UTC 0:00
        used_tokens = 0
        is_rate_limited = False

# 応答モードの判定
def get_response_mode(question):
    question_lower = question.lower()
    long_triggers = ["長文", "詳細", "詳しく"]
    if any(trigger in question_lower for trigger in long_triggers):
        return "long", 2000, long_instruction
    return "normal", 130, normal_instruction

# Hugging Face APIで応答生成（推論部分を除去）
def get_hf_response(prompt, max_tokens):
    url = "https://api-inference.huggingface.co/models/mixtral-8x7b"  # モデルは必要に応じて更新
    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "inputs": prompt,
        "parameters": {"max_length": max_tokens, "temperature": 0.7, "top_p": 0.9},
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)
        response.raise_for_status()
        raw_text = response.json()[0]["generated_text"] if response.json() else "サーバーが疲れちゃったのだ…24時間待ってから続きをするのだ！"
        
        # プロンプトと推論部分を除去
        if raw_text.startswith(prompt):
            raw_text = raw_text[len(prompt):].strip()
        if "推論：" in raw_text:
            raw_text = raw_text.split("推論：", 1)[1].strip()

        token_count = get_token_count(raw_text)
        if token_count > max_tokens:
            encoding = tiktoken.get_encoding("cl100k_base")
            tokens = encoding.encode(raw_text)[:max_tokens]
            trimmed_text = encoding.decode(tokens).rsplit(" ", 1)[0]  # 末尾でトリミング
            return f"{trimmed_text}…\n続きがあるのでもう一度話しかけてほしいのだ！"
        return raw_text
    except Exception as e:
        error_msg = f"{datetime.datetime.now()} | HF APIエラー: {str(e)}\n"
        with open("error_logs.txt", "a", encoding="utf-8") as f:
            f.write(error_msg)
        return "サーバーが疲れちゃったのだ…24時間待ってから続きをするのだ！"

# 応答生成（DeepSeek R1で推論、Hugging Faceで応答）
def get_response(question, logs):
    global used_tokens, is_rate_limited
    check_token_reset()

    # DeepSeek R1で推論を取得（max_tokens=1でreasoning_contentのみ）
    reasoning = ""
    if not is_rate_limited:
        try:
            client = openrouter.OpenRouter(api_key=DEEPSEEK_API_KEY)
            response = client.completions.create(
                model="deepseek/deepseek-r1",
                prompt=f"{zunda_base}\nログ：{logs}\n質問：{question}",
                max_tokens=1,  # 最終回答は1トークン、推論（reasoning_content）のみ取得
                response_format={"type": "json", "reasoning_content": True},
                timeout=DEEPSEEK_TIMEOUT
            )
            token_count = get_token_count(question + logs)
            if used_tokens + token_count > DAILY_TOKEN_LIMIT:
                is_rate_limited = True
            else:
                used_tokens += token_count + 1
                reasoning = response.choices[0].reasoning_content
                print(f"DeepSeek R1推論: {reasoning}")  # デバッグ用
        except Exception as e:
            print(f"DeepSeek R1エラー: {str(e)}")
            reasoning = ""

    # 応答モード（通常/長文）を判定
    mode, max_tokens, mode_instruction = get_response_mode(question)
    zunda_instruction = (
        "東北弁で可愛く、元気いっぱいで答えるのだ。\n"
        "一人称は「ぼく」で、語尾は「～のだ」か「～なのだ」に必ずして、敬語を使わず、楽しく明るく話すのだ。\n"
        + mode_instruction
    )

    # Hugging Face APIで最終応答を生成（推論をプロンプトに含める）
    prompt = f"{zunda_base}\n{zunda_instruction}\n推論：{reasoning}\n質問：{question}"
    return get_hf_response(prompt, max_tokens)

# 安全なメッセージ送信（レート制限対応）
async def safe_send(channel, message):
    global send_count
    channel_id = channel.id
    current_time = datetime.datetime.now()
    
    # 1秒と1分の送信回数をリセット
    if channel_id not in send_count:
        send_count[channel_id] = {'count_1s': 0, 'count_1m': 0, 'timestamp_1s': current_time, 'timestamp_1m': current_time}
    
    # 1秒のリセット
    if (current_time - send_count[channel_id]['timestamp_1s']).total_seconds() > 1:
        send_count[channel_id]['count_1s'] = 0
        send_count[channel_id]['timestamp_1s'] = current_time
    
    # 1分のリセット
    if (current_time - send_count[channel_id]['timestamp_1m']).total_seconds() > 60:
        send_count[channel_id]['count_1m'] = 0
        send_count[channel_id]['timestamp_1m'] = current_time
    
    send_count[channel_id]['count_1s'] += 1
    send_count[channel_id]['count_1m'] += 1

    try:
        await channel.send(message)
        # 1秒に5回以上または1分に5回以上なら30秒待機、通常は1秒待機
        wait_time = 30 if send_count[channel_id]['count_1s'] >= 5 or send_count[channel_id]['count_1m'] >= 5 else 1
        await asyncio.sleep(wait_time)
    except discord.errors.HTTPException as e:
        if e.status == 429:  # レート制限エラー
            if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
                await channel.send("多忙すぎちゃったのだ…1分待ってほしいのだ！")
            await asyncio.sleep(60)  # 60秒待機して再試行
            await channel.send(message)
        else:
            error_msg = f"{datetime.datetime.now()} | Discordエラー: {str(e)}\n{traceback.format_exc()}\n"
            with open("error_logs.txt", "a", encoding="utf-8") as f:
                f.write(error_msg)
            raise e

# ログ保存
async def save_logs(channel):
    if not os.path.exists("all_logs.txt"):
        open("all_logs.txt", "w").close()
    with open("all_logs.txt", "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now()} | チャンネル: {channel.id} | メッセージ: {channel.last_message.content if channel.last_message else 'なし'}\n")

# ログ要約管理（20KBごとにDeepSeek R1で要約）
async def manage_summary(channel):
    global used_tokens, is_rate_limited
    log_file = "all_logs.txt"
    summary_file = "latest_summary.txt"
    
    check_token_reset()

    if os.path.exists(log_file) and os.path.getsize(log_file) > MAX_SIZE and not is_rate_limited:
        if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
            await channel.send("過去の記憶を整理してるのだ…少し待ってほしいのだ！")
        with open(log_file, "r", encoding="utf-8") as f:
            new_logs = f.read()
        try:
            token_count = get_token_count(new_logs)
            if used_tokens + token_count > DAILY_TOKEN_LIMIT:
                is_rate_limited = True
                if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
                    await channel.send("今日は一日中頑張ったから適当に答えるのだ…")
                return

            client = openrouter.OpenRouter(api_key=DEEPSEEK_API_KEY)
            response = client.completions.create(
                model="deepseek/deepseek-r1",
                prompt=f"以下のログを要約して：\n{new_logs}",
                max_tokens=1,
                response_format={"type": "json", "reasoning_content": True},
                timeout=DEEPSEEK_TIMEOUT
            )
            summary = response.choices[0].reasoning_content
            used_tokens += token_count + 1
            if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
                await channel.send("記憶を整理したのだ！これでスッキリしたのだ！")

            if os.path.exists(summary_file):
                with open(summary_file, "r", encoding="utf-8") as f:
                    old_summary = f.read()
                summary = old_summary + "\n" + summary
            with open(summary_file, "w", encoding="utf-8") as f:
                f.write(summary)
            open(log_file, "w").close()
            if bot.first_summary:
                if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
                    await channel.send("過去の記憶がおぼろげになったのだ…。たくさんおしゃべりしたから、ちょっとまとめたのだ！")
                bot.first_summary = False
        except (openrouter.OpenRouterException, requests.RequestException, TimeoutError) as e:
            error_msg = f"{datetime.datetime.now()} | エラー: {str(e)}\n{traceback.format_exc()}\n"
            with open("error_logs.txt", "a", encoding="utf-8") as f:
                f.write(error_msg)
            if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
                await channel.send("サーバーが疲れちゃったのだ…。24時間待ってから続きをするのだ！")
            return

# 仮ログ要約管理（10KBごとにMixtral 8x7Bで簡易要約）
async def manage_temporary_summary(channel):
    global used_tokens, is_rate_limited
    log_file = "all_logs.txt"
    temp_summary_file = "temporary_summary.txt"
    
    check_token_reset()

    if os.path.exists(log_file) and os.path.getsize(log_file) > MAX_SIZE / 2 and is_rate_limited:
        if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
            await channel.send("過去の記憶を軽く整理してるのだ…少し待ってほしいのだ！")
        with open(log_file, "r", encoding="utf-8") as f:
            new_logs = f.read()
        try:
            summary = get_hf_response(f"以下のログを東北弁で簡潔に要約して：\n{new_logs}", 100)
            if os.path.exists(temp_summary_file):
                with open(temp_summary_file, "r", encoding="utf-8") as f:
                    old_summary = f.read()
                summary = old_summary + "\n" + summary
            with open(temp_summary_file, "w", encoding="utf-8") as f:
                f.write(summary)
            open(log_file, "w").close()
            if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
                await channel.send("記憶を軽く整理したのだ！これで少しスッキリしたのだ！")

            # 仮要約使用後にクリア（累積を防ぐ）
            with open(temp_summary_file, "w", encoding="utf-8") as f:
                f.write("")  # クリア
        except Exception as e:
            error_msg = f"{datetime.datetime.now()} | エラー: {str(e)}\n{traceback.format_exc()}\n"
            with open("error_logs.txt", "a", encoding="utf-8") as f:
                f.write(error_msg)
            if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
                await channel.send("ちょっとミスっちゃったのだ…24時間待ってから続きをするのだ！")

# メッセージ処理
@bot.event
async def on_ready():
    print(f"{bot.user}としてログインしたのだ！")
    while True:
        await asyncio.sleep(60)  # 1分ごとにトークンリセットチェック
        check_token_reset()

@bot.event
async def on_message(message):
    if message.author == bot.user or message.channel.id != CHANNEL_ID:
        return

    await save_logs(message.channel)
    await manage_summary(message.channel)
    await manage_temporary_summary(message.channel)

    if message.content.startswith("ずんだもん"):
        question = message.content.replace("ずんだもん", "").strip()
        if not question:
            await safe_send(message.channel, "何を聞きたいのだ？もう一度教えてほしいのだ！")
            return

        try:
            await processing_queue.put(message)
            logs = ""
            if os.path.exists("latest_summary.txt"):
                with open("latest_summary.txt", "r", encoding="utf-8") as f:
                    logs = f.read()
            if os.path.exists("temporary_summary.txt"):
                with open("temporary_summary.txt", "r", encoding="utf-8") as f:
                    temp_logs = f.read()
                logs = logs + "\n" + temp_logs if logs else temp_logs

            response = get_response(question, logs)
            await safe_send(message.channel, response)
        except Exception as e:
            error_msg = f"{datetime.datetime.now()} | エラー: {str(e)}\n{traceback.format_exc()}\n"
            with open("error_logs.txt", "a", encoding="utf-8") as f:
                f.write(error_msg)
            if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
                await safe_send(message.channel, "サーバーが疲れちゃったのだ…24時間待ってから続きをするのだ！")
        finally:
            await processing_queue.get()
            await processing_queue.task_done()

# ボットのコマンド
@bot.command(name="zunda")
async def zunda_command(ctx, action=None, *args):
    if action == "start":
        await safe_send(ctx.channel, "起動したのだ！「ずんだもん」と呼びかけておしゃべりするのだ！")
    elif action == "notify":
        if not args:
            await safe_send(ctx.channel, "「!zunda notify on」か「!zunda notify off」で設定できるのだ！")
            return
        status = args[0].lower()
        if status == "on":
            bot.notify_enabled = True
            await safe_send(ctx.channel, "通知をオンにしたのだ！")
        elif status == "off":
            bot.notify_enabled = False
            await safe_send(ctx.channel, "通知をオフにしたのだ！")
        else:
            await safe_send(ctx.channel, "「on」か「off」を指定してほしいのだ！")
    elif action == "reset":
        # 脳みそリセットの確認
        await safe_send(ctx.channel, "脳みそをリセットすると過去の記憶が全部消えるのだ…本当にいいのだ？「yes」か「no」で答えてほしいのだ！")
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]
        try:
            response = await bot.wait_for("message", check=check, timeout=30.0)
            if response.content.lower() == "yes":
                # ログファイルと要約ファイルのクリア
                for file in ["all_logs.txt", "latest_summary.txt", "temporary_summary.txt"]:
                    if os.path.exists(file):
                        open(file, "w").close()
                bot.first_summary = True
                if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
                    await safe_send(ctx.channel, "脳みそが空っぽになっちゃったのだ…新しくおしゃべりするのだ！")
            else:
                await safe_send(ctx.channel, "リセットをキャンセルしたのだ！これからも楽しくおしゃべりするのだ！")
        except asyncio.TimeoutError:
            await safe_send(ctx.channel, "30秒待っても返事がないのだ…リセットをキャンセルしたのだ！")
    else:
        await safe_send(ctx.channel, "「!zunda start」、「!zunda notify on/off」、「!zunda reset」で操作できるのだ！")

# ボットの起動
if __name__ == "__main__":
    if not all([TOKEN, CHANNEL_ID, DEEPSEEK_API_KEY, HF_API_KEY]):
        raise ValueError("環境変数（TOKEN, CHANNEL_ID, DEEPSEEK_API_KEY, HF_API_KEY）が設定されていないのだ！ReplitのSecretsで設定してほしいのだ！")
    bot.run(TOKEN)
