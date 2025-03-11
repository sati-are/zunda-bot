# ずんだもんBot セットアップとテスト手順

## 準備するもの
- インターネット接続、パソコン、Discordアカウント、Replitアカウント。

## セットアップ手順
1. **Replitアカウントを作成**:
   - [https://replit.com](https://replit.com) にアクセスし、無料登録。
   - メールアドレスまたはGoogleアカウントでログイン。

2. **Replitプロジェクトを作成**:
   - Replitダッシュボードで「+ New Repl」をクリック。
   - 言語を「Python」に設定し、名前を「zunda-bot」と入力。
   - テンプレートは「Blank Repl」を選択。

3. **コードを追加**:
   - `main.py`に`zunda_bot.py`の内容をコピー＆ペースト。
   - コードは[GitHubリポジトリ](https://github.com/yourusername/zunda-bot)からダウンロード可能。

4. **依存ライブラリをインストール**:
   - Replitのシェル（右下の「Shell」タブ）で以下を実行：
     ```
     pip install discord.py openrouter transformers tiktoken bitsandbytes
     ```
   - インストールが完了するまで数分かかる場合がある。

5. **環境変数を設定**:
   - Replitの「Secrets」タブにアクセス（左サイドバーから「Secrets」をクリック）。
   - 以下の環境変数を追加：
     - `TOKEN`: Discord Botのトークン（後述の「Discord Botトークンの取得」で取得）。
     - `CHANNEL_ID`: ずんだもんBotを利用したいDiscordチャンネルのID（後述の「チャンネルIDの取得」で取得）。
     - `DEEPSEEK_API_KEY`: DeepSeek R1のAPIキー（[DeepSeek公式サイト](https://deepseek.com)から取得）。
   - 各値を入力し、「Add New Secret」をクリック。

6. **コードを実行**:
   - Replitの「Run」ボタンをクリックして、ずんだもんBotを起動。
   - コンソールに「Bot is ready!」またはエラーメッセージが表示される。

## Discord Botトークンの取得
1. **Discord Developer Portalにアクセス**:
   - [Discord Developer Portal](https://discord.com/developers/applications) にログイン。
   - 「New Application」をクリックし、アプリケーション名（例: 「ZundaBot」）を入力。

2. **Botを作成**:
   - アプリケーションページで「Bot」をクリック。
   - 「Add Bot」をクリックし、「Yes, do it!」で確認。
   - Botのトークンを表示（「Reset Token」で新しいトークンを生成可能）。
   - トークンをコピーし、ReplitのSecretsで`TOKEN`に設定（トークンは他人に公開しないでください）。

3. **Botをサーバーに招待**:
   - アプリケーションページの「OAuth2」→「URL Generator」をクリック。
   - 「Bot」スコープと「Send Messages」「Read Message History」の権限を選択。
   - 生成されたURLをコピーし、ブラウザで開いてBotをDiscordサーバーに招待。
   - 特定チャンネル（`CHANNEL_ID`で指定）にBotを追加。

## チャンネルIDの取得
1. Discordサーバーの右クリックメニューから「サーバー設定」→「ウィジェット」を開く。
2. チャンネル名を右クリックし、「コピーID」を選択（デベロッパーモードを有効にする必要あり）。
3. コピーしたIDをReplitのSecretsで`CHANNEL_ID`に整数形式で設定。

## Discordでの利用方法
1. **Botの起動確認**:
   - Replitで`zunda_bot.py`を実行し、DiscordチャンネルでBotがオンライン（緑の丸印）になっているか確認。
   - コンソールに「Bot is ready!」と表示されれば、正常に起動。

2. **基本的な利用**:
   - 特定チャンネルで`!zunda start`と入力して、ずんだもんBotを起動。
   - 「ずんだもん」とチャットに書いて質問（例: 「ずんだもん、元気？」）。
   - ずんだもんが東北弁で「ぼく、元気いっぱいなのだ！」のように応答。

3. **通知の管理**:
   - 通知がうるさい場合、`!zunda notify off`でオフに。
   - 通知を復元したい場合、`!zunda notify on`でオンに。

4. **フィードバックの送信（オプション）**:
   - 応答に満足できない場合、`!zunda feedback 悪い [コメント]`（例: `!zunda feedback 悪い 語尾が違うのだ`）。
   - 良い応答の場合は、`!zunda feedback 良い [コメント]`（例: `!zunda feedback 良い すごく可愛い応答だったのだ`）。

## テスト手順
- **通常使用（1秒待機）**:
  - `!zunda start`で起動後、「ずんだもん」とチャットに書いて質問（例: 「ずんだもん、元気？」）。
  - 通常は1秒以内に東北弁で応答が返るはず。処理が軽快に動作するか確認。
- **活発な使用（30秒待機）**:
  - 1秒以内に5回以上または1分以内に5回以上質問を送り、レート制限が発動するか確認。
  - 「ぼく、ずんだもん、ちょっと多忙すぎちゃったのだ…1分待ってほしいのだよ！」というメッセージが表示され、30秒待機後応答が返るか確認。
- **通知オプション**:
  - `!zunda notify off`で通知をオフにし、通知メッセージが表示されないか確認。
  - `!zunda notify on`で通知をオンに戻し、通常の通知が復元するか確認。
- **エラーログ確認**:
  - 意図的にエラーを発生（例: APIキーの無効化）し、`error_logs.txt`にタイムスタンプ付きでエラーが記録されているか確認。
- **トークン制限確認**:
  - トークン使用量（7,500トークン/日）を超えるまで質問を繰り返し、「ぼく、ずんだもん、今日は一日中頑張ったから適当に答えるのだ…」というメッセージが表示され、Mixtral 8x7Bで軽量応答が返るか確認。
  - 24時間待機後、通常のDeepSeek R1応答が復元するか確認。

## 注意点
- **Replitの無料枠**:
  - Replit無料枠（CPU、512MB RAM）で動作するため、負荷が高い場合処理が遅延する可能性あり。
- **Discordのレート制限**:
  - 50リクエスト/秒、10,000リクエスト/10分の制限に対応し、コードの`safe_send()`で自動待機（1秒/30秒）。
- **APIキーとトークンの管理**:
  - `TOKEN`と`DEEPSEEK_API_KEY`は安全に管理（Replit Secretsや環境変数を使用）。他人に公開しないでください。
- **トークン制限**:
  - DeepSeek R1の7,500トークン/日制限を超えると、24時間待機が必要。活発な使用には注意。

## トラブルシューティング
- **エラー: 404 Not Found**:
  - DiscordチャンネルIDやBotトークンが正しいか確認。ReplitのSecretsを再確認。
- **エラー: 429 Too Many Requests**:
  - レート制限が発動しているため、1分待機後再試行。コードの`safe_send()`で自動対応済み。
- **エラー: APIキーが無効**:
  - DeepSeek APIキーが正しいか確認。Replit Secretsを更新。
- **エラー: メモリ不足**:
  - Replit無料枠のメモリ（512MB）を超えた場合、ログサイズを減らす（`MAX_SIZE`を調整）。

## ライセンス
MITライセンス（変更可能）。
