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

# �{�b�g�̐ݒ�
bot = commands.Bot(command_prefix="!")  # �R�}���h�v���t�B�b�N�X���u!�v�ɐݒ�
processing_queue = asyncio.Queue(maxsize=3)  # �������N�G�X�g��3���ɐ���
bot.notify_enabled = True  # �ʒm�f�t�H���g�I��
send_count = {}  # �`�����l�����Ƃ̑��M�񐔂ƃ^�C���X�^���v
used_tokens = 0  # �g�[�N���g�p�ʂ̒ǐ�
is_rate_limited = False  # ���[�g�������
bot.first_summary = True  # ����v��t���O

# ���ϐ�����ݒ��ǂݍ���
TOKEN = os.getenv("TOKEN")  # Discord Bot�g�[�N��
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))  # ����`�����l��ID
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")  # DeepSeek API�L�[
DAILY_TOKEN_LIMIT = 7500  # �f�t�H���g�̃g�[�N������iDeepSeek R1�j
MAX_SIZE = 20 * 1024  # 20KB�Ń��O��v��
DEEPSEEK_TIMEOUT = 60  # DeepSeek API�̃^�C���A�E�g�i�b�j

# Mixtral 8x7B��8-bit�ʎq���ݒ�
quantization_config = BitsAndBytesConfig(load_in_8bit=True)
summarizer_fallback = pipeline("text-generation", model="meta-llama/Mixtral-8x7B", device=0 if torch.cuda.is_available() else -1, quantization_config=quantization_config)
tokenizer_mixtral = AutoTokenizer.from_pretrained("meta-llama/Mixtral-8x7B")

# ���k�ق̃v�����v�g
zunda_prompt = "���񂾂���͓��k�قŉ���������AI�`���b�gBot�Ȃ̂��I"

# �g�[�N���J�E���g�֐�
def get_token_count(text):
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

# �g�[�N�����Z�b�g�`�F�b�N
def check_token_reset():
    global used_tokens, is_rate_limited
    current_time = datetime.datetime.now()
    if current_time.hour == 0 and current_time.minute == 0:  # UTC 0:00
        used_tokens = 0
        is_rate_limited = False

# ���������iDeepSeek R1�܂���Mixtral 8x7B�j
def get_response(question, logs):
    global used_tokens, is_rate_limited
    check_token_reset()

    if is_rate_limited:
        return summarizer_fallback(f"���k�قŉ���������̂��F{question}", max_length=50, do_sample=True)[0]['generated_text']

    try:
        client = openrouter.OpenRouter(api_key=DEEPSEEK_API_KEY)
        response = client.completions.create(
            model="deepseek/deepseek-r1",
            prompt=f"���k�قŉ���������AI�`���b�gBot�i���񂾂���j�Ƃ��āA�ȉ��̃��O���l�����ĉ񓚁F\n���O�F{logs}\n����F{question}",
            max_tokens=1,  # �ŏI�񓚂�1�g�[�N��
            response_format={"type": "json", "reasoning_content": True},
            timeout=DEEPSEEK_TIMEOUT
        )
        token_count = get_token_count(question + logs)
        if used_tokens + token_count > DAILY_TOKEN_LIMIT:
            is_rate_limited = True
            return summarizer_fallback(f"���k�قŉ���������̂��F{question}", max_length=50, do_sample=True)[0]['generated_text']
        used_tokens += token_count + 1
        return response.choices[0].reasoning_content
    except (openrouter.OpenRouterException, requests.RequestException, TimeoutError):
        return summarizer_fallback(f"���k�قŉ���������̂��F{question}", max_length=50, do_sample=True)[0]['generated_text']

# ���S�ȃ��b�Z�[�W���M�i���[�g�����Ή��j
async def safe_send(channel, message):
    global send_count
    channel_id = channel.id
    current_time = datetime.datetime.now()
    
    # 1�b��1���̑��M�񐔂����Z�b�g
    if channel_id not in send_count:
        send_count[channel_id] = {'count_1s': 0, 'count_1m': 0, 'timestamp_1s': current_time, 'timestamp_1m': current_time}
    
    # 1�b�̃��Z�b�g
    if (current_time - send_count[channel_id]['timestamp_1s']).total_seconds() > 1:
        send_count[channel_id]['count_1s'] = 0
        send_count[channel_id]['timestamp_1s'] = current_time
    
    # 1���̃��Z�b�g
    if (current_time - send_count[channel_id]['timestamp_1m']).total_seconds() > 60:
        send_count[channel_id]['count_1m'] = 0
        send_count[channel_id]['timestamp_1m'] = current_time
    
    send_count[channel_id]['count_1s'] += 1
    send_count[channel_id]['count_1m'] += 1

    try:
        await channel.send(message)
        # 1�b��5��ȏ�܂���1����5��ȏ�Ȃ�30�b�ҋ@�A�ʏ��1�b�ҋ@
        wait_time = 30 if send_count[channel_id]['count_1s'] >= 5 or send_count[channel_id]['count_1m'] >= 5 else 1
        await asyncio.sleep(wait_time)
    except discord.errors.HTTPException as e:
        if e.status == 429:  # ���[�g�����G���[
            if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
                await channel.send("���񂾂���A������Ƒ��Z������������̂��c1���҂��Ăق����̂���I")
            await asyncio.sleep(60)  # 60�b�ҋ@���čĎ��s
            await channel.send(message)
        else:
            error_msg = f"{datetime.datetime.now()} | Discord�G���[: {str(e)}\n{traceback.format_exc()}\n"
            with open("error_logs.txt", "a", encoding="utf-8") as f:
                f.write(error_msg)
            raise e

# ���O�ۑ�
async def save_logs(channel):
    if not os.path.exists("all_logs.txt"):
        open("all_logs.txt", "w").close()
    with open("all_logs.txt", "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now()} | �`�����l��: {channel.id} | ���b�Z�[�W: {channel.last_message.content if channel.last_message else '�Ȃ�'}\n")

# �v��Ǘ�
async def manage_summary(channel):
    global used_tokens, is_rate_limited
    log_file = "all_logs.txt"
    summary_file = "latest_summary.txt"
    
    check_token_reset()

    if os.path.exists(log_file) and os.path.getsize(log_file) > MAX_SIZE and not is_rate_limited:
        if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
            await safe_send(channel, "���񂾂���A�ߋ��̋L���𐮗����Ă�̂��c�����҂��Ăق����̂���I")
        with open(log_file, "r", encoding="utf-8") as f:
            new_logs = f.read()
        try:
            token_count = get_token_count(new_logs)
            if used_tokens + token_count > DAILY_TOKEN_LIMIT:
                is_rate_limited = True
                if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
                    await safe_send(channel, "���񂾂���A�����͈�����撣��������K���ɓ�����̂��c")
                return

            client = openrouter.OpenRouter(api_key=DEEPSEEK_API_KEY)
            response = client.completions.create(
                model="deepseek/deepseek-r1",
                prompt=f"�ȉ��̃��O��v�񂵂āF\n{new_logs}",
                max_tokens=1,
                response_format={"type": "json", "reasoning_content": True},
                timeout=DEEPSEEK_TIMEOUT
            )
            summary = response.choices[0].reasoning_content
            used_tokens += token_count + 1
            if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
                await safe_send(channel, "���񂾂���A�L���𐮗������̂��I����ŃX�b�L�������̂���I")

        except (openrouter.OpenRouterException, requests.RequestException, TimeoutError) as e:
            error_msg = f"{datetime.datetime.now()} | �G���[: {str(e)}\n{traceback.format_exc()}\n"
            with open("error_logs.txt", "a", encoding="utf-8") as f:
                f.write(error_msg)
            if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
                await safe_send(channel, "���񂾂���A�T�[�o�[����ꂿ������̂��c�B24���ԑ҂��Ă��瑱��������̂���I")
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
                await safe_send(channel, "���񂾂���A�ߋ��̋L�������ڂ낰�ɂȂ����̂��c�B�������񂨂���ׂ肵������A������Ƃ܂Ƃ߂��̂���I")
            bot.first_summary = False

# ���v��Ǘ�
async def manage_temporary_summary(channel):
    global used_tokens, is_rate_limited
    log_file = "all_logs.txt"
    temp_summary_file = "temporary_summary.txt"
    
    check_token_reset()

    if os.path.exists(log_file) and os.path.getsize(log_file) > MAX_SIZE / 2 and is_rate_limited:
        if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
            await safe_send(channel, "���񂾂���A�ߋ��̋L�����y���������Ă�̂��c�����҂��Ăق����̂���I")
        with open(log_file, "r", encoding="utf-8") as f:
            new_logs = f.read()
        try:
            summary = summarizer_fallback(f"�ȉ��̃��O�𓌖k�قŊȌ��ɗv�񂵂āF\n{new_logs}", max_length=100, do_sample=True)[0]['generated_text']
            if os.path.exists(temp_summary_file):
                with open(temp_summary_file, "r", encoding="utf-8") as f:
                    old_summary = f.read()
                summary = old_summary + "\n" + summary
            with open(temp_summary_file, "w", encoding="utf-8") as f:
                f.write(summary)
            open(log_file, "w").close()
            if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
                await safe_send(channel, "���񂾂���A�L�����y�����������̂��I����ŏ����X�b�L�������̂���I")
        except Exception as e:
            error_msg = f"{datetime.datetime.now()} | �G���[: {str(e)}\n{traceback.format_exc()}\n"
            with open("error_logs.txt", "a", encoding="utf-8") as f:
                f.write(error_msg)
            if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
                await safe_send(channel, "���񂾂���A������ƃ~�X����������̂��c24���ԑ҂��Ă��瑱��������̂���I")

# ���b�Z�[�W����
@bot.event
async def on_message(message):
    if message.author == bot.user or message.channel.id != CHANNEL_ID:
        return

    await save_logs(message.channel)
    await manage_summary(message.channel)
    await manage_temporary_summary(message.channel)

    if message.content.startswith("���񂾂���"):
        question = message.content.replace("���񂾂���", "").strip()
        if not question:
            await safe_send(message.channel, "���񂾂���A���𕷂������̂��H������x�����Ăق����̂���I")
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
            error_msg = f"{datetime.datetime.now()} | �G���[: {str(e)}\n{traceback.format_exc()}\n"
            with open("error_logs.txt", "a", encoding="utf-8") as f:
                f.write(error_msg)
            if hasattr(bot, 'notify_enabled') and bot.notify_enabled is not False:
                await safe_send(message.channel, "���񂾂���A�T�[�o�[����ꂿ������̂��c24���ԑ҂��Ă��瑱��������̂���I")
        finally:
            await processing_queue.get()
            await processing_queue.task_done()

# �ʒm�ݒ�R�}���h
@bot.command(name="zunda")
async def zunda_command(ctx, action=None):
    if action == "notify":
        if ctx.message.content.split()[-1].lower() == "off":
            bot.notify_enabled = False
            await safe_send(ctx.channel, "���񂾂���A�ʒm���I�t�ɂ����̂��I�Â��ɂ���̂���I")
        elif ctx.message.content.split()[-1].lower() == "on":
            bot.notify_enabled = True
            await safe_send(ctx.channel, "���񂾂���A�ʒm���I���ɂ����̂��I���C�ɓ�����̂���I")
        else:
            await safe_send(ctx.channel, "���񂾂���A�u!zunda notify on�v���u!zunda notify off�v�Őݒ�ł���̂���I")
    elif action == "start":
        await safe_send(ctx.channel, "���񂾂���A�N�������̂��I�u���񂾂���v�ƌĂт����Ă�����ׂ肵�悤�ˁI")
    else:
        await safe_send(ctx.channel, "���񂾂���A�u!zunda start�v�܂��́u!zunda notify on/off�v�ő���ł���̂���I")

# �{�b�g�̋N��
if __name__ == "__main__":
    if not all([TOKEN, CHANNEL_ID, DEEPSEEK_API_KEY]):
        raise ValueError("���ϐ��iTOKEN, CHANNEL_ID, DEEPSEEK_API_KEY�j���ݒ肳��Ă��Ȃ��̂��IReplit��Secrets�Őݒ肵�Ăق����̂���I")
    bot.run(TOKEN)