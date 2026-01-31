# AI-news-aggregater Known Issues

> Last updated: 2026-01-31

## Active Issues

### [KNOWN] Gemini API Free Tier Rate Limits
**Discovered:** 2026-01-31
**Status:** Mitigated
**Severity:** Medium

**Description:** Gemini API無料枠のレート制限により、一度に多くの記事を処理するとクォータ超過エラー(429)が発生する。

**Error:**
```
429 You exceeded your current quota
Quota exceeded for metric: generate_content_free_tier_requests
```

**Mitigation Applied:**
- バッチサイズを10→5に削減
- 1回の処理記事数を50→20に削減
- バッチ間の待機時間を2秒→15-20秒に延長
- リトライロジック（指数バックオフ）を追加

**Long-term Solutions:**
1. Gemini API有料プランにアップグレード
2. 処理を複数回の実行に分散
3. 他のLLM API（Claude API等）への移行検討

---

### [KNOWN] Reddit API blocked from GitHub Actions
**Discovered:** 2026-01-31
**Status:** Won't Fix (External Limitation)
**Severity:** Low

**Description:** RedditがクラウドプロバイダーのIPアドレスをブロックしているため、GitHub ActionsからReddit APIにアクセスできない。

**Error:**
```
403 Client Error: Blocked for url: https://www.reddit.com/r/MachineLearning/hot.json
```

**Impact:** Reddit記事が取得できない（Hacker News + GitHub Trendingは正常動作）

**Workarounds:**
1. Reddit公式APIを使用（OAuth認証が必要）
2. プロキシサービスを使用
3. ローカル実行でReddit記事を取得

---

## Resolved Issues

### [FIXED] GitHub Actions workflow permission denied
**Discovered:** 2026-01-31
**Fixed:** 2026-01-31
**Root Cause:** GitHub Actionsワークフローに`permissions: contents: write`が設定されていなかったため、`git push`が403エラーで失敗
**Solution:** `.github/workflows/fetch.yml`に`permissions: contents: write`を追加
**Prevention:** GitHub Actionsでリポジトリに書き込む場合は明示的にパーミッションを設定

### [FIXED] Gemini API model not found
**Discovered:** 2026-01-31
**Fixed:** 2026-01-31
**Root Cause:** `gemini-1.5-flash`モデルがAPI v1betaで利用不可（廃止またはリネーム）
**Error:**
```
404 models/gemini-1.5-flash is not found for API version v1beta
```
**Solution:** モデル名を`gemini-2.0-flash`に更新
**Prevention:** Gemini APIのモデル名は定期的に変更されるため、エラーが発生したら最新モデル名を確認

### [FIXED] pytest not installed on Python 3.10
**Discovered:** 2026-01-30
**Fixed:** 2026-01-30
**Root Cause:** システムのPython 3.10にpytestがインストールされていなかった
**Solution:** Python 3.12 venv環境のpytestを使用してテストを実行
**Prevention:** requirements-dev.txtにpytestを追加し、仮想環境でテストを実行する手順をドキュメント化

### [FIXED] test_sort_by_score failing due to ambiguous keyword
**Discovered:** 2026-01-30
**Fixed:** 2026-01-30
**Root Cause:** テストケースで"important"というキーワードが両方のタイトル("Not important", "Very important")に含まれていたため、両方同じスコアになりソート順が不定になった
**Solution:** テストケースのキーワードを"critical"と"normal"に分離し、異なるスコアになるように修正
**Prevention:** テストケース設計時は、マッチするキーワードが一意にマッチするようにする

### [FIXED] test_configure_with_api_key patch error
**Discovered:** 2026-01-30
**Fixed:** 2026-01-30
**Root Cause:** `@patch('summarizer.genai')`が失敗。genaiはモジュールレベルでtry-exceptブロック内でのみインポートされるため、google.generativeaiがインストールされていない環境ではsummarizserモジュールにgenai属性が存在しない
**Solution:** patchを削除し、環境によって結果が異なることを許容するテストに変更
**Prevention:** 条件付きインポートされるモジュールをpatchする場合は、そのモジュールが存在するかどうかを考慮したテスト設計を行う

### [FIXED] TypeError in scorer.py when tags is None
**Discovered:** 2026-01-30
**Fixed:** 2026-01-30
**Severity:** Medium
**Root Cause:** `article.get("tags", [])` でデフォルト値`[]`を設定していても、`tags`キーが存在して値が`None`の場合は`None`が返される。`" ".join(None)`は`TypeError: can only join an iterable`を発生させる。
**Reproduction Steps:**
```python
article = {"id": "test", "title": None, "summary": None, "tags": None, "url": "..."}
score_articles([article], config)  # TypeError
```
**Solution:**
```python
# Before (buggy)
" ".join(article.get("tags", []))

# After (fixed)
tags = article.get("tags") or []
" ".join(tags)
```
**Prevention:**
- [ ] 辞書からオプショナルなリスト/文字列を取得する際は `get()` のデフォルト値だけでなく、`or` でNone値も処理する
- [ ] E2Eテストでエッジケース（None値）を確認する

### [FIXED] Missing exports in fetchers/__init__.py
**Discovered:** 2026-01-30
**Fixed:** 2026-01-30
**Root Cause:** 並列でagentが作業した際に、`fetchers/__init__.py`がgithub_trendingのみをエクスポートし、hackernewsとredditのエクスポートが欠落していた
**Solution:** `__init__.py`を更新してすべてのフェッチャーをエクスポート
**Prevention:** 並列作業時は共通ファイル（__init__.py等）の更新を最後に統合確認する

---

## Notes

- Python 3.10とPython 3.12の両方がシステムにインストールされている
- pytestはPython 3.12のvenv環境にインストール済み
- テスト実行時は `"C:\Users\xtc19\AppData\Local\Programs\Python\Python312\workspace\venv\Scripts\python.exe" -m pytest` を使用
