# 🧠 Head First 正則表達式學習手冊
### 用一行暗語，找遍全世界的文字！

> 📖 **參考來源**：[Regular Expression 完全指南](https://aaron.makiot.com/blogs/trick/2025/regular-expression/)

---

## 這本手冊適合誰？

✅ 看到 `^(?=.*[A-Z]).*$` 完全不知道在說什麼的人
✅ 想從一大堆文字裡精準撈出 Email、電話、網址的人
✅ 爬蟲時想用 regex 從 HTML 裡直接抽取資料
✅ 想把 regex 用在自動化工具（如 Make.com）的人

---

# 第一章：正則表達式是什麼？你每天都在用但不知道

---

## 🧩 先想一個問題

你手上有一份文件，裡面有一千行資料：

```
聯絡人：王小明，電話：0912-345-678，信箱：ming@example.com
聯絡人：李美華，電話：+886-2-2345-6789，信箱：hua@gmail.com
聯絡人：陳大偉，電話：(02)8765-4321，信箱：wei@company.co.uk
...（997 行）
```

**問題來了**：你要怎麼把所有 Email 地址撈出來？

> 🤔 手動複製貼上？1000 行要多久？
> 🤔 用 `split()` 切字串？格式每行都不同怎麼辦？
> 🤔 寫一大堆 `if` 判斷？要判斷到什麼時候？

**正則表達式的答案：一行搞定。**

```python
import re
emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
```

---

## 💡 核心概念：正則表達式是一種「模式語言」

你在跟電腦說：「幫我找符合**這種樣子**的文字」

```
普通語言：「找出長得像 Email 的文字」
正則表達式：[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}

翻譯：
[a-zA-Z0-9._%+-]+   → 一堆英數字加特殊符號（@ 前面）
@                    → 一個 @ 符號
[a-zA-Z0-9.-]+      → 一堆英數字（網域名稱）
\.                   → 一個點（需要跳脫）
[a-zA-Z]{2,}        → 2個以上的英文字母（.com .tw .uk）
```

---

## 🧠 Brain Power

> 你常用的「Ctrl+F」搜尋功能，其實就是最簡單的模式比對。
> 正則表達式只是把這個能力大幅強化了。
> 想想看：如果 Ctrl+F 支援正則，你最想用它做什麼？

---

# 第二章：基本符號——認識你的工具箱

---

## 📦 符號大全（第一組：單字元）

| 符號 | 意思 | 比喻 | 範例 | 符合 |
|------|------|------|------|------|
| `.` | 任何**一個**字元 | 萬用牌（除換行） | `a.c` | `abc`, `a1c`, `a#c` |
| `\d` | 數字 0-9 | digit | `\d\d\d` | `123`, `456`, `007` |
| `\D` | **非**數字 | 大寫=反義 | `\D+` | `abc`, `你好` |
| `\w` | 英數字+底線 | word character | `\w+` | `hello`, `user_123` |
| `\W` | **非**英數字底線 | | `\W` | `!`, `@`, `空格` |
| `\s` | 空白字元 | space | `a\sb` | `a b`, `a	b`（tab） |
| `\S` | **非**空白 | | `\S+` | `hello`, `123` |

---

## 📦 符號大全（第二組：位置錨點）

| 符號 | 意思 | 比喻 | 範例 | 說明 |
|------|------|------|------|------|
| `^` | 行首 | 開頭釘子 | `^Hello` | 只找行最開頭的 Hello |
| `$` | 行尾 | 結尾釘子 | `world$` | 只找行最結尾的 world |
| `\b` | 單字邊界 | 字的圍牆 | `\bcat\b` | 只找獨立的 cat，不找 catch |
| `\B` | **非**單字邊界 | | `\Bcat\B` | 找在字中間的 cat |

---

## 📦 符號大全（第三組：數量詞）

| 符號 | 意思 | 記憶口訣 | 範例 | 符合 |
|------|------|---------|------|------|
| `*` | 0 次或多次 | 零到無限 | `ab*c` | `ac`, `abc`, `abbbc` |
| `+` | 1 次或多次 | 至少一次 | `ab+c` | `abc`, `abbbc`（不符合 `ac`） |
| `?` | 0 次或 1 次 | 可有可無 | `colou?r` | `color`, `colour` |
| `{n}` | 恰好 n 次 | 精確次數 | `\d{4}` | `2024`, `1234` |
| `{n,}` | 至少 n 次 | n 以上 | `\d{2,}` | `12`, `123`, `1234` |
| `{n,m}` | n 到 m 次 | n~m 之間 | `\d{2,4}` | `12`, `123`, `1234` |

---

## 📦 符號大全（第四組：群組與集合）

| 符號 | 意思 | 範例 | 符合 |
|------|------|------|------|
| `[abc]` | a 或 b 或 c | `[aeiou]` | 任何一個母音 |
| `[a-z]` | a 到 z（範圍） | `[a-zA-Z]` | 任何英文字母 |
| `[^abc]` | **不是** a、b、c | `[^0-9]` | 任何非數字字元 |
| `(abc)` | 捕獲群組 | `(hello)+` | `hello`, `hellohello` |
| `(?:abc)` | 非捕獲群組 | `(?:abc)+` | 群組但不捕獲 |
| `a\|b` | a 或 b | `cat\|dog` | `cat` 或 `dog` |

---

## 🔬 動手試試看：Python 中的基本用法

```python
import re

text = "我的電話是 0912-345-678，備用 (02)2345-6789，Email: test@example.com"

# re.search()  → 找第一個符合的（回傳 Match 物件）
match = re.search(r'\d{4}', text)
print(match.group())   # 0912

# re.findall() → 找所有符合的（回傳 list）
phones = re.findall(r'\d+', text)
print(phones)          # ['0912', '345', '678', '02', '2345', '6789']

# re.sub()     → 取代符合的文字
cleaned = re.sub(r'\d', '*', text)
print(cleaned)         # 把所有數字換成 *

# re.split()   → 用模式切割字串
parts = re.split(r'[,，]', text)
print(parts)           # 用逗號切割
```

---

## ⚠️ 超重要！跳脫字元的陷阱

某些字元在 regex 有特殊意義，要找「本人」時需要加 `\`：

```
需要跳脫的字元：. * + ? ^ $ { } [ ] | ( ) \

# 想找一個點（.）
錯誤：.      → 這會符合任何字元！
正確：\.     → 只符合真正的點

# 想找一個左括號（(）
錯誤：(      → regex 會認為是群組開始
正確：\(     → 只符合真正的括號

# Python 中用原始字串 r'' 避免雙重跳脫
re.search(r'\.', text)   # 正確：找真正的點
re.search('\\.', text)   # 也可，但容易搞混
```

---

# 第三章：貪婪 vs 懶惰——兩種完全不同的性格

---

## 😈 貪婪模式（預設）

正則表達式預設是「貪婪」的——它會盡可能**多**吃字元。

```python
html = "<b>粗體</b> 和 <i>斜體</i>"

# 貪婪：.*  → 吃越多越好
match = re.search(r'<.*>', html)
print(match.group())
# 輸出：<b>粗體</b> 和 <i>斜體</i>
# 它從第一個 < 一路吃到最後一個 >！
```

---

## 😇 懶惰模式（加 `?`）

加上 `?` 變成「懶惰」——它會盡可能**少**吃字元。

```python
html = "<b>粗體</b> 和 <i>斜體</i>"

# 懶惰：.*?  → 吃越少越好
matches = re.findall(r'<.*?>', html)
print(matches)
# 輸出：['<b>', '</b>', '<i>', '</i>']
# 每次只吃到最近的 >，完美！
```

---

## 📋 貪婪 vs 懶惰對照表

| 寫法 | 模式 | 行為 |
|------|------|------|
| `.*` | 貪婪 | 吃到最遠的位置 |
| `.*?` | 懶惰 | 吃到最近的位置 |
| `.+` | 貪婪 | 至少一個，吃越多越好 |
| `.+?` | 懶惰 | 至少一個，吃越少越好 |
| `\d{2,4}` | 貪婪 | 優先吃 4 個 |
| `\d{2,4}?` | 懶惰 | 優先吃 2 個 |

> 🔥 **爬蟲黃金法則**：從 HTML 抓資料時，**永遠用懶惰模式** `.*?`

---

## 🧠 Brain Power

> `<div>第一個</div><div>第二個</div>`
> 用 `<div>(.*)</div>` 會抓到什麼？
> 用 `<div>(.*?)</div>` 呢？

---

# 第四章：捕獲群組——把你要的裝進口袋

---

## 💡 核心概念：`()` 就是你的口袋

```python
text = "訂單日期：2024-03-15，金額：NT$ 1,500"

# 沒有群組：只知道有沒有符合
re.search(r'\d{4}-\d{2}-\d{2}', text)

# 有群組：可以把年、月、日分別拿出來
match = re.search(r'(\d{4})-(\d{2})-(\d{2})', text)
print(match.group(0))  # 整個符合：2024-03-15
print(match.group(1))  # 第一個群組：2024（年）
print(match.group(2))  # 第二個群組：03（月）
print(match.group(3))  # 第三個群組：15（日）
```

---

## 📋 群組類型對照表

| 寫法 | 類型 | 說明 |
|------|------|------|
| `(abc)` | 捕獲群組 | 捕獲內容，可用 `group(n)` 取出 |
| `(?:abc)` | 非捕獲群組 | 只是群組，不捕獲（不占號碼） |
| `(?P<name>abc)` | 命名群組 | 可用名稱取出 `group('name')` |
| `(?=abc)` | 正向預查 | 前面有 abc（但不包含） |
| `(?!abc)` | 負向預查 | 前面**沒有** abc |

---

## 🔬 動手試試看：命名群組更清楚

```python
text = "聯絡人：wang@example.com"

# 命名群組，程式碼更好讀
pattern = r'(?P<user>[a-zA-Z0-9._%+-]+)@(?P<domain>[a-zA-Z0-9.-]+)\.(?P<tld>[a-zA-Z]{2,})'
match = re.search(pattern, text)

if match:
    print(match.group('user'))    # wang
    print(match.group('domain'))  # example
    print(match.group('tld'))     # com
```

---

## 🎯 預查（Lookahead）的妙用

```python
text = "價格：$100，折扣價：$80，運費：$30"

# 正向預查：找 $ 後面的數字（但不包含 $）
prices = re.findall(r'(?<=\$)\d+', text)
print(prices)   # ['100', '80', '30']

# 負向預查：找不在 $ 後面的數字
# 也就是排除掉價格，只找其他數字
pattern = r'(?<!\$)\b\d+\b'
```

---

# 第五章：修飾符——改變整個規則的旗標

---

## 🚩 Python 中的修飾符

```python
import re

text = """第一行：Hello World
第二行：hello python
第三行：HELLO REGEX"""

# re.IGNORECASE (re.I)：不分大小寫
matches = re.findall(r'hello', text, re.IGNORECASE)
print(matches)   # ['Hello', 'hello', 'HELLO']

# re.MULTILINE (re.M)：^ 和 $ 符合每行的開頭/結尾
matches = re.findall(r'^\w+', text, re.MULTILINE)
print(matches)   # ['第一行', '第二行', '第三行']

# re.DOTALL (re.S)：讓 . 也能符合換行符
match = re.search(r'Hello.*python', text, re.DOTALL)
print(match.group())  # Hello World\n第二行：hello python

# 組合使用（用 | 連接）
matches = re.findall(r'^hello', text, re.IGNORECASE | re.MULTILINE)
print(matches)   # ['Hello', 'hello', 'HELLO']
```

---

## 📋 修飾符快速對照

| 修飾符 | 縮寫 | 效果 |
|--------|------|------|
| `re.IGNORECASE` | `re.I` | 不分大小寫 |
| `re.MULTILINE` | `re.M` | `^`/`$` 匹配每行 |
| `re.DOTALL` | `re.S` | `.` 也匹配換行 |
| `re.VERBOSE` | `re.X` | 允許空白和註解，方便閱讀複雜 regex |
| `re.GLOBAL` | —— | Python 用 `findall` 代替 |

---

## 🔬 動手試試看：re.VERBOSE 讓複雜 regex 可讀

```python
# 沒有 VERBOSE：根本看不懂
email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# 有 VERBOSE：每段都能加說明
email_pattern_verbose = re.compile(r"""
    ^                       # 字串開頭
    [a-zA-Z0-9._%+-]+      # 使用者名稱（英數字加特殊符號）
    @                       # @ 符號
    [a-zA-Z0-9.-]+         # 網域名稱
    \.                      # 一個點
    [a-zA-Z]{2,}           # 頂級域名（至少 2 個字母）
    $                       # 字串結尾
""", re.VERBOSE)

result = email_pattern_verbose.match("user@example.com")
print(result is not None)  # True
```

---

# 第六章：20 個實用 Regex 模式

---

## 🎯 驗證類模式

### 1. Email 地址

```python
pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# 測試
emails = [
    "john.doe@example.com",   # ✅
    "user123@gmail.co.uk",    # ✅
    "invalid@",               # ❌
    "@nodomain.com",          # ❌
]
for e in emails:
    ok = bool(re.match(pattern, e))
    print(f"{e:30} {'✅' if ok else '❌'}")
```

---

### 2. 網址（URL）

```python
pattern = r'^(https?:\/\/)?(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'

# 符合：https://www.example.com
#       example.com/path?q=test
```

---

### 3. 台灣電話號碼（國際格式）

```python
pattern = r'^\+?(\d{1,3})?[\s-]?\(?\d{1,4}\)?[\s-]?\d{1,4}[\s-]?\d{1,9}$'

phones = [
    "+886-912-345-678",    # ✅
    "0912-345-678",        # ✅
    "(02)2345-6789",       # ✅
    "+1 (123) 456-7890",   # ✅
]
```

---

### 4. IPv4 位址

```python
pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'

# 符合：192.168.1.1, 127.0.0.1
# 不符合：999.1.1.1, 192.168.1

# 逐段解析：
# 25[0-5]           → 250~255
# 2[0-4][0-9]       → 200~249
# [01]?[0-9][0-9]?  → 0~199
```

---

### 5. 日期（YYYY-MM-DD）

```python
pattern = r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$'

# 符合：2024-01-31, 2023-12-01
# 不符合：2024-13-01（月份超過12）, 2024-01-32（日期超過31）

# 解析：
# 0[1-9]      → 01~09 月
# 1[0-2]      → 10~12 月
# 0[1-9]      → 01~09 日
# [12][0-9]   → 10~29 日
# 3[01]       → 30~31 日
```

---

### 6. 時間（HH:MM 或 HH:MM:SS）

```python
pattern = r'^([01]?[0-9]|2[0-3]):([0-5][0-9])(?::([0-5][0-9]))?$'

# 符合：13:45, 09:05, 23:59:59
# 不符合：24:00, 12:60
```

---

### 7. 強密碼驗證

```python
pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'

# 解析（使用預查）：
# (?=.*[a-z])     → 必須含小寫字母
# (?=.*[A-Z])     → 必須含大寫字母
# (?=.*\d)        → 必須含數字
# (?=.*[@$!%*?&]) → 必須含特殊符號
# [...]{ 8,}      → 至少 8 個字元

passwords = [
    "Passw0rd!",    # ✅
    "password",     # ❌（無大寫、無數字、無特殊符號）
    "Pass1!",       # ❌（太短）
]
```

---

### 8. 十六進位色碼

```python
pattern = r'^#?([a-fA-F0-9]{6}|[a-fA-F0-9]{3})$'

colors = ["#FF0000", "#f00", "FF0000", "#GGG"]
# ✅ ✅ ✅ ❌
```

---

### 9. 使用者名稱（3-16字元，英文開頭）

```python
pattern = r'^[a-zA-Z][a-zA-Z0-9_]{2,15}$'

# 符合：john_doe123, user_2023, abc
# 不符合：1user（數字開頭）, ab（太短）, a_very_long_username_here（太長）
```

---

### 10. 中文字元

```python
pattern = r'[\u4e00-\u9fa5]'

text = "Hello 世界！This is 台灣。"
chinese = re.findall(pattern, text)
print(''.join(chinese))   # 世界台灣

# 抓取連續中文詞組
words = re.findall(r'[\u4e00-\u9fa5]+', text)
print(words)  # ['世界', '台灣']
```

---

## 🎯 清理與轉換類模式

### 11. 移除 HTML 標籤

```python
html = "<p>這是<strong>重要</strong>的<a href='#'>連結</a></p>"

# 移除所有 HTML 標籤
text = re.sub(r'<[^>]+>', '', html)
print(text)   # 這是重要的連結
```

---

### 12. 清除多餘空白

```python
text = "這裡  有    很多    空白"

# 多個空白換成單一空白
cleaned = re.sub(r'\s{2,}', ' ', text)
print(cleaned)   # 這裡 有 很多 空白

# 移除開頭和結尾空白（等同 strip()）
cleaned = re.sub(r'^\s+|\s+$', '', text)
```

---

### 13. 抓取引號內容

```python
text = 'CEO說："我們的目標是\"永續發展\"和\"創新突破\""'

# 抓取雙引號內的文字
quoted = re.findall(r'"([^"]*)"', text)
print(quoted)   # ['我們的目標是', '永續發展', '創新突破']
```

---

### 14. CSV 行解析（含引號欄位）

```python
import re

csv_line = '王小明,"台北市, 信義區",0912-345-678,"工程師, 資深"'

# 處理引號包覆的逗號
pattern = r'(?:^|,)(?:"([^"]*(?:""[^"]*)*)"|([^,]*))'
fields = re.findall(pattern, csv_line)
# 每個 match 是 (引號內容, 非引號內容) 的 tuple
result = [a or b for a, b in fields]
print(result)   # ['王小明', '台北市, 信義區', '0912-345-678', '工程師, 資深']
```

---

### 15. 抓取 `<script>` 標籤內容

```python
html = """
<html>
<script type="text/javascript">
var data = {"name": "test"};
</script>
<p>正文</p>
<script>console.log("hello");</script>
</html>
"""

scripts = re.findall(r'<script[^>]*>([\s\S]*?)<\/script>', html, re.IGNORECASE)
for i, s in enumerate(scripts):
    print(f"Script {i+1}：{s.strip()[:50]}")
```

---

# 第七章：爬蟲實戰——從 HTML 直接抓資料

---

## 💡 為什麼爬蟲要用 Regex？

```
情境1：BeautifulSoup 找不到 → 網頁結構太奇怪
情境2：在 Make.com 自動化工具裡，只有 regex 可以用
情境3：需要同時抓多種格式的資料，一個 pattern 搞定
情境4：HTML 結構很穩定，regex 比 DOM 解析快
```

---

## 🎯 實戰一：Google News 文章標題與連結

```python
import re, requests

url = "https://news.google.com/search?q=台積電&hl=zh-TW"
html = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).text

# 抓取新聞標題
title_pattern = r'<h[3-4][^>]*>.*?<a[^>]*>(.*?)<\/a>.*?<\/h[3-4]>'
titles = re.findall(title_pattern, html, re.DOTALL)

# 抓取新聞連結
link_pattern = r'<h[3-4][^>]*>.*?<a[^>]*?href="([^"]*)"[^>]*>.*?<\/a>.*?<\/h[3-4]>'
links = re.findall(link_pattern, html, re.DOTALL)

# 清除 HTML 實體和多餘空白
def clean_text(text):
    text = re.sub(r'<[^>]+>', '', text)   # 移除 HTML 標籤
    text = re.sub(r'&amp;', '&', text)    # HTML 實體
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    return text.strip()

for title, link in zip(titles[:5], links[:5]):
    print(f"標題：{clean_text(title)}")
    print(f"連結：{link}")
    print()
```

---

## 🎯 實戰二：LinkedIn 職缺資料

```python
html = requests.get(
    "https://www.linkedin.com/jobs/search/?keywords=data+engineer",
    headers={'User-Agent': 'Mozilla/5.0'}
).text

# 職缺標題
job_titles = re.findall(
    r'<h3[^>]*class="[^"]*base-search-card__title[^"]*"[^>]*>.*?<a[^>]*>(.*?)<\/a>.*?<\/h3>',
    html, re.DOTALL
)

# 公司名稱
companies = re.findall(
    r'<h4[^>]*class="[^"]*base-search-card__subtitle[^"]*"[^>]*>.*?<a[^>]*>(.*?)<\/a>.*?<\/h4>',
    html, re.DOTALL
)

# 工作地點
locations = re.findall(
    r'<span[^>]*class="[^"]*job-search-card__location[^"]*"[^>]*>(.*?)<\/span>',
    html, re.DOTALL
)

# 薪資（如果有的話）
salaries = re.findall(
    r'<span[^>]*class="[^"]*job-search-card__salary-info[^"]*"[^>]*>(.*?)<\/span>',
    html, re.DOTALL
)

# 整合資料
jobs = []
for i, (title, company) in enumerate(zip(job_titles, companies)):
    jobs.append({
        'title':    re.sub(r'\s+', ' ', title).strip(),
        'company':  re.sub(r'\s+', ' ', company).strip(),
        'location': locations[i].strip() if i < len(locations) else '',
        'salary':   salaries[i].strip() if i < len(salaries) else '未提供',
    })

for job in jobs[:3]:
    print(f"職位：{job['title']}")
    print(f"公司：{job['company']} | 地點：{job['location']}")
    print(f"薪資：{job['salary']}")
    print()
```

---

## ⚠️ HTML 爬蟲 Regex 五大原則

```
原則1：永遠用懶惰模式 .*?
       ❌ <div>.*</div>
       ✅ <div>.*?</div>

原則2：屬性用 [^>]* 跳過
       ❌ <div class="xxx">
       ✅ <div[^>]*>        ← 不管 class 叫什麼

原則3：跨行內容加 re.DOTALL
       re.findall(pattern, html, re.DOTALL)

原則4：記得清理 HTML 實體
       &amp; → &
       &lt;  → <
       &gt;  → >
       &nbsp; → 空格

原則5：複雜情況改用 BeautifulSoup + XPath
       regex 適合穩定、簡單的結構
       DOM 解析適合複雜的巢狀結構
```

---

# 第八章：進階技巧——讓你的 Regex 更聰明

---

## 🚀 技巧一：編譯 Pattern（重複使用時更快）

```python
import re

# 每次 re.findall() 都要重新編譯 pattern，效率低
for text in large_list:
    re.findall(r'\d+', text)   # 慢

# 預先編譯一次，重複使用
digit_pattern = re.compile(r'\d+')
for text in large_list:
    digit_pattern.findall(text)   # 快很多！
```

---

## 🚀 技巧二：OR 條件與群組搭配

```python
# 找所有日期格式（可能是不同格式）
dates_pattern = re.compile(r"""
    (\d{4}[-/]\d{2}[-/]\d{2})   # YYYY-MM-DD 或 YYYY/MM/DD
    |
    (\d{2}[-/]\d{2}[-/]\d{4})   # DD-MM-YYYY 或 DD/MM/YYYY
    |
    ([A-Z][a-z]+\s\d{1,2},\s\d{4})  # January 31, 2024
""", re.VERBOSE)

text = "活動時間：2024-03-15，另一活動：15/03/2024，報名截止：March 10, 2024"
matches = dates_pattern.findall(text)
# 每個 match 是三個群組的 tuple，其中只有一個非空
dates = [m[0] or m[1] or m[2] for m in matches]
print(dates)   # ['2024-03-15', '15/03/2024', 'March 10, 2024']
```

---

## 🚀 技巧三：反向引用（前後一致）

```python
# 找成對的 HTML 標籤（開頭和結尾一樣）
pattern = r'<(\w+)[^>]*>.*?<\/\1>'
#               ^^^                 ↑
#           捕獲群組1            反向引用群組1

html = "<b>粗體</b> <i>斜體</i> <div>區塊</div>"
matches = re.findall(pattern, html, re.DOTALL)
print(matches)   # ['b', 'i', 'div']（標籤名稱）
```

---

## 🚀 技巧四：避免過度回溯

```python
# ❌ 危險的 regex：可能造成「災難性回溯」
# 在某些輸入下會跑很久甚至卡死
bad_pattern = r'(a+)+b'   # 巢狀量詞

# ✅ 改寫版：使用更精確的條件
good_pattern = r'a+b'

# ✅ 或使用原子群組（Python 3.11+）
atomic_pattern = r'(?>a+)b'
```

---

# 第九章：Make.com 自動化工具整合

---

## 🔧 在 Make.com 中使用 Regex

Make.com 的 **Text Parser** 模組支援正則表達式，讓你不用寫程式也能做資料擷取！

---

## 📋 Make.com Regex 工作流程

```
步驟1：HTTP 模組
       GET https://news.example.com/rss
       ↓
步驟2：HTML to Text 轉換器
       把 HTML 轉成純文字（清除標籤）
       ↓
步驟3：Text Parser（正則表達式）
       輸入 Pattern：(\d{4}-\d{2}-\d{2})
       ↓
步驟4：輸出
       {{1}} = 第一個捕獲群組（日期）
       {{2}} = 第二個捕獲群組（如果有）
```

---

## 🎯 Make.com 實用 Pattern

```
抓取 Email：
[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}

抓取 URL：
https?:\/\/[^\s"'<>]+

抓取括號內的數字：
\((\d+)\)

抓取引號內的文字：
"([^"]+)"

抓取特定文字後面的值：
總計：(\d+(?:,\d{3})*)元
```

---

## ⚠️ Make.com 注意事項

```
1. 群組編號從 {{1}} 開始
2. 沒有 re.DOTALL，需要用 [\s\S] 代替 .
3. 用 | 測試多種格式的替代方案
4. 先在 regex101.com 測試好再貼進去
5. 使用「全域比對」選項抓取多筆資料
```

---

# 第十章：正則表達式速查手冊

---

## 🗺️ 全部符號一頁搞定

```
單字元
├── .    任何字元（除換行）
├── \d   數字         \D 非數字
├── \w   英數字底線   \W 非英數字底線
├── \s   空白字元     \S 非空白
└── [abc] 其中之一   [^abc] 排除這些

位置錨點
├── ^    行首
├── $    行尾
├── \b   單字邊界
└── \B   非單字邊界

數量詞（預設貪婪，加 ? 變懶惰）
├── *     0次以上    *?
├── +     1次以上    +?
├── ?     0或1次     ??
├── {n}   剛好n次
├── {n,}  至少n次
└── {n,m} n到m次

群組
├── (abc)      捕獲群組
├── (?:abc)    非捕獲群組
├── (?P<n>abc) 命名群組
├── (?=abc)    正向預查
├── (?!abc)    負向預查
├── (?<=abc)   正向後顧
└── (?<!abc)   負向後顧

Python 函式
├── re.match()    從開頭比對
├── re.search()   找第一個符合
├── re.findall()  找所有符合（回傳 list）
├── re.finditer() 找所有符合（回傳 iterator）
├── re.sub()      取代
├── re.split()    切割
└── re.compile()  預編譯

修飾符
├── re.I  不分大小寫
├── re.M  多行模式
├── re.S  點匹配換行
└── re.X  詳細模式（允許空白和註解）
```

---

## 🏆 20 個實用 Pattern 速查

| # | 用途 | Pattern |
|---|------|---------|
| 1 | Email | `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$` |
| 2 | URL | `^(https?:\/\/)?(www\.)?[-\w@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b` |
| 3 | 國際電話 | `^\+?(\d{1,3})?[\s-]?\(?\d{1,4}\)?[\s-]?\d{1,4}[\s-]?\d{1,9}$` |
| 4 | IPv4 | `^(?:(?:25[0-5]\|2[0-4]\d\|[01]?\d\d?)\.){3}(?:25[0-5]\|2[0-4]\d\|[01]?\d\d?)$` |
| 5 | 日期 YYYY-MM-DD | `^\d{4}-(0[1-9]\|1[0-2])-(0[1-9]\|[12]\d\|3[01])$` |
| 6 | 時間 HH:MM | `^([01]?\d\|2[0-3]):([0-5]\d)(?::([0-5]\d))?$` |
| 7 | 強密碼 | `^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$` |
| 8 | 信用卡 | `^(?:4\d{12}(?:\d{3})?`\|`5[1-5]\d{14}\|3[47]\d{13})$` |
| 9 | 郵遞區號（美國） | `^\d{5}(?:-\d{4})?$` |
| 10 | 社會安全碼 | `^(?!000\|666\|9\d{2})([0-8]\d{2}\|7([0-6]\d\|7[012]))(?!00)\d{2}(?!0000)\d{4}$` |
| 11 | HTML 標籤 | `<\/?[a-z][^>]*>` |
| 12 | 引號內容 | `"([^"]*)"` |
| 13 | 十六進位色碼 | `^#?([a-fA-F0-9]{6}\|[a-fA-F0-9]{3})$` |
| 14 | 數字範圍 0-100 | `^([0-9]\|[1-9][0-9]\|100)$` |
| 15 | 使用者名稱 | `^[a-zA-Z][a-zA-Z0-9_]{2,15}$` |
| 16 | 中文字元 | `[\u4e00-\u9fa5]+` |
| 17 | Script 標籤 | `<script[^>]*>([\s\S]*?)<\/script>` |
| 18 | CSV 解析 | `(?:^`,`)(?: "([^"]*(?:""[^"]*)*)" \| ([^`,`]*))` |
| 19 | 多餘空白 | `\s{2,}` |
| 20 | 純數字 | `^\d+$` |

---

## ❓ 沒有笨問題這回事（總整理）

**Q：regex 跟 `str.replace()` 比，什麼時候用哪個？**
> A：格式**固定**用 `str.replace()`（快又清楚）。
> 格式**有變化**、需要**模式匹配**，用 `re.sub()`。
> 例如：把所有「連續空白」換成一個空格，一定要用 regex。

**Q：`re.match()` 和 `re.search()` 差在哪？**
> A：`match()` 只看**字串開頭**是否符合，等同於 pattern 前面自動加上 `^`。
> `search()` 找**整個字串**中第一個符合的位置。
> 幾乎所有情況你應該用 `search()`，除非你確定只要比對開頭。

**Q：`.*` 和 `[\s\S]*` 有什麼差？**
> A：`.*` 預設不匹配換行符（`\n`），加上 `re.DOTALL` 才行。
> `[\s\S]*` 永遠匹配包含換行的任何字元，不需要額外修飾符。
> 在 Make.com 等不支援修飾符的工具裡，一定要用 `[\s\S]*`。

**Q：如何測試我的 regex？**
> A：強烈推薦 [regex101.com](https://regex101.com)——
> 即時高亮顯示匹配結果、解釋每個符號的意思、可以選 Python/JS/Go 模式。

**Q：regex 能解析所有 HTML 嗎？**
> A：技術上不能（HTML 是遞迴結構，正規語言無法完整解析）。
> 但對於**固定格式的片段**，regex 非常有效。
> 遇到複雜、深層的 HTML，請用 BeautifulSoup 或 lxml。

---

## 🎓 你已經學會了

- [x] 正則表達式的核心概念（模式匹配語言）
- [x] 基本符號（單字元、錨點、數量詞、群組、集合）
- [x] 貪婪 vs 懶惰模式（`.*` vs `.*?`）
- [x] 捕獲群組與命名群組
- [x] 預查（Lookahead / Lookbehind）
- [x] Python 的 re 模組（match/search/findall/sub/compile）
- [x] 修飾符（IGNORECASE / MULTILINE / DOTALL / VERBOSE）
- [x] 20 個實用 Pattern（Email、URL、日期、密碼...）
- [x] HTML 爬蟲五大原則
- [x] Google News / LinkedIn 實戰範例
- [x] Make.com 自動化工具整合
- [x] 效能優化技巧（預編譯、避免回溯）

---

> 📝 **最後一句話**：正則表達式就像學武功——基本功很重要，
> 但真正的功力來自在真實問題中不斷練習。
> 每次遇到「需要從文字中找規律」的問題，先想想 regex 能不能解！✨

---

*製作日期：2026-03-10 | 資料來源：[Regular Expression 完全指南](https://aaron.makiot.com/blogs/trick/2025/regular-expression/)*
