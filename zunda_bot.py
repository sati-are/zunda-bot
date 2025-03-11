import discord
from discord.ext import commands
import os
import datetime
import openrouter
from transformers import pipeline, BitsAndBytesConfig, AutoTokenizer
import tiktoken
import asyncio
import requests
import traceback

# ボットの設定
bot = commands.Bot(command_prefix="!")  # コマンドプレフィックスを「!」に設定
processing_queue = asyncio.Queue(maxsize=3)  # 同時リクエストを3件に制限
bot.notify_enabled = True  # 通知デフォルトオン
send_count = {}  # チャンネルごとの送信回数とタイムスタンプ
used_tokens = 0  # トークン使用量の追跡
is_rate_limited = False  # レート制限状態
bot.first_summary = True  # 初回要約フラグ

# 環境変数から設定を読み込む
TOKEN = os.getenv("TOKEN")  # Discord Botトークン
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))  # 特定チャンネルID
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")  # DeepSeek APIキー
DAILY_TOKEN_LIMIT = 7500  # デフォルトのトークン上限（DeepSeek R1）
MAX_SIZE = 20 * 1024  # 20KBでログを要約
DEEPSEEK_TIMEOUT = 60  # DeepSeek APIのタイムアウト（秒）

# Mixtral 8x7Bの8-bit量子化設定
quantization_config = BitsAndBytesConfig(load_in_8bit=True)
summarizer_fallback = pipeline("text-generation", model="meta-llama/Mixtral-8x7B", device=0 if torch.cuda.is_available() else -1, quantization_config=quantization_config)
tokenizer_mixtral = AutoTokenizer.from_pretrained("meta-llama/Mixtral-8x7B")

# 東北弁のプロンプト
zunda_prompt = "ずんだもんは東北弁で可愛く答えるAIチャットBotなのだ！"

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

# 応答生成（DeepSeek R1またはMixtral 8x7B）
def get_response(question, logs):
    global used_tokens, is_rate_limited
    check_token_reset()

    if is_rate_limited:
        return summarizer_fallback(f"東北弁で可愛く答えるのだ：{question}", max_length=50, do_sample=True)[0]['generated_text']

    try:
        client = openrouter.OpenRouter(api_key=DEEPSEEK_API_KEY)
        response = client.completions.create(
            model="deepseek/deepseek-r1",
            prompt=f"東北弁で可愛く答えるAIチャットBot（ずんだもん）として、以下のログを考慮して回答：\nログ：{logs}\n質問：{question}",
            max_tokens=1,  # 最終回答は1トークン
            response_format={"type": "json", "reasoning_content": True},
            timeout=DEEPSEEK_TIMEOUT
        )
        token_count = get_token_count(question + logs)
        if used_tokens + token_count > DAILY_TOKEN_LIMIT:
            is_rate_limited = True
            return summarizer_fallback(f"東北弁で可愛く答えるのだ：{question}", max_length=50, do_sample=True)[0]['generated_text']
        used_tokens += token_count + 1
        return response.choices[0].reasoning_content
    except (openrouter.OpenRouterException, requests.RequestException, TimeoutError):
        return summarizer_fallback(f"東北弁で可愛く答えるのだ：{question}", max_length=50, do_sample=True)[0]['generated_text']

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
                await channel.send("ずんだもん、ちょっと多忙すぎちゃったのだ…1分待ってほしいのだよ！")
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

# 要約管理
async def manage_summary(channel):
    global used_tokens, is_rate_limited
    log_file = "all_logs.txt"
    summary_file = "latest_summary.txt"
    
    check_token_reset()

    if os.path.exists(log_file) and os.path.getsize(log_file) > MAX_SIZE and not is_rate_limited:
        if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
            await safe_send(channel, "ずんだもん、過去の記憶を整理してるのだ…少し待ってほしいのだよ！")
        with open(log_file, "r", encoding="utf-8") as f:
            new_logs = f.read()
        try:
            token_count = get_token_count(new_logs)
            if used_tokens + token_count > DAILY_TOKEN_LIMIT:
                is_rate_limited = True
                if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
                    await safe_send(channel, "ずんだもん、今日は一日中頑張ったから適当に答えるのだ…")
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
                await safe_send(channel, "ずんだもん、記憶を整理したのだ！これでスッキリしたのだよ！")

        except (openrouter.OpenRouterException, requests.RequestException, TimeoutError) as e:
            error_msg = f"{datetime.datetime.now()} | エラー: {str(e)}\n{traceback.format_exc()}\n"
            with open("error_logs.txt", "a", encoding="utf-8") as f:
                f.write(error_msg)
            if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
                await safe_send(channel, "ずんだもん、サーバーが疲れちゃったのだ…。24時間待ってから続きをするのだよ！")
            return

        if os.path.exists(summary_file):
            with open(summary_file, "r", encoding="utf-8") as f:
                old_summary = f.read()
            summary = old_summary + "\n" + summary
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(summary)
        open(log_file, "w").close()
        if bot.first_summary:
            if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
                await safe_send(channel, "ずんだもん、過去の記憶がおぼろげになったのだ…。たくさんおしゃべりしたから、ちょっとまとめたのだよ！")
            bot.first_summary = False

# 仮要約管理
async def manage_temporary_summary(channel):
    global used_tokens, is_rate_limited
    log_file = "all_logs.txt"
    temp_summary_file = "temporary_summary.txt"
    
    check_token_reset()

    if os.path.exists(log_file) and os.path.getsize(log_file) > MAX_SIZE / 2 and is_rate_limited:
        if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
            await safe_send(channel, "ずんだもん、過去の記憶を軽く整理してるのだ…少し待ってほしいのだよ！")
        with open(log_file, "r", encoding="utf-8") as f:
            new_logs = f.read()
        try:
            summary = summarizer_fallback(f"以下のログを東北弁で簡潔に要約して：\n{new_logs}", max_length=100, do_sample=True)[0]['generated_text']
            if os.path.exists(temp_summary_file):
                with open(temp_summary_file, "r", encoding="utf-8") as f:
                    old_summary = f.read()
                summary = old_summary + "\n" + summary
            with open(temp_summary_file, "w", encoding="utf-8") as f:
                f.write(summary)
            open(log_file, "w").close()
            if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
                await safe_send(channel, "ずんだもん、記憶を軽く整理したのだ！これで少しスッキリしたのだよ！")
        except Exception as e:
            error_msg = f"{datetime.datetime.now()} | エラー: {str(e)}\n{traceback.format_exc()}\n"
            with open("error_logs.txt", "a", encoding="utf-8") as f:
                f.write(error_msg)
            if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
                await safe_send(channel, "ずんだもん、ちょっとミスっちゃったのだ…24時間待ってから続きをするのだよ！")

# メッセージ処理
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
            await safe_send(message.channel, "ずんだもん、何を聞きたいのだ？もう一度教えてほしいのだよ！")
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
                await safe_send(message.channel, "ずんだもん、サーバーが疲れちゃったのだ…24時間待ってから続きをするのだよ！")
        finally:
            await processing_queue.get()
            await processing_queue.task_done()

# 通知設定コマンド
@bot.command(name="zunda")
async def zunda_command(ctx, action=None):
    if action == "notify":
        if ctx.message.content.split()[-1].lower() == "off":
            bot.notify_enabled = False
            await safe_send(ctx.channel, "ずんだもん、通知をオフにしたのだ！静かにするのだよ！")
        elif ctx.message.content.split()[-1].lower() == "on":
            bot.notify_enabled = True
            await safe_send(ctx.channel, "ずんだもん、通知をオンにしたのだ！元気に答えるのだよ！")
        else:
            await safe_send(ctx.channel, "ずんだもん、「!zunda notify on」か「!zunda notify off」で設定できるのだよ！")
    elif action == "start":
        await safe_send(ctx.channel, "ずんだもん、起動したのだ！「ずんだもん」と呼びかけておしゃべりしようね！")
    else:
        await safe_send(ctx.channel, "ずんだもん、「!zunda start」または「!zunda notify on/off」で操作できるのだよ！")

# ボットの起動
if __name__ == "__main__":
    if not all([TOKEN, CHANNEL_ID, DEEPSEEK_API_KEY]):
        raise ValueError("環境変数（TOKEN, CHANNEL_ID, DEEPSEEK_API_KEY）が設定されていないのだ！ReplitのSecretsで設定してほしいのだよ！")
    bot.run(TOKEN)