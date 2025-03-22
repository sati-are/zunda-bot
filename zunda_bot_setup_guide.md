# ずんだもんBot セットアップとテスト手順

## 1. 準備するもの
- インターネット接続
- パソコン（どのOSでもOK）
- Discordアカウント（[discord.com](https://discord.com)から無料登録）
- Replitアカウント（[replit.com](https://replit.com)からメールまたはGoogleアカウントで無料登録）

## 2. Replitでのセットアップ
### 2.1 Replitアカウントを作成
- [Replit公式サイト](https://replit.com) にアクセスし、「Sign Up」で無料登録。
   - メールアドレスまたはGoogleアカウントでログイン。

### 2.2 Replitプロジェクトを作成
- Replitダッシュボードで「Apps」-「+ New Repl」をクリック。
- **「choose a Template」タブを選択。
- **Template**: 「Python」を選択。
- **Title**: 「zunda-bot」と入力。

- 「Create Repl」をクリック。

### 2.3 コードをGitHubから追加
- GitHubリポジトリ（[https://github.com/sati-are/zunda-bot](https://github.com/sati-are/zunda-bot)）にアクセス。
- `zunda-bot.py`（ずんだもんBotのコード）をダウンロード。
- Replitのプロジェクト画面で、左サイドバーの「Files」タブを開く。
- Replitのエディタに`zunda-bot`をドラッグ＆ドロップまたはコピー＆ペーストで追加。

### 2.4 依存ライブラリをインストール
- Replitのシェル（右下「Shell」タブ）で以下を実行：

  pip install discord.py openrouter tiktoken requests python-dotenv

### 2.5 環境変数を設定
- Replitの「Secrets」タブ（左サイドバー）をクリック。
- 以下の環境変数を追加：
- `TOKEN`: Discord Botのトークン（後で取得）
- `CHANNEL_ID`: チャンネルID（後で取得）
- `DEEPSEEK_API_KEY`: DeepSeek APIキー（[DeepSeek公式サイト](https://deepseek.com)から取得）
- `HF_API_KEY`: Hugging Face APIキー（[Hugging Face Settings](https://huggingface.co/settings/tokens)から取得）
- 値を入力して「Add New Secret」をクリック。

## 3. Discord Botの設定
### 3.1 Discord Developer PortalでBotを作成
- [Discord Developer Portal](https://discord.com/developers/applications) にログイン。
- 「New Application」をクリックし、名前（例: 「ZundaBot」）を入力。
- 「Bot」タブで「Add Bot」をクリック。「Yes, do it!」で確認。
- Botトークンを表示し、Replitの`TOKEN`に設定（他人に公開しないでください）。

### 3.2 BotをDiscordサーバーに招待
- 「OAuth2」→「URL Generator」をクリック。
- 「Bot」スコープと「Send Messages」「Read Message History」の権限を選択。
- 生成されたURLをコピーし、ブラウザで開いてBotをサーバーに招待。

### 3.3 チャンネルIDの取得
- Discordで、Botを使いたいチャンネルに移動。
- チャンネル名を右クリックし、「コピーID」（デベロッパーモードをオンに必要）。
- デベロッパーモードの有効化: 「ユーザー設定」→「外観」→「デベロッパーモード」をオン。
- コピーしたIDをReplitの`CHANNEL_ID`に整数形式で設定。

## 4. コードの実行とテスト
- Replitの「Run」ボタンをクリックしてBotを起動。
- DiscordでBotが緑の丸（オンライン）になり、「!zunda start」で起動。
- 質問（例: 「ずんだもん、元気？」）を送り、東北弁の応答が返るか確認。
- 長文モード（「ずんだもん、宇宙について詳しく教えて！」）で「続きがあるので…」が付くかチェック。

## 5. 注意点
- Replit無料枠（CPU、512MB RAM）で動作。APIリクエストが遅延する可能性あり。
- `TOKEN`やAPIキーは他人に教えないでください。
- DeepSeek R1は7,500トークン/日制限あり、超えると軽量応答になるよ。

## 6. トラブルシューティング
## トラブルシューティング
- **Botが起動しない**:
  Replitの「Run」ボタンを押しても「Bot is ready!」が出ない場合、環境変数（Secrets）を確認して、APIキーが正しいかチェック。
  DiscordでBotがオンラインにならない場合、チャンネルIDやBotトークンが間違ってる可能性があるから、設定を見直して。

- **応答が遅いまたはエラー**:
  「サーバーが疲れちゃった…」が出たら、1分待ってから再試行。インターネット接続やAPIの制限を確認。
  error_logs.txtにエラーが記録されてるから、内容を開発者に相談してね。

- **レート制限に引っかかる**:
  1秒に5回以上質問すると「多忙すぎちゃった…」が出るから、30秒待ってから再試行してね。


## ライセンス
MITライセンス（変更可能）。
