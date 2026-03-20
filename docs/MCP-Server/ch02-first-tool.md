# 第二章：打造你的第一個工具

## ──10 行程式，讓 Claude 知道現在幾點

---

```
┌─────────────────────────────────────────────────────┐
│  你：「Claude，現在幾點？」                          │
│                                                     │
│  Claude：「我無法得知當前時間，因為我沒有存取      │
│            即時資訊的能力……」                       │
│                                                     │
│  ← 這個問題，用 10 行 Python 就能解決。             │
└─────────────────────────────────────────────────────┘
```

「知道現在幾點」聽起來超簡單對吧？

但對 Claude 來說，這不是一件理所當然的事。Claude 的訓練資料在某個時間點截止，之後它就不知道時間過了多久。每次對話對它來說都像是從黑暗中醒來，不知道現在是早上、下午，還是凌晨兩點。

讓我們用這個最簡單的例子，學習怎麼打造一個完整的 MCP Tool。10 行程式。真的。

---

## 2.1 Tool 解剖：一個工具由什麼組成？

在 MCP 的世界裡，每一個 **Tool（工具）** 都由四個部分組成：

```
┌─────────────────────────────────────────────────────────┐
│                     MCP Tool 解剖圖                      │
│                                                         │
│  ① 名稱（name）                                         │
│     AI 用來識別和呼叫工具的唯一標識符                   │
│     例如："get_current_time"                            │
│                                                         │
│  ② 描述（description）                                  │
│     AI 用來決定「何時」呼叫工具的說明書                  │
│     ← 這個比你想像的重要 100 倍（第三章詳談）           │
│                                                         │
│  ③ 輸入 Schema（inputSchema）                           │
│     工具接受哪些參數、型別是什麼                        │
│     FastMCP 會從 Python 型別提示自動生成！              │
│                                                         │
│  ④ 回傳值（return value）                               │
│     工具執行完的結果，通常是字串                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

這四個部分，AI 在每次決定「要不要呼叫這個工具」、「傳什麼參數」時，都會參考。

> **重要**：MCP Tool 的回傳值幾乎都應該是**字串（str）**。因為 LLM 只能讀文字。就算你的資料是 JSON 物件，也要用 `json.dumps()` 轉成字串再回傳。

---

## 2.2 FastMCP 裝飾器魔法

FastMCP 最酷的功能是：**你不需要手寫 JSON Schema**。

JSON Schema 是描述工具參數格式的規範，格式繁瑣。如果你要手寫，看起來像這樣：

```json
{
  "name": "greet",
  "description": "向用戶打招呼",
  "inputSchema": {
    "type": "object",
    "properties": {
      "name": {
        "type": "string",
        "description": "要問候的人名"
      },
      "formal": {
        "type": "boolean",
        "default": false,
        "description": "是否使用正式語氣"
      }
    },
    "required": ["name"]
  }
}
```

有了 FastMCP，你只需要寫正常的 Python 函式，加上 `@mcp.tool()` 裝飾器，Schema 就自動生成了：

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("問候服務")

# 你寫的 Python 函式（看起來就是普通函式）
@mcp.tool()
def greet(name: str, formal: bool = False) -> str:
    """向指定的人打招呼。name 是對方的名字，formal 設為 True 則使用正式語氣。"""
    if formal:
        return f"您好，{name} 先生/女士，很高興認識您。"
    return f"嗨，{name}！"
```

FastMCP 在背後做了這些事：

```
@mcp.tool() 裝飾器的魔法：

Python 型別提示          →    JSON Schema 型別
─────────────────────────────────────────────────
str                      →    {"type": "string"}
int                      →    {"type": "integer"}
float                    →    {"type": "number"}
bool                     →    {"type": "boolean"}
list[str]                →    {"type": "array", "items": {"type": "string"}}
list[float]              →    {"type": "array", "items": {"type": "number"}}

有預設值的參數           →    不放進 required 列表（選填）
沒有預設值的參數         →    放進 required 列表（必填）
函式的 docstring         →    description 欄位
```

自動生成的 JSON Schema（和手寫的完全一樣）：

```json
{
  "name": "greet",
  "description": "向指定的人打招呼。name 是對方的名字，formal 設為 True 則使用正式語氣。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "formal": {"type": "boolean", "default": false}
    },
    "required": ["name"]
  }
}
```

> **提醒**：**docstring（函式說明字串）就是工具的 description**。這個字串 AI 一定會讀到。請認真寫，像在寫給 AI 看的使用說明書一樣。我們在第三章會深入討論怎麼寫好 description。

---

### 腦力激盪 🧠

> 為什麼 return type（回傳型別提示）也很重要？
> 如果你把 `-> str` 改成 `-> dict`，會發生什麼？

花 30 秒思考。

<details>
<summary>點開看答案</summary>

Return type 對 FastMCP 的 Schema 生成影響不大，但對你的程式邏輯很重要。

如果你回傳了 `dict` 而不是 `str`，FastMCP 會嘗試序列化它，但行為可能不如預期。更重要的是：

1. **LLM 只能讀文字**。如果你回傳一個 Python dict，LLM 會看到 Python 的 repr 字串（`{'key': 'value'}`），而不是格式化的 JSON。應該用 `json.dumps(data, ensure_ascii=False)` 轉換。

2. **回傳型別提示是給你自己看的文件**。寫 `-> str` 讓未來的你（或同事）知道這個工具回傳的是文字。

</details>

---

## 2.3 stdio 傳輸：底層發生了什麼？

當你把 MCP Server 加進 Claude Desktop 的設定後，每次 Claude Desktop 啟動，它會：

```
Claude Desktop 的啟動流程：

1. 讀取 claude_desktop_config.json
   ↓
2. 看到 "command": "python", "args": ["server.py"]
   ↓
3. 用 subprocess.Popen() 啟動 Python 子程序
   ↓
4. 建立雙向管道（pipes）：
      Claude Desktop ──stdin──→ Python process
      Claude Desktop ←─stdout─ Python process
   ↓
5. 透過管道發送初始化訊息（JSON-RPC 格式）
   ↓
6. Python process 回應它有哪些工具
   ↓
7. 連線建立完成！
```

之後每次 AI 決定要呼叫工具：

```
工具呼叫的資料流：

Claude (LLM)
  "我需要呼叫 get_current_time 工具"
     ↓
Claude Desktop (Host)
  {"jsonrpc": "2.0", "method": "tools/call",
   "params": {"name": "get_current_time", "arguments": {}}}
     ↓ stdin 管道
Python 子程序（你的 server.py）
  執行 get_current_time()
  返回 "2026-03-20 14:30:00 +0800"
     ↓ stdout 管道
Claude Desktop
  把結果塞回給 LLM
     ↓
Claude (LLM)
  "現在是 2026 年 3 月 20 日下午 2:30。"
```

> **重要**：**永遠不要在 stdio 模式的工具裡用 `print()` 輸出到 stdout！**
>
> 因為 stdout 是 MCP 協議的通訊管道。如果你在工具函式裡寫 `print("debug info")`，這段文字會混進 JSON-RPC 訊息裡，讓 Claude Desktop 完全看不懂，導致連線中斷。
>
> Debug 請用 `import sys; print("debug", file=sys.stderr)` 或用 Python 的 `logging` 模組。

---

### 腦力激盪 🧠

> stdio 傳輸的優點和缺點各是什麼？
> 什麼情況下你會不想用 stdio？

<details>
<summary>點開看答案</summary>

**優點：**
- 最簡單，不需要設定網路
- 安全：不開任何 port，不暴露在網路上
- 延遲低：在同一台機器上，管道通訊比 HTTP 快
- 不需要認證機制

**缺點：**
- 只能在本機使用，不能讓其他人的機器連到你的工具
- 每個使用者都要在自己的機器上安裝你的 Server 和所有相依套件
- 不適合需要多人共用、或需要部署到伺服器的情境
- Server 崩潰時，整個 Claude Desktop 連線也斷了

當你要讓**多個使用者**、**多台機器**，或**雲端環境**使用你的 MCP Server 時，就需要改用 Streamable HTTP（第五章主題）。

</details>

---

## 2.4 claude_desktop_config.json — 告訴 Claude 你的 Server 在哪

Claude Desktop 透過一個 JSON 設定檔知道要啟動哪些 MCP Server。

這個檔案的位置：
- **macOS**：`~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**：`%APPDATA%\Claude\claude_desktop_config.json`

設定格式：

```json
{
  "mcpServers": {
    "my-time-server": {
      "command": "python",
      "args": ["/Users/yourname/projects/time_server.py"],
      "env": {
        "PYTHONPATH": "/Users/yourname/projects"
      }
    }
  }
}
```

> **重要**：`args` 裡一定要用**絕對路徑**！相對路徑會讓 Claude Desktop 找不到你的檔案，因為它的工作目錄不是你以為的那個地方。
>
> 快速取得絕對路徑的方法：在終端機 `cd` 到你的 server.py 所在目錄，然後執行 `pwd`（macOS/Linux）或 `cd`（Windows）。

多個 MCP Server 可以同時設定：

```json
{
  "mcpServers": {
    "time-server": {
      "command": "python",
      "args": ["/absolute/path/time_server.py"]
    },
    "weather-server": {
      "command": "python",
      "args": ["/absolute/path/weather_server.py"],
      "env": {
        "WEATHER_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

修改設定後，需要**重啟 Claude Desktop** 才會生效。

---

## 2.5 從 Hello World 到真實 API

現在讓我們一步一步建立真正有用的工具。

### 第一步：get_current_time()

```python
# time_server.py — 從這裡開始
from mcp.server.fastmcp import FastMCP
from datetime import datetime
import pytz

mcp = FastMCP("時間服務")

@mcp.tool()
def get_current_time(timezone: str = "Asia/Taipei") -> str:
    """
    取得指定時區的當前時間。

    當使用者詢問「現在幾點」、「今天是幾號」、「現在是什麼時間」時呼叫此工具。
    timezone 參數使用 IANA 時區名稱，例如 Asia/Taipei、America/New_York、UTC。
    """
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        return now.strftime(f"%Y年%m月%d日 %H:%M:%S (%Z, UTC%z)")
    except pytz.UnknownTimeZoneError:
        return f"錯誤：找不到時區 '{timezone}'。請使用 IANA 時區名稱，例如 Asia/Taipei。"

if __name__ == "__main__":
    mcp.run()  # 預設使用 stdio 傳輸
```

安裝相依套件並測試：

```bash
pip install pytz

# 用 Inspector 測試，不需要 Claude Desktop
mcp dev time_server.py
```

### 第二步：加入真實 API 呼叫

讓我們再加一個工具，呼叫 wttr.in 這個免費的天氣 API：

```python
# weather_server.py — 完整的天氣工具
from mcp.server.fastmcp import FastMCP
from datetime import datetime
import httpx
import pytz
import json

mcp = FastMCP("天氣與時間服務")

@mcp.tool()
def get_current_time(timezone: str = "Asia/Taipei") -> str:
    """
    取得指定時區的當前時間。

    當使用者詢問現在時間、今天日期時呼叫此工具。
    timezone 使用 IANA 格式，預設為台北時間。
    """
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        return now.strftime(f"%Y年%m月%d日 %H:%M:%S (%Z)")
    except pytz.UnknownTimeZoneError:
        # 錯誤訊息對 AI 要有意義，讓 AI 能引導使用者修正
        return f"錯誤：找不到時區 '{timezone}'。請使用 IANA 時區名稱，例如 Asia/Taipei。"


@mcp.tool()
def get_weather(city: str) -> str:
    """
    查詢指定城市的當前天氣狀況。

    當使用者詢問天氣、溫度、是否下雨時呼叫此工具。
    city 參數接受城市名稱（英文或中文皆可），例如 Taipei、Tokyo、New York。
    如果使用者沒有指定城市，請先詢問城市名稱再呼叫工具。
    """
    try:
        # 使用 httpx 作同步 HTTP 呼叫（FastMCP 支援同步函式）
        # wttr.in 是免費的天氣 API，無需 API Key
        url = f"https://wttr.in/{city}?format=j1&lang=zh"

        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
            response.raise_for_status()  # 如果 HTTP 狀態碼是 4xx/5xx 就拋出例外

        data = response.json()

        # 從 API 回應中提取有用的資訊
        current = data["current_condition"][0]

        # 組合成人類可讀的字串回傳給 AI
        result = {
            "城市": city,
            "溫度（攝氏）": current["temp_C"],
            "體感溫度": current["FeelsLikeC"],
            "天氣描述": current["weatherDesc"][0]["value"],
            "濕度": f"{current['humidity']}%",
            "風速": f"{current['windspeedKmph']} km/h",
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except httpx.TimeoutException:
        # 超時錯誤：讓 AI 知道是網路問題，而不是城市名稱錯誤
        return f"錯誤：查詢 '{city}' 天氣超時。請稍後再試。"

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"錯誤：找不到城市 '{city}'。請確認城市名稱是否正確。"
        return f"錯誤：天氣 API 回應異常（HTTP {e.response.status_code}）。"

    except (KeyError, IndexError, json.JSONDecodeError):
        # API 回應格式異常
        return f"錯誤：解析 '{city}' 的天氣資料時發生問題，可能是城市名稱不支援。"

    except Exception as e:
        # 最後的防線：捕獲所有未預期的錯誤
        return f"錯誤：查詢天氣時發生未預期的問題：{str(e)}"


if __name__ == "__main__":
    mcp.run()
```

```bash
# 安裝相依套件
pip install httpx pytz

# 用 Inspector 測試
mcp dev weather_server.py
```

在 Inspector 裡測試 `get_weather`：
- 傳入 `{"city": "Taipei"}` → 應該看到台北天氣資料
- 傳入 `{"city": "不存在的城市XYZ"}` → 應該看到有意義的錯誤訊息
- 傳入 `{"city": "Tokyo"}` → 應該看到東京天氣資料

---

## 動手做：統計計算工具 Lab

現在換你了。讓我們把理論付諸實踐。

### 目標

建立一個 `calculate_stats` 工具，接受一組數字，回傳統計分析結果。

### 規格

```
函式簽名：calculate_stats(numbers: list[float]) -> str

輸入：一組浮點數的列表
回傳：包含以下資訊的字串
  - 數量（count）
  - 總和（sum）
  - 平均值（mean）
  - 最大值（max）
  - 最小值（min）
  - 標準差（std）

錯誤處理：
  - 如果列表是空的，回傳有意義的錯誤訊息
  - 不要 raise exception，直接回傳錯誤字串
```

### 起始程式碼

```python
# stats_server.py
from mcp.server.fastmcp import FastMCP
import json
import math

mcp = FastMCP("統計分析服務")

@mcp.tool()
def calculate_stats(numbers: list[float]) -> str:
    """
    計算一組數字的基本統計值，包括平均值、最大值、最小值和標準差。

    當使用者提供一組數字並要求統計分析、計算平均值、找最大最小值時呼叫此工具。
    numbers 是要分析的數字列表，例如 [1.5, 2.3, 4.7, 3.1]。
    """
    # 你的程式碼寫在這裡
    # 提示 1：用 if not numbers: 檢查空列表
    # 提示 2：標準差 = sqrt(sum((x - mean)^2 for x in numbers) / n)
    # 提示 3：用 json.dumps(result, ensure_ascii=False) 回傳
    pass


if __name__ == "__main__":
    mcp.run()
```

### 參考解答

```python
# stats_server.py — 完整版
from mcp.server.fastmcp import FastMCP
import json
import math

mcp = FastMCP("統計分析服務")

@mcp.tool()
def calculate_stats(numbers: list[float]) -> str:
    """
    計算一組數字的基本統計值，包括平均值、最大值、最小值和標準差。

    當使用者提供一組數字並要求統計分析、計算平均值、找最大最小值時呼叫此工具。
    numbers 是要分析的數字列表，例如 [1.5, 2.3, 4.7, 3.1]。
    如果使用者給的是逗號分隔的文字數字，請先解析後再呼叫此工具。
    """
    # 檢查空列表
    if not numbers:
        return "錯誤：請提供至少一個數字。numbers 列表不能是空的。"

    n = len(numbers)
    total = sum(numbers)
    mean = total / n
    maximum = max(numbers)
    minimum = min(numbers)

    # 計算標準差（母體標準差）
    variance = sum((x - mean) ** 2 for x in numbers) / n
    std = math.sqrt(variance)

    result = {
        "數量": n,
        "總和": round(total, 4),
        "平均值": round(mean, 4),
        "最大值": round(maximum, 4),
        "最小值": round(minimum, 4),
        "標準差": round(std, 4),
        "範圍（最大-最小）": round(maximum - minimum, 4),
    }

    return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
```

### 測試步驟

```bash
mcp dev stats_server.py
```

在 Inspector 裡測試這些情況：

```json
// 正常情況
{"numbers": [1.5, 2.3, 4.7, 3.1, 5.9]}

// 單個數字
{"numbers": [42.0]}

// 空列表（應該看到錯誤訊息，不應該崩潰）
{"numbers": []}

// 包含負數
{"numbers": [-5.0, -3.0, 0.0, 3.0, 5.0]}
```

### 連接到 Claude Desktop

當你確認 Inspector 測試通過，把 Server 加進 Claude Desktop：

```json
{
  "mcpServers": {
    "stats-server": {
      "command": "python",
      "args": ["/你的絕對路徑/stats_server.py"]
    }
  }
}
```

重啟 Claude Desktop，然後試試問：
- 「幫我計算 [85, 92, 78, 95, 88, 76, 91] 的統計值」
- 「這組數字的平均是多少：23.5, 18.2, 31.7, 25.0, 29.3」

---

## 重點回顧 📌

```
┌─────────────────────────────────────────────────────┐
│                  第二章重點回顧                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  • Tool 的四個組成部分：                            │
│    名稱、描述、輸入 Schema、回傳值                  │
│                                                     │
│  • FastMCP 裝飾器魔法：                             │
│    @mcp.tool() 從 Python 型別提示自動生成 Schema    │
│    docstring 自動成為工具的 description             │
│                                                     │
│  • 匯入方式：from mcp.server.fastmcp import FastMCP │
│                                                     │
│  • stdio 傳輸原理：                                 │
│    Claude Desktop 用 subprocess 啟動你的 Python     │
│    透過 stdin/stdout 管道傳輸 JSON-RPC 訊息         │
│    ⚠️ 不能在工具函式裡 print() 到 stdout           │
│                                                     │
│  • 設定 Claude Desktop：                            │
│    修改 claude_desktop_config.json                  │
│    args 一定要用絕對路徑                            │
│    修改後需重啟 Claude Desktop                      │
│                                                     │
│  • 錯誤處理原則：                                   │
│    工具函式不應該 raise exception                   │
│    錯誤要用有意義的字串回傳給 AI                    │
│    讓 AI 能引導使用者修正問題                       │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 常見問題 FAQ

**Q1：我修改了 server.py，但 Claude Desktop 好像沒有更新？**

Claude Desktop 在啟動時會 spawn 你的 Python 子程序，之後就不會重新讀取了。每次修改 `server.py` 後，都需要**完全重啟 Claude Desktop**（關閉應用程式，不只是關視窗），再重新開啟。

如果你是用 `mcp dev server.py` 測試，修改後直接 Ctrl+C 停止，重新執行即可。

**Q2：我的 Claude Desktop 看不到我的工具，怎麼辦？**

請按順序檢查：

1. `claude_desktop_config.json` 的路徑是絕對路徑嗎？
2. JSON 格式有沒有語法錯誤？（用 JSON linter 檢查）
3. `command` 指定的 `python` 是正確的 Python 嗎？試試改成 `python3` 或完整路徑 `/usr/bin/python3`
4. 在終端機手動執行 `python /path/to/server.py` 看看有沒有報錯
5. 重啟 Claude Desktop 了嗎？

**Q3：工具函式可以用 async/await 嗎？**

可以！FastMCP 完全支援 async 工具函式：

```python
@mcp.tool()
async def fetch_data(url: str) -> str:
    """從指定 URL 抓取資料"""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text
```

如果你的工具需要並行呼叫多個 API，async 會比較有效率。

**Q4：工具可以接受 Optional 型別嗎？**

可以，但有兩種寫法：

```python
# 方法一：用 Python 預設值（推薦）
def search(query: str, limit: int = 10) -> str:
    ...

# 方法二：用 Optional 型別提示（需要 from typing import Optional）
from typing import Optional
def search(query: str, limit: Optional[int] = None) -> str:
    actual_limit = limit if limit is not None else 10
    ...
```

推薦用方法一，比較簡潔，FastMCP 也處理得更好。

**Q5：我可以在一個 server.py 裡放多少個工具？**

技術上沒有限制，但有一個實務上的重要原則：**不要放超過 7 個工具**。

研究顯示，當工具數量超過 7 個，AI 模型在選擇正確工具時的準確率會下降（選擇過多導致認知負荷增加）。這個議題我們在第三章會深入討論，包含如何決定要不要把工具拆分成多個 MCP Server。

---

## 課後練習

### ⭐ 基礎練習：完成 Lab

確保你的 `calculate_stats` 工具通過所有測試情況，並成功連接到 Claude Desktop（或用 Inspector 完整測試）。

截圖以下兩個畫面：
1. Inspector 裡呼叫工具的成功結果
2. `numbers: []` 時的錯誤訊息（不是 Python traceback，是你自訂的錯誤字串）

### ⭐⭐ 進階練習：幣別匯率工具

使用 `https://api.exchangerate-api.com/v4/latest/USD`（免費，無需 API Key）建立一個 `convert_currency` 工具：

```
函式簽名：convert_currency(amount: float, from_currency: str, to_currency: str) -> str

範例：convert_currency(100.0, "USD", "TWD")
回傳：包含換算結果和當前匯率的字串
```

要求：
- 處理不支援的貨幣代碼（回傳有意義的錯誤）
- 處理網路超時
- 匯率精確到小數點後 4 位

### ⭐⭐⭐ 挑戰練習：帶快取的工具

匯率 API 不需要每次都查——同樣的匯率在 1 小時內不會有太大變化。

修改你的幣別匯率工具，加入記憶體快取：
- 第一次呼叫時查詢 API，把結果存在模組級別的 dict 裡
- 快取的有效期間是 60 分鐘
- 快取過期後自動重新查詢
- 在回傳字串裡標明是「即時匯率」還是「快取匯率（x 分鐘前）」

提示：`datetime.now()` 和 `timedelta` 可以幫你追蹤快取時間。

---

## 下一章預告

你現在已經能建立可以執行的 MCP 工具了。但有一個問題：**Claude 什麼時候會呼叫你的工具？**

我們在 Lab 裡用 Inspector 手動呼叫工具沒有問題。但在真實使用中，Claude 要靠 description 自己判斷什麼時候呼叫哪個工具。

第三章，我們要深入討論工具設計的藝術——一個好的 description 和一個壞的 description，可以讓同一個工具的使用率從 0% 變成 90%。這不是誇張，這是真實發生的事。

→ [第三章：工具設計的藝術](./ch03-tool-design.md)

← [第一章：你的 AI 不會用工具](./ch01-why-mcp.md)
