# System Patterns

> 📌 此檔案記錄專案中使用的模式和慣例，新模式出現時更新。

## 🏗️ 架構模式

### DDD 分層架構
```
Presentation → Application → Domain ← Infrastructure
```
- Domain 層不依賴任何外層
- Repository Pattern 為唯一資料存取方式

### 憲法-子法層級
```
CONSTITUTION.md (最高原則)
  └── .github/bylaws/ (子法)
        └── .claude/skills/ (實施細則)
```

## 🛠️ 設計模式

### Repository Pattern
- 介面在 Domain 層定義
- 實作在 Infrastructure 層

### Strategy Pattern
- 用於取代複雜條件判斷
- 實例：ShippingStrategy, PaymentStrategy

### Command Pattern (CQRS)
- Commands: 寫入操作
- Queries: 讀取操作

## 📝 命名慣例

| 類型 | 慣例 | 範例 |
|------|------|------|
| Entity | 名詞單數 | `User`, `Order` |
| Value Object | 描述性名詞 | `Email`, `Money` |
| Repository | `I{Entity}Repository` | `IUserRepository` |
| Use Case | 動詞 + 名詞 | `CreateOrder` |
| Domain Event | 過去式 | `OrderCreated` |

## 📚 程式碼慣例

### Python
- 使用 `snake_case` 命名
- 檔案名全小寫
- 類別使用 `PascalCase`
- 優先使用 type hints

### 測試
- 測試檔案以 `test_` 開頭
- 測試類別以 `Test` 開頭
- 使用 pytest markers 分類

---
*Last updated: 2025-12-15*

## 認知層 MCP (Cognitive Layer MCP)

透過 ThinkingStep entity 和 5 個 thinking tools (rc_think_aloud, rc_reflect, rc_identify_gaps, rc_challenge_assumption, rc_get_thinking_chain) 記錄 Agent 的思考過程，不只是結果。強制 Agent 暴露「為什麼」而非僅「是什麼」。核心設計：rc_propose_hypothesis 有 7 個 required fields（clinical_reasoning, differential_diagnoses_considered, uncertainty_factors, confidence_rationale），Agent 不填就無法呼叫。

### Examples

- rc_propose_hypothesis 強制填寫 7 個思考欄位
- ThinkingStep 記錄 alternatives_considered（被拒絕的選項）
- rc_reflect 讓 Agent 識別自己的認知偏差
