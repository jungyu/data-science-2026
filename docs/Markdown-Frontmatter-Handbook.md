# 🧠 Head First Markdown + Frontmatter 學習手冊
### 寫文件、建網站、做筆記——一套語法走天下！

> 📖 **參考來源**：[Markdown Guide](https://www.markdownguide.org/)

---

## 這本手冊適合誰？

✅ 第一次聽到 Markdown，不知道 `**粗體**` 和 `__粗體__` 差在哪的人
✅ 在 GitHub、Notion、Obsidian、Hugo 寫文件的人
✅ 想搞懂文章頂端那一段 `---` 包住的神祕內容（Frontmatter）
✅ 想讓自己的 .md 檔案被靜態網站生成器（Jekyll / Hugo）正確讀取的人

---

# 第一章：Markdown 是什麼？你已經在用它了

---

## 🧩 先想一個問題

你在 GitHub 上看到的 README，那些**粗體**、`程式碼`、整齊的表格——

它的原始檔案長這樣：

```
## 安裝方式

**步驟一**：安裝依賴套件

```bash
pip install my-package
```

這樣寫，GitHub 就會自動幫你渲染成漂亮的格式。
這就是 **Markdown**。
```

---

## 💡 核心概念：Markdown 是「帶格式的純文字」

```
你寫的                        你看到的
──────────────              ──────────────────
# 大標題                    【大標題】（h1 大字）
**粗體文字**                 粗體文字
- 項目一                     • 項目一
- 項目二                     • 項目二
[點我](https://...)          點我（可點擊連結）
```

> 💬 **John Gruber（Markdown 發明者，2004）**：
> "Markdown 格式化的文件，就算不渲染，讀純文字也應該讓人覺得自然。"

---

## 🌍 Markdown 能用在哪裡？

| 用途 | 工具/平台 |
|------|-----------|
| 網站/部落格 | Jekyll、Hugo、Gatsby、WordPress |
| 文件系統 | MkDocs、Docusaurus、Read the Docs |
| 筆記 | Obsidian、Notion、Bear、Joplin |
| 簡報 | Marp、Remark、Deckset |
| 電子書 | Leanpub（轉 PDF/EPUB） |
| 協作 | GitHub、GitLab、Slack、Discord |
| Email | Markdown Here（瀏覽器擴充套件） |

---

## 🔄 Markdown 的運作流程

```
你寫的 .md 檔
      │
      ▼
Markdown 解析器（Parser）
（pandoc / marked / goldmark / kramdown）
      │
      ▼
HTML 檔案 → 瀏覽器顯示
      │
      ▼
也可以匯出成 PDF / EPUB / Word
```

---

## ⚠️ Markdown 有不同「口味」（Flavors）！

```
CommonMark       → 標準規格，最通用
GitHub Flavored  → GitHub 用，多了 Task List、表格
Markdown Extra   → 多了 Definition List、Footnotes
MultiMarkdown    → 學術用途，多了 Citation
```

> 🔥 本手冊以 **CommonMark + GitHub Flavored** 為主，99% 的平台都支援。

---

## 🧠 Brain Power

> Markdown 和 HTML 的關係是什麼？
> 如果你已經會 HTML，為什麼還要學 Markdown？

---

# 第二章：標題、段落、換行——最基本的三樣

---

## 📌 標題：用 `#` 的數量決定層級

```markdown
# 一級標題（最大）
## 二級標題
### 三級標題
#### 四級標題
##### 五級標題
###### 六級標題（最小）
```

**渲染後：**

> # 一級標題
> ## 二級標題
> ### 三級標題

---

## 📋 標題語法對照表

| Markdown | HTML 等同 | 用途 |
|----------|-----------|------|
| `# 標題` | `<h1>` | 頁面主標題（通常只用一次） |
| `## 標題` | `<h2>` | 章節大標 |
| `### 標題` | `<h3>` | 節次小標 |
| `#### 標題` | `<h4>` | 小節 |

---

## ⚠️ 三個標題陷阱

```markdown
❌ 錯誤：#沒有空格的標題
✅ 正確：# 有空格的標題

❌ 錯誤：沒有空行就接著內文
# 標題
這段文字緊接著標題

✅ 正確：標題前後要空行

# 標題

這段文字在空行後面
```

---

## 📌 段落：空一行就是新段落

```markdown
這是第一段。這段裡面的文字
即使在原始檔換行，
渲染後還是同一段。

這是第二段，因為上面空了一行。
```

**渲染後：**
> 這是第一段。這段裡面的文字即使在原始檔換行，渲染後還是同一段。
>
> 這是第二段，因為上面空了一行。

---

## 📌 換行：行尾加兩個空格

```markdown
第一行（後面有兩個空格）
第二行（這行會換行顯示）

第一行（沒有空格）
第二行（這行不會換行，會接在第一行後面）
```

> 💡 **小技巧**：記不住兩個空格？直接用 HTML 標籤 `<br>` 也可以。

---

# 第三章：強調語法——粗體、斜體、刪除線

---

## 📋 強調語法對照表

| 效果 | 寫法 | 結果 |
|------|------|------|
| 粗體 | `**文字**` 或 `__文字__` | **文字** |
| 斜體 | `*文字*` 或 `_文字_` | *文字* |
| 粗體＋斜體 | `***文字***` | ***文字*** |
| 刪除線 | `~~文字~~` | ~~文字~~ |
| 螢光標記 | `==文字==` | ==文字==（需支援） |

---

## 🔬 動手試試看

```markdown
這個句子有 **非常重要** 的部分。

這是 *義大利斜體* 風格的文字。

我們 ***既粗體又斜體*** 地強調這段話。

~~過時的資訊~~ 已經不適用了。

請注意 ==這個關鍵概念==。
```

---

## ⚠️ 底線 vs 星號的陷阱

```markdown
✅ 在句子中間用星號：un**frigging**believable
❌ 底線在中間不一定有效：un__frigging__believable

原則：
- 段落開頭和結尾的強調，兩種都可以
- 字詞中間的強調，一律用星號 *
```

---

## 🧠 Brain Power

> `**粗體**` 和 `__粗體__` 渲染結果一樣，但哪一個更「安全」？
> 提示：想想中文和英文混排的情況。

---

# 第四章：清單——有序、無序、任務清單

---

## 📌 無序清單：用 `-`、`*`、`+`

```markdown
- 第一項
- 第二項
  - 縮排子項目（用兩個空格或 Tab）
  - 另一個子項目
- 第三項
```

**渲染後：**
> - 第一項
> - 第二項
>   - 縮排子項目
>   - 另一個子項目
> - 第三項

---

## 📌 有序清單：用數字加點

```markdown
1. 第一步
2. 第二步
3. 第三步
   1. 子步驟 A
   2. 子步驟 B
4. 第四步
```

> 🔥 **秘密**：數字不需要連續！Markdown 會自動排序。
> ```markdown
> 1. 第一項
> 1. 第二項（數字都是 1 也沒關係）
> 1. 第三項
> ```
> 渲染後還是 1、2、3。

---

## 📌 任務清單（GitHub Flavored Markdown）

```markdown
- [x] 完成需求分析
- [x] 設計資料庫結構
- [ ] 撰寫 API 文件
- [ ] 部署到正式環境
```

**渲染後（可點擊的 checkbox）：**
> - [x] 完成需求分析
> - [x] 設計資料庫結構
> - [ ] 撰寫 API 文件
> - [ ] 部署到正式環境

---

## 🎯 清單裡放其他元素

```markdown
- 第一項

  這段文字屬於第一項（縮排 2 空格）

- 第二項

  > 這是第二項裡的引用區塊

- 第三項

  ```python
  # 這是第三項裡的程式碼
  print("Hello")
  ```
```

---

## ⚠️ 清單常見陷阱

```markdown
❌ 不要在同一個清單混用不同符號
- 項目一
* 項目二    ← 可能產生新的清單
+ 項目三    ← 可能再產生一個新清單

✅ 保持一致，全用 -
- 項目一
- 項目二
- 項目三
```

---

# 第五章：連結與圖片——超連結的藝術

---

## 📌 連結的四種寫法

```markdown
# 寫法一：行內連結（最常用）
[顯示文字](https://www.example.com)

# 寫法二：帶 title（滑鼠懸停顯示說明）
[顯示文字](https://www.example.com "這是說明文字")

# 寫法三：裸連結（自動變超連結）
<https://www.example.com>
<user@example.com>

# 寫法四：參考式連結（長文章適用，保持正文整潔）
[顯示文字][ref-id]

[ref-id]: https://www.example.com "可選的說明"
```

---

## 📌 圖片語法

```markdown
# 基本圖片（! 開頭）
![替代文字](image.jpg)

# 帶 title 的圖片
![替代文字](image.jpg "圖片說明")

# 可點擊的圖片（圖片包在連結裡）
[![替代文字](image.jpg)](https://www.example.com)

# 使用絕對路徑
![Logo](https://www.example.com/logo.png)
```

---

## 🔬 動手試試看：參考式連結的好處

```markdown
# 沒有參考式：正文很難讀
請參考 [Markdown 基礎語法](https://www.markdownguide.org/basic-syntax/ "Markdown Basic Syntax") 和
[進階語法](https://www.markdownguide.org/extended-syntax/ "Markdown Extended Syntax")。

# 有參考式：正文清爽，參考在文末集中管理
請參考 [Markdown 基礎語法][basic] 和 [進階語法][extended]。

[basic]: https://www.markdownguide.org/basic-syntax/ "Markdown Basic Syntax"
[extended]: https://www.markdownguide.org/extended-syntax/ "Markdown Extended Syntax"
```

---

# 第六章：程式碼——開發者的好朋友

---

## 📌 行內程式碼：用反引號包起來

```markdown
執行 `pip install flask` 安裝套件。

函式 `print()` 會輸出文字。
```

> 如果程式碼本身包含反引號，用**雙反引號**包：
> ```markdown
> `` 這裡有 `反引號` 的程式碼 ``
> ```

---

## 📌 程式碼區塊：三個反引號

````markdown
```python
def greet(name):
    print(f"Hello, {name}!")

greet("World")
```
````

**渲染後（有語法高亮）：**
```python
def greet(name):
    print(f"Hello, {name}!")

greet("World")
```

---

## 📋 常見語言識別符

| 語言 | 識別符 |
|------|--------|
| Python | `python` |
| JavaScript | `javascript` 或 `js` |
| TypeScript | `typescript` 或 `ts` |
| Bash/Shell | `bash` 或 `sh` |
| SQL | `sql` |
| JSON | `json` |
| YAML | `yaml` |
| HTML | `html` |
| CSS | `css` |
| Markdown | `markdown` |
| 不指定語言 | 空白（無高亮） |

---

## 📌 縮排式程式碼區塊（舊語法）

```markdown
    # 縮排 4 個空格就是程式碼區塊
    print("這是舊式寫法")
    # 現代推薦用 ``` 取代
```

---

# 第七章：引用、表格、水平線

---

## 📌 引用區塊：用 `>` 開頭

```markdown
> 這是一段引用文字。

> 引用裡面也可以放 **粗體** 和 *斜體*。
>
> 甚至可以多段落。

# 巢狀引用
> 第一層引用
>
>> 第二層引用（再加一個 >）
>
> 回到第一層
```

---

## 📌 表格（Extended Syntax）

```markdown
| 欄位一 | 欄位二 | 欄位三 |
| ------ | ------ | ------ |
| 資料 A | 資料 B | 資料 C |
| 資料 D | 資料 E | 資料 F |
```

**對齊方式：**

```markdown
| 靠左對齊 | 置中對齊 | 靠右對齊 |
| :------- | :------: | -------: |
| 文字靠左 | 文字置中 | 文字靠右 |
| 1        |    2     |        3 |
```

**渲染後：**

| 靠左對齊 | 置中對齊 | 靠右對齊 |
| :------- | :------: | -------: |
| 文字靠左 | 文字置中 | 文字靠右 |
| 1        |    2     |        3 |

---

## ⚠️ 表格限制

```markdown
表格內可以用：連結、行內程式碼、粗體/斜體
表格內不能用：標題、引用、清單、水平線、圖片

如果要在表格裡放 | 符號：
| 欄位 | 說明 |
| ---- | ---- |
| 管道符 | 用 &#124; 代替 \| |
```

---

## 📌 水平分隔線

```markdown
---

***

___
```

三種寫法效果相同，都渲染成 `<hr>` 分隔線。

> ⚠️ **前後要空行**，否則可能被解析成 Setext 標題語法。

---

# 第八章：腳注、定義清單、特殊語法

---

## 📌 腳注（Footnotes）

```markdown
這是一段有腳注的文字[^1]，還有另一個長腳注[^long]。

[^1]: 這是第一個腳注的內容。

[^long]: 這是比較長的腳注。

    可以縮排來加入多段內容。

    `code` 也可以放進腳注。
```

**渲染後：** 文字後面出現上標數字，頁面底部有對應說明。

> ⚠️ 腳注定義**不能放在**清單、引用或表格裡面。

---

## 📌 定義清單（Definition Lists）

```markdown
Markdown
: 一種輕量級標記語言，由 John Gruber 於 2004 年創建。

HTML
: 超文字標記語言，是網頁的骨架。
: 也是 Markdown 渲染的目標格式。
```

**渲染後：**

> **Markdown**
> ：一種輕量級標記語言，由 John Gruber 於 2004 年創建。
>
> **HTML**
> ：超文字標記語言，是網頁的骨架。
> ：也是 Markdown 渲染的目標格式。

---

## 📌 標題 ID（Heading IDs）

```markdown
### 我的自訂標題 {#custom-anchor}
```

可以讓頁面內連結精準跳到這個標題：
```markdown
[跳到自訂標題](#custom-anchor)
```

外部連結：
```
https://example.com/page#custom-anchor
```

---

## 📌 Emoji

```markdown
# 方式一：直接貼入 emoji 字元
今天天氣真好 ☀️ 出去走走吧！

# 方式二：使用 shortcode（支援的平台）
:tada: 恭喜完成任務！
:warning: 注意這個問題
:rocket: 部署成功！
```

---

## 📌 上標與下標

```markdown
H~2~O     → H₂O（下標）
X^2^      → X²（上標）

# HTML 替代方案（所有平台通用）
H<sub>2</sub>O
X<sup>2</sup>
```

---

# 第九章：轉義字元與原始 HTML

---

## 📌 跳脫特殊字元

當你想顯示有特殊意義的符號，在前面加 `\`：

```markdown
\*這不是斜體\*
\# 這不是標題
\[這不是連結\]
\`這不是程式碼\`
```

**可以跳脫的字元：**
```
\ ` * _ { } [ ] < > ( ) # + - . ! |
```

---

## 📌 直接使用 HTML

大部分 Markdown 解析器接受行內 HTML：

```markdown
這是 **Markdown 粗體** 和 <em>HTML 斜體</em> 混用。

使用 HTML 做表格對齊：
<div align="center">

這段文字置中

</div>
```

> ⚠️ **安全注意**：某些平台（如 GitHub）會過濾危險的 HTML 標籤（如 `<script>`）。

---

# 第十章：Frontmatter——文件的「身份證」

---

## 🧩 先想一個問題

你在 Hugo 或 Jekyll 網站看到的文章，每篇都有標題、日期、標籤、作者——

這些資訊從哪裡來？不是從文章內容裡面，而是從 **Frontmatter**。

---

## 💡 什麼是 Frontmatter？

Frontmatter 是 .md 檔案頂端、由 `---` 包住的一段**中繼資料（Metadata）**：

```markdown
---
title: 我的第一篇文章
date: 2024-03-15
author: 王小明
tags: [Python, 資料科學]
draft: false
---

# 正文從這裡開始

這是文章的內容...
```

> 💬 **白話解釋**：Frontmatter 就像書的封面頁，寫了書名、作者、出版日期——
> 這些資訊不是「書的內容」，而是描述這本書的「資料」。

---

## 📋 三種 Frontmatter 格式

### 格式一：YAML（最常用，`---` 包住）

```yaml
---
title: "文章標題"
date: 2024-03-15
author: "作者姓名"
tags:
  - Python
  - 資料科學
draft: false
---
```

### 格式二：TOML（Hugo 常用，`+++` 包住）

```toml
+++
title = "文章標題"
date = 2024-03-15T00:00:00Z
author = "作者姓名"
tags = ["Python", "資料科學"]
draft = false
+++
```

### 格式三：JSON（`{` `}` 包住）

```json
{
  "title": "文章標題",
  "date": "2024-03-15",
  "author": "作者姓名",
  "tags": ["Python", "資料科學"],
  "draft": false
}
```

---

## 📋 YAML Frontmatter 語法速查

```yaml
---
# 字串（有沒有引號都可以）
title: 我的文章
title: "我的文章"

# 數字
weight: 10
priority: 1.5

# 布林值
draft: false
published: true
featured: false

# 日期（ISO 8601 格式）
date: 2024-03-15
lastmod: 2024-03-20T10:30:00+08:00

# 陣列（兩種寫法）
tags: [Python, 資料科學, 爬蟲]
tags:
  - Python
  - 資料科學
  - 爬蟲

# 物件（巢狀結構）
author:
  name: 王小明
  email: wang@example.com
  bio: "資深工程師"

# 多行字串
description: |
  這是第一行。
  這是第二行。
  （| 保留換行）

summary: >
  這是第一行，
  這是第二行。
  （> 把換行變空格，形成一段）

# 空值
thumbnail: null
expires: ~
---
```

---

## 🧠 Brain Power

> YAML 裡的 `|` 和 `>` 都能寫多行字串，差別在哪？
> 想想看：文章摘要適合用哪個？程式碼片段呢？

---

# 第十一章：各平台的 Frontmatter 欄位

---

## 🌐 Jekyll（GitHub Pages）

```yaml
---
layout: post                    # 使用哪個版型
title: "文章標題"
date: 2024-03-15 10:00:00 +0800
categories: [技術, Python]       # 分類（影響 URL）
tags: [爬蟲, 資料科學]
author: wang
excerpt: "文章摘要，顯示在列表頁"
permalink: /2024/my-article/    # 自訂 URL
published: true                 # false = 草稿
image: /assets/img/cover.jpg
---
```

---

## 🚀 Hugo

```yaml
---
title: "文章標題"
date: 2024-03-15T10:00:00+08:00
lastmod: 2024-03-20T00:00:00+08:00
draft: false                    # true = 草稿（build 時略過）
weight: 10                      # 排序權重（數字越小越前面）

# 分類系統
categories: ["技術文章"]
tags: ["Python", "爬蟲"]
series: ["Python 資料科學系列"]

# 顯示設定
description: "文章描述，用於 SEO meta description"
summary: "顯示在文章列表的摘要"
featured_image: "cover.jpg"

# SEO
keywords: ["Python", "爬蟲", "資料科學"]
slug: "custom-url-slug"         # 自訂 URL 路徑

# 作者
author: "王小明"
authors: ["王小明", "李美華"]   # 多位作者

# 其他
toc: true                       # 顯示目錄
math: true                      # 啟用數學公式（KaTeX）
---
```

---

## 📝 Obsidian（個人筆記）

```yaml
---
title: 會議記錄 2024-03-15
date: 2024-03-15
created: 2024-03-15T10:30:00
modified: 2024-03-20T14:20:00

# 連結與分類
tags: [工作, 會議, Q1]
aliases:                        # 這個筆記的別名（搜尋用）
  - "三月十五日會議"
  - "Q1 規劃會議"

# 筆記狀態
status: "完成"                  # 草稿/進行中/完成
type: "會議記錄"

# 參與者
attendees:
  - 王小明
  - 李美華
  - 陳大偉

# 相關連結
related:
  - "[[Q1 目標]]"
  - "[[專案 A]]"
---
```

---

## 📊 資料科學 / 學術用途（Jupyter Book / Quarto）

```yaml
---
title: "台灣股市分析報告"
author:
  - name: 王小明
    affiliation: 國立台灣大學
    email: wang@ntu.edu.tw
  - name: 李美華
    affiliation: 中央研究院

date: 2024-03-15
date-modified: last-modified

# 格式設定
format:
  html:
    toc: true
    toc-depth: 3
    code-fold: true
  pdf:
    geometry: margin=1in

# 執行設定
execute:
  echo: false                   # 隱藏程式碼
  warning: false
  cache: true

# 關鍵字（用於索引）
keywords: [股市分析, 機器學習, Python]
abstract: |
  本報告分析台灣股市近五年的趨勢...
bibliography: references.bib    # 參考文獻
---
```

---

## 🌐 Next.js / Gatsby（React 靜態網站）

```yaml
---
title: "文章標題"
description: "SEO 描述文字"
date: "2024-03-15"
author: "王小明"
category: "技術"
tags: ["React", "Next.js"]
image: "/images/cover.jpg"
imageAlt: "封面圖說明"
published: true
featured: false

# Open Graph（社群媒體分享）
og_title: "分享時顯示的標題"
og_description: "分享時顯示的描述"
og_image: "/images/og-cover.jpg"

# 系列文章
series: "React 入門系列"
seriesOrder: 3
---
```

---

# 第十二章：Python 讀取 Frontmatter

---

## 🔬 動手試試看：用 python-frontmatter 解析 .md 檔

```bash
pip install python-frontmatter
```

```python
import frontmatter

# 讀取 .md 檔案
post = frontmatter.load("article.md")

# 取得 Frontmatter 欄位
print(post['title'])      # 文章標題
print(post['date'])       # 2024-03-15
print(post['tags'])       # ['Python', '資料科學']
print(post['draft'])      # False

# 取得 Markdown 內文
print(post.content)       # # 正文從這裡開始\n\n這是文章...

# 取得所有 metadata（dict）
print(post.metadata)
# {'title': '文章標題', 'date': ..., 'tags': [...]}
```

---

## 🔬 動手試試看：批次處理一個資料夾的 .md 檔

```python
import frontmatter
from pathlib import Path
import pandas as pd

def load_all_posts(folder: str) -> pd.DataFrame:
    """讀取資料夾中所有 .md 檔的 Frontmatter"""
    posts = []
    for md_file in Path(folder).glob("**/*.md"):
        post = frontmatter.load(md_file)
        meta = dict(post.metadata)
        meta['file'] = md_file.name
        meta['content_length'] = len(post.content)
        posts.append(meta)

    return pd.DataFrame(posts)

# 使用範例
df = load_all_posts("docs/")
print(df[['file', 'title', 'date', 'tags']].head())

# 找出所有草稿
drafts = df[df['draft'] == True]
print(f"草稿數量：{len(drafts)}")

# 依日期排序
df_sorted = df.sort_values('date', ascending=False)
```

---

## 🔬 動手試試看：寫入 Frontmatter

```python
import frontmatter
from datetime import date

# 建立新文章
post = frontmatter.Post(
    content="# 我的新文章\n\n這是文章內容。",
    title="我的新文章",
    date=date.today(),
    tags=["Python", "Markdown"],
    draft=False,
    author="王小明"
)

# 儲存成 .md 檔案
with open("new-article.md", "wb") as f:
    frontmatter.dump(post, f)

# 修改既有檔案
post = frontmatter.load("existing.md")
post['lastmod'] = date.today()
post['tags'].append("新標籤")

with open("existing.md", "wb") as f:
    frontmatter.dump(post, f)
```

---

# 第十三章：完整實戰——建立部落格文章系統

---

## 🎯 目標

建立一個能管理多篇 Markdown 文章的系統：
- 讀取所有文章的 Frontmatter
- 依日期排序
- 過濾草稿
- 輸出文章列表 JSON

---

## 💻 完整程式碼

```python
import frontmatter
import json
from pathlib import Path
from datetime import date, datetime

class BlogManager:
    def __init__(self, posts_dir: str):
        self.posts_dir = Path(posts_dir)

    def load_posts(self, include_drafts: bool = False) -> list[dict]:
        """載入所有文章"""
        posts = []
        for md_file in self.posts_dir.glob("*.md"):
            post = frontmatter.load(md_file)
            meta = dict(post.metadata)

            # 跳過草稿（除非明確要求）
            if meta.get('draft', False) and not include_drafts:
                continue

            # 標準化日期格式
            if 'date' in meta:
                d = meta['date']
                if isinstance(d, (date, datetime)):
                    meta['date'] = d.isoformat()

            meta['slug'] = md_file.stem
            meta['word_count'] = len(post.content.split())
            posts.append(meta)

        return sorted(posts, key=lambda x: x.get('date', ''), reverse=True)

    def get_by_tag(self, tag: str) -> list[dict]:
        """依標籤篩選文章"""
        return [
            p for p in self.load_posts()
            if tag in p.get('tags', [])
        ]

    def export_index(self, output: str = "index.json"):
        """輸出文章索引 JSON"""
        posts = self.load_posts()
        index = [{
            'title': p.get('title', ''),
            'date': p.get('date', ''),
            'slug': p.get('slug', ''),
            'tags': p.get('tags', []),
            'summary': p.get('summary', p.get('description', '')),
        } for p in posts]

        with open(output, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        print(f"已匯出 {len(index)} 篇文章到 {output}")

# 使用範例
blog = BlogManager("content/posts/")

# 列出所有已發布文章
posts = blog.load_posts()
for p in posts[:5]:
    print(f"[{p['date']}] {p['title']} ({p['word_count']} 字)")

# 找 Python 相關文章
python_posts = blog.get_by_tag("Python")
print(f"\nPython 相關文章：{len(python_posts)} 篇")

# 匯出索引
blog.export_index("public/index.json")
```

---

# 第十四章：速查手冊

---

## 🗺️ Markdown 全語法一頁總覽

```
標題
├── # H1    ## H2    ### H3    #### H4

強調
├── **粗體**   *斜體*   ***粗體斜體***   ~~刪除線~~   ==螢光==

清單
├── 無序：- 項目  或  * 項目
├── 有序：1. 項目
└── 任務：- [x] 完成  - [ ] 未完成

連結與圖片
├── [文字](URL)
├── [文字](URL "說明")
├── ![alt](image.jpg)
└── [![alt](image.jpg)](URL)

程式碼
├── 行內：`code`
└── 區塊：``` 語言\n程式碼\n```

引用
└── > 引用文字（可巢狀 >>）

表格
├── | 欄1 | 欄2 |
├── | --- | --- |
└── 對齊：:--- 靠左  :---: 置中  ---: 靠右

特殊
├── --- 水平線
├── [^1] 腳注  [^1]: 定義
├── ### 標題 {#id}  自訂錨點
├── :emoji:  表情符號
├── H~2~O  下標
└── X^2^  上標
```

---

## 🗺️ Frontmatter 常用欄位速查

```yaml
---
# 基本資訊
title: "文章標題"
date: 2024-03-15
lastmod: 2024-03-20
author: "作者"

# 分類
tags: [標籤A, 標籤B]
categories: [分類]
series: "系列名稱"

# 狀態
draft: false
published: true
weight: 10          # 排序用

# 顯示
description: "SEO 描述"
summary: "摘要"
featured_image: "cover.jpg"
toc: true           # 顯示目錄

# 進階
slug: "custom-url"  # 自訂網址
permalink: /path/   # 完整路徑
aliases: [別名]     # 搜尋別名
---
```

---

## ❓ 沒有笨問題這回事（總整理）

**Q：Markdown 和 reStructuredText（.rst）哪個更好？**
> A：Python 文件圈（Sphinx）愛用 .rst，功能更強大但語法複雜。
> Markdown 更簡單、更通用，幾乎所有平台都支援。
> 一般專案選 Markdown，除非你在寫 Python library 文件。

**Q：Frontmatter 一定要用 YAML 嗎？**
> A：不一定。Hugo 支援 YAML（`---`）、TOML（`+++`）、JSON（`{`）。
> Jekyll 只支援 YAML。Obsidian 只支援 YAML。
> **建議：統一用 YAML**，最通用，幾乎所有工具都支援。

**Q：`.md` 和 `.markdown` 副檔名有差嗎？**
> A：功能完全相同，`.md` 更常見也更短。
> GitHub、大部分編輯器都能自動識別兩者。

**Q：表格的 `|` 要對齊嗎？**
> A：技術上不需要，但對齊讓原始碼更好讀：
> ```markdown
> | 短  | 比較長的標題 |    # 沒對齊，可以
> | 短  | 很長很長的內容 |  # 可以
> ```
> 很多編輯器（VS Code + 外掛）會自動對齊表格。

**Q：Frontmatter 的日期格式？**
> A：推薦用 **ISO 8601**：`2024-03-15` 或 `2024-03-15T10:30:00+08:00`
> 這是最通用的格式，Python `datetime`、Hugo、Jekyll 都能正確解析。

---

## 🎓 你已經學會了

- [x] Markdown 的歷史與核心概念
- [x] 標題、段落、換行的正確寫法
- [x] 粗體、斜體、刪除線、螢光標記
- [x] 無序、有序、任務清單
- [x] 連結（四種寫法）與圖片
- [x] 行內程式碼與程式碼區塊（含語法高亮）
- [x] 引用、表格、水平線
- [x] 腳注、定義清單、標題 ID、Emoji
- [x] 上標、下標、跳脫字元
- [x] Frontmatter 是什麼？為什麼需要它？
- [x] YAML / TOML / JSON 三種格式
- [x] Jekyll / Hugo / Obsidian / Quarto 的常用欄位
- [x] Python `python-frontmatter` 套件讀寫 .md 檔
- [x] 完整部落格文章管理系統

---

> 📝 **最後一句話**：Markdown 的美在於簡單——
> 你學的是一套「約定俗成的符號語言」，而不是程式語言。
> 寫著寫著，你會發現自己連 Email 都想用 `**粗體**` 來強調重點。🎯

---

*製作日期：2026-03-10 | 資料來源：[Markdown Guide](https://www.markdownguide.org/)*
