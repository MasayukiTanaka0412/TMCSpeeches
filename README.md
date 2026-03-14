# TMCSpeeches Archive

## 1. プロジェクト概要
Toastmasters のスピーチ原稿（`.md` / `.txt` / `.pdf` / `.pptx` / `.docx`）を一覧化し、`articles.csv` をデータソースとして Medium 風の読みやすい静的サイトで閲覧するプロジェクトです。

## 2. サイトの目的
- 原稿の一覧性を高める
- タイトル・概要・タグ・更新日で探索しやすくする
- GitHub Pages でそのまま公開できる軽量構成にする

## 3. GitHub Pages での公開方法
1. リポジトリに `index.html` と `articles.csv` を配置（本リポジトリは配置済み）。
2. GitHub の **Settings > Pages** で公開ブランチを選択。
3. ルートディレクトリ（`/`）を公開対象にすれば、そのまま表示されます。

## 4. ディレクトリ構造

```text
.
├─ index.html
├─ articles.csv
├─ generate_articles_csv.py
├─ README.md
└─ (speech files: .md / .txt / .pdf / .pptx / .docx)
```

## 5. `articles.csv` の仕様
ヘッダー付き UTF-8 CSV。

| 列名 | 説明 |
|---|---|
| `title` | 記事タイトル |
| `summary` | 本文先頭から切り出した概要（最大約200文字） |
| `tags` | タグ（カンマ区切り or セミコロン区切り） |
| `filename` | GitHub Pages で参照可能な相対パス |
| `lastModified` | ファイル最終更新日時（文字列） |

## 6. 新しい記事を追加する方法
1. ルートまたは配下ディレクトリに対象ファイルを追加。
2. 次のコマンドで `articles.csv` を再生成。

```bash
python3 generate_articles_csv.py
```

3. 生成された `articles.csv` をコミットして GitHub Pages に反映。

## 7. 対応ファイル形式
- `.md`
- `.txt`
- `.pdf`
- `.pptx`
- `.docx`

## 8. 使用ライブラリ
### 生成スクリプト（Python）
- `PyPDF2`（PDF テキスト抽出）

> `.docx` / `.pptx` は ZIP(XML) を標準ライブラリで解析するため、追加依存は不要です。

### フロントエンド（CDN）
- `Papa Parse`（CSV パース）
- `marked`（Markdown を HTML 化）
- `DOMPurify`（HTML サニタイズ）
- `Google Fonts`（Inter / Merriweather）

## 9. `articles.csv` の再生成方法

```bash
python3 generate_articles_csv.py
```

- 隠しディレクトリ、`.git`、`node_modules`、`venv`、`.venv`、`dist`、`build` は除外します。
- 解析失敗時はフォールバック（`title=ファイル名`, `summary=""`, `tags=""`）で安全に継続します。

## 10. `.md` / `.txt` のメタデータ記法
先頭に次の形式を置くと最優先で採用されます（空行で終了）。

```text
title: My Speech
summary: My first Toastmasters speech
tags: toastmasters,intro,speech

本文...
```

メタデータがない場合は、最初の見出しまたは最初の意味のある行を `title` として採用します。

## 11. `.pdf` / `.pptx` / `.docx` からの抽出ルール
- `.docx`: 最初の意味のある段落を `title`、全文先頭を `summary`。
- `.pptx`: 先頭スライドのタイトル相当テキストを優先して `title`、全スライド本文先頭を `summary`。
- `.pdf`: 抽出テキストの最初の意味のある1行を `title`、本文先頭を `summary`。

いずれも `summary` は改行・連続空白を整形し、最大約200文字に切り詰めます。
