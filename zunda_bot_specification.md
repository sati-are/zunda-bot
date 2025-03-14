# ずんだもんBot 仕様書

## 1. 概要
- **名前**: Zunda-Bot（ずんだもんBot）
- **目的**: Discord上で、東北弁で可愛く、元気いっぱいに応答するAIチャットBotを開発します。DeepSeek R1で推論、Hugging FaceのMixtral 8x7Bで応答を生成し、Replit無料枠（512MB RAM、CPU性能制限）で動作します。
- **特徴**:
  - 東北弁で「ぼく」を一人称とし、語尾を「～のだ」または「～なのだ」に統一して話します。
  - ログを20KBごとにDeepSeek R1で要約し、10KBごとにMixtral 8x7Bで仮要約します。
  - トークン使用量を7,500トークン/日（DeepSeek R1制限）に管理し、レート制限対応を備えています。
  - 脳みそリセット機能（`!zunda reset`）で過去の記憶をクリアし、軽量化を図ります。

## 2. 技術的要件
### 2.1 プラットフォーム
- **ホスティング**: Replit（無料枠、512MB RAM、CPU性能制限）
- **言語**: Python 3.8
- **依存ライブラリ**:
  - `discord.py`: Discord Bot用
  - `openrouter`: DeepSeek R1 API用
  - `tiktoken`: トークンカウント用（OpenAI `cl100k_base`）
  - `requests`: Hugging Face API用
  - `python-dotenv`: 環境変数管理用

### 2.2 API
- **DeepSeek R1**:
  - 推論モデル（`deepseek/deepseek-r1`）を使用し、`max_tokens=1`で`reasoning_content`のみ取得します。
  - トークン上限: 7,500トークン/日（UTC 0:00にリセット）
  - タイムアウト: 60秒
- **Hugging Face**:
  - Mixtral 8x7Bモデルで応答生成（`max_length=130`または`2000`、`temperature=0.7`、`top_p=0.9`）
  - タイムアウト: 15秒

### 2.3 制約
- **Replit無料枠**:
  - 512MB RAM、CPU性能制限を考慮し、同時リクエストを3件に制限（`asyncio.Queue(maxsize=3)`）します。
  - ログサイズ: 20KB（DeepSeek R1要約）、10KB（Mixtral仮要約）
- **Discordレート制限**:
  - 1秒に5回、1分に5回送信制限（超過時30秒待機）
- **DeepSeek R1レート制限**:
  - 7,500トークン/日超過で`is_rate_limited=True`となり、Mixtral 8x7Bの仮要約に切り替えます。

## 3. 機能仕様
### 3.1 基本機能
- **起動**: `!zunda start`で起動し、「起動したのだ！」と通知します。
- **応答**:
  - 「ずんだもん」と呼びかけると、質問に応答します。モードは以下です：
    - 通常モード（`max_tokens=130`）: 簡潔な回答
    - 長文モード（「長文」「詳細」「詳しく」指定、`max_tokens=2000`）: 詳細な回答
  - 東北弁で「ぼく」を一人称とし、語尾を「～のだ」または「～なのだ」に統一します。
- **ログ管理**:
  - `all_logs.txt`にチャットログを保存（タイムスタンプ、チャンネルID、メッセージ）
  - 20KBごとに`latest_summary.txt`でDeepSeek R1要約、10KBごとに`temporary_summary.txt`でMixtral 8x7B仮要約します。

### 3.2 通知設定
- **コマンド**: `!zunda notify on/off`
  - `on`: 通知を有効（デフォルト）
  - `off`: 通知を無効
  - 通知例:
    - 起動: 「起動したのだ！」
    - 要約: 「記憶を整理したのだ！」「記憶を軽く整理したのだ！」

### 3.3 脳みそリセット機能（`!zunda reset`）
- **目的**: 過去のチャットログと要約データをクリアし、メモリ/ディスク使用量を軽減します。
- **動作**:
  1. ユーザーに確認を求める: 「脳みそをリセットすると過去の記憶が全部消えるのだ…本当にいいのだか？「yes」か「no」で答えてほしいのだ！」
  2. 30秒以内に「yes」または「no」を待機
  3. 「yes」の場合:
     - `all_logs.txt`、`latest_summary.txt`、`temporary_summary.txt`を空ファイルにクリア
     - `bot.first_summary = True`にリセット（次回要約時に「過去の記憶がおぼろげになったのだ…」を表示）
     - 通知（有効時）: 「脳みそが空っぽになっちゃったのだ…新しくおしゃべりしようね！」
  4. 「no」またはタイムアウトの場合:
     - リセットをキャンセル
     - 通知（有効時）: 「リセットをキャンセルしたのだ！これからも楽しくおしゃべりしようね！」
- **削除されない内容**:
  - 環境変数（`TOKEN`、`CHANNEL_ID`、`DEEPSEEK_API_KEY`、`HF_API_KEY`）
  - プログラムコードや依存ライブラリ
  - チャンネル設定（`CHANNEL_ID`）
  - 送信回数トラッキング（`send_count`）
  - トークン使用量（`used_tokens`）やレート制限状態（`is_rate_limited`）（リセットしない仕様）

### 3.4 仮要約（`temporary_summary.txt`）の管理
- **累積確認**: `temporary_summary.txt`は、Mixtral 8x7Bで10KBごとに仮要約を保存し、累積する可能性があります。
- **使用後の初期化**: 仮要約が使用（応答生成に含まれる）後、`temporary_summary.txt`を空ファイル（0バイト）にクリアします。これにより、累積によるデータ重複やメモリ増加を防ぎます。

## 4. 通知メッセージのルール
- すべての通知メッセージは「～のだ」または「～なのだ」で終わる必要があります。「～のだよ」や「ぼく、ずんだもん」は使用しません。
- 必要に応じて「ずんだもん」を文頭に配置可能ですが、省略も可能です（例: 「起動したのだ！」）。

## 5. パフォーマンスとスケーラビリティ
- **ログサイズ管理**: `all_logs.txt`を20KB、`latest_summary.txt`に要約、`temporary_summary.txt`を適宜クリアし、Replitの512MB RAMを最適化します。
- **トークン管理**: DeepSeek R1の7,500トークン/日を`used_tokens`で追跡し、超過時に`is_rate_limited`を切り替えます。脳みそリセットではトークン/レート制限をリセットしません。
- **同時リクエスト**: `asyncio.Queue(maxsize=3)`で3件の同時リクエストを制限し、CPU負荷を軽減します。

## 6. 関連リンク
- **DeepSeek R1 API Docs**: [https://deepseek.com/docs]（https://deepseek.com/docs）
- **Discord.py Docs**: [https://discordpy.readthedocs.io]（https://discordpy.readthedocs.io）
- **Hugging Face Transformers**: [https://huggingface.co/docs/transformers]（https://huggingface.co/docs/transformers）
- **Tiktoken**: [https://github.com/openai/tiktoken]（https://github.com/openai/tiktoken）

## 7. ライセンス
- MITライセンスに基づくオープンソースプロジェクトです。

## 8. 処理のフローチャート
-
-
-+-------------------+
-|  Discord          |
-| "ずんだもん元気?" |
-+-------------------+
-         | (質問データ)
-         v
-+-------------------+       +-------------------+
-|  Replit           | ----> |  DeepSeek R1      |
-| - 質問受信        |       | - 推論取得        |
-| - (Python処理)    | <---- |  (max_tokens=1)   |
-+-------------------+       +-------------------+
-         | (推論: reasoning_content)
-         v
-+-------------------+
-|  Replit           |
-| - 推論処理        |
-| - (Python処理)    |
-+-------------------+
-         | (推論+質問)
-         v
-+-------------------+
-|  Hugging Face API  |
-| - Mixtral 8x7B応答生成 |
-|   (max_length=130) |
-+-------------------+
-         | (東北弁応答)
-         v
-+-------------------+
-|  Discord           |
-| "元気なのだ！"     |
-+-------------------+
