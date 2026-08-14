# Evidence-Based RCA Gap Analysis

> 評估 RootCause MCP 與「真正的 Evidence-Based RCA」的差距  
> 更新時間：2026-01-16

---

## 🎯 定義：什麼是 Evidence-Based RCA？

參考 Evidence-Based Medicine (EBM) 的標準：

```
Evidence-Based RCA = 
    (1) 每個 Cause 必須有 Evidence 支持
  + (2) Evidence 有來源追蹤與品質評估
  + (3) Causation 驗證基於 Evidence（非 AI 臆測）
  + (4) Report 包含 Evidence Summary & Gap Analysis
```

---

## 📊 現況評估

### ✅ Level 1: Evidence Collection (已實作 80%)

| 功能 | 狀態 | 說明 |
|------|------|------|
| Cause.evidence | ✅ 已實作 | `List[str]` 可附加證據清單 |
| WhyNode.evidence | ✅ 已實作 | 5-Why 每層可附加證據 |
| Fishbone export | ✅ 已實作 | 匯出時包含 evidence |
| Why Tree export | ✅ 已實作 | 匯出時包含 evidence |

**Gap:**
- ❌ Evidence 是自由文字，無結構化
- ❌ 無來源追蹤（哪個檔案、哪一行、何時產生）
- ❌ 無證據類型分類（文件/檢驗/觀察/訪談）

---

### ⚠️ Level 2: Evidence Linking (實作 30%)

| 功能 | 狀態 | 說明 |
|------|------|------|
| Evidence → Cause | ⚠️ 部分實作 | 一個 Cause 可有多個 Evidence |
| Evidence → Multiple Causes | ❌ 未實作 | 無法追蹤「一個 Evidence 支持多個 Cause」 |
| Evidence Graph | ❌ 未實作 | 無視覺化 Evidence 網路 |
| Evidence Consistency Check | ❌ 未實作 | 無檢查 Evidence 是否矛盾 |

**Gap:**
- ❌ Evidence 不是 first-class entity（只是 Cause 的附屬屬性）
- ❌ 無 Evidence-Cause Many-to-Many 關聯
- ❌ 無 Evidence 之間的時序關係

---

### ❌ Level 3: Evidence Quality Assessment (實作 0%)

| 功能 | 狀態 | 缺失 |
|------|------|------|
| Evidence Strength Grading | ❌ | Strong / Moderate / Weak |
| Evidence Source Reliability | ❌ | Primary source vs Hearsay |
| Evidence Completeness Check | ❌ | 是否有 critical gap？ |
| Evidence Conflict Detection | ❌ | 證據間是否矛盾？ |
| Chain of Custody | ❌ | 誰收集？何時？如何驗證？ |

**Example (理想狀態):**

```python
Evidence(
    id="EVD-001",
    content="護理紀錄：08:30 BP 75/40",
    source="nursing_flowsheet.csv:Line_42",
    timestamp="2024-08-10T08:30:00Z",
    type=EvidenceType.DOCUMENT,
    strength=EvidenceStrength.STRONG,  # Primary source
    collected_by="RN_CHEN",
    verified=True,
    supports_causes=["CAUSE-003", "CAUSE-007"]
)
```

**Current State:**

```python
Cause(
    description="...",
    evidence=["護理紀錄：08:30 BP 75/40"]  # ← 只是字串
)
```

---

### ❌ Level 4: Evidence-Based Causation (實作 20%)

| 功能 | 狀態 | 說明 |
|------|------|------|
| Counterfactual Testing | ✅ 已實作 | 4 準則驗證 |
| Evidence Citation in Verification | ❌ 未實作 | 驗證時未要求 cite evidence |
| Evidence-Based Confidence Score | ❌ 未實作 | Confidence 是 AI 給的，非基於證據數量/品質 |
| Bradford Hill Full Criteria | ❌ 未實作 | 只實作 4 個，完整有 9 個 |

**Gap:**

目前的 `rc_verify_causation` 是這樣：

```python
# Current
rc_verify_causation(
    cause="未識別HOCM",
    effect="PEA arrest"
)
→ AI 判斷: "Temporality: PASS"  # ← 但沒要求 evidence

# Evidence-Based (理想)
rc_verify_causation(
    cause="未識別HOCM",
    effect="PEA arrest",
    evidence_temporality=["EVD-001: Pre-op echo 3y ago", "EVD-002: Syncope 2y ago"],
    evidence_necessity=["EVD-003: 若識別HOCM會選spinal, 避免sympathectomy"],
    evidence_mechanism=["EVD-004: 術前文獻 HOCM + GA = LVOT obstruction"]
)
→ Evidence-grounded: "Temporality: PASS (supported by 2 strong evidences)"
```

---

### ❌ Level 5: Evidence Summary & Reporting (實作 10%)

| 功能 | 狀態 | 缺失 |
|------|------|------|
| Export includes Evidence | ✅ 已實作 | Markdown/JSON 含 evidence |
| Evidence Summary Table | ❌ 未實作 | 無彙整表格 |
| Evidence-Cause Matrix | ❌ 未實作 | 哪些 Evidence 支持哪些 Cause |
| Evidence Gap Analysis | ❌ 未實作 | 哪些 Cause 缺乏證據支持 |
| Evidence Timeline | ❌ 未實作 | 事件時序圖 |
| Evidence Quality Dashboard | ❌ 未實作 | 證據品質總覽 |

**Example (理想 Report):**

```markdown
## Evidence Summary

| Evidence ID | Type | Timestamp | Strength | Supports Causes |
|-------------|------|-----------|----------|-----------------|
| EVD-001 | Document | 08:30 | Strong | CAUSE-003, CAUSE-007 |
| EVD-002 | Lab | 08:19 | Strong | CAUSE-007 |
| EVD-003 | Observation | 08:12 | Moderate | CAUSE-003 |

## Evidence-Cause Matrix

|              | CAUSE-001 | CAUSE-002 | CAUSE-003 |
|--------------|-----------|-----------|-----------|
| **EVD-001**  | ✅        | -         | ✅        |
| **EVD-002**  | -         | ✅        | ✅        |
| **EVD-003**  | -         | -         | ⚠️        |

Legend: ✅ Strong support, ⚠️ Weak support, - No relation

## Evidence Gap Analysis

⚠️ **CAUSE-004**: "系統性因素" has NO evidence support (純推測)
⚠️ **CAUSE-005**: Only 1 weak evidence (需補強)
✅ **CAUSE-001**: 3 strong evidences (well-supported)
```

---

## 🎯 Roadmap: 如何達成 Evidence-Based

### Phase 1: Evidence Entity 強化 (1 週)

**目標**: Evidence 從「字串」升級為「First-Class Entity」

```python
# New Domain Entity
class Evidence(Entity):
    id: EvidenceID
    content: str
    source: str  # "nursing_flowsheet.csv:Line_42"
    timestamp: Optional[datetime]
    type: EvidenceType  # DOCUMENT, LAB, OBSERVATION, INTERVIEW
    strength: EvidenceStrength  # STRONG, MODERATE, WEAK
    collected_by: Optional[str]
    verified: bool
    
class EvidenceType(str, Enum):
    DOCUMENT = "document"        # 文件證據
    LABORATORY = "laboratory"    # 檢驗報告
    OBSERVATION = "observation"  # 臨床觀察
    INTERVIEW = "interview"      # 訪談紀錄
    IMAGING = "imaging"          # 影像檢查
    MONITOR = "monitoring"       # 監視器數據

class EvidenceStrength(str, Enum):
    STRONG = "strong"      # Primary source, 可驗證
    MODERATE = "moderate"  # Secondary source, 合理
    WEAK = "weak"          # Hearsay, 需補強
    CONFLICTING = "conflicting"  # 與其他證據矛盾
```

**New Tools:**
- `rc_add_evidence` - 新增證據（結構化）
- `rc_link_evidence_to_cause` - 關聯證據與原因
- `rc_assess_evidence_strength` - AI 輔助評估證據強度

**Impact:**
- Database schema 更新
- Cause/WhyNode 改為參照 Evidence ID（而非內嵌字串）

---

### Phase 2: Evidence Quality Layer (2 週)

**目標**: 建立證據品質評估機制

```python
class EvidenceQualityService:
    def assess_reliability(self, evidence: Evidence) -> ReliabilityScore:
        """評估證據可靠性"""
        
    def detect_conflicts(self, evidences: List[Evidence]) -> List[Conflict]:
        """偵測證據間矛盾"""
        
    def check_completeness(self, cause: Cause) -> CompletenessReport:
        """檢查證據完整性"""
        
    def grade_strength(self, evidence: Evidence) -> EvidenceStrength:
        """評估證據強度"""
```

**New Tools:**
- `rc_check_evidence_conflicts` - 檢查證據矛盾
- `rc_evidence_gap_analysis` - 找出證據缺口
- `rc_grade_evidence_quality` - 整體品質評估

---

### Phase 3: Evidence-Based Verification (1 週)

**目標**: Causation 驗證強制引用證據

```python
# Enhanced rc_verify_causation
rc_verify_causation(
    cause="未識別HOCM",
    effect="PEA arrest",
    evidence_ids=["EVD-001", "EVD-002", "EVD-003"],  # ← 必須提供
    criteria=["temporality", "necessity", "mechanism"]
)
→ 回傳中包含每個準則的證據支持強度
```

**Bradford Hill 9 Criteria 完整實作:**

| Criteria | 準則 | 說明 |
|----------|------|------|
| 1. Strength | 關聯強度 | Effect size 大小 |
| 2. Consistency | 一致性 | 多個證據是否一致 |
| 3. Specificity | 特異性 | 因果關係是否特定 |
| 4. **Temporality** | **時序性** | ✅ 已實作 |
| 5. Biological Gradient | 劑量反應 | 因增加則果增加 |
| 6. Plausibility | 合理性 | 有生物機轉解釋 |
| 7. Coherence | 一致性 | 與現有知識吻合 |
| 8. Experiment | 實驗證據 | 有實驗支持 |
| 9. Analogy | 類比性 | 類似案例支持 |

---

### Phase 4: Evidence-Based Reporting (1 週)

**目標**: Report 包含完整 Evidence Analysis

**New Sections in Report:**
1. Evidence Summary Table
2. Evidence-Cause Matrix
3. Evidence Timeline (Mermaid Gantt Chart)
4. Evidence Gap Analysis
5. Evidence Quality Dashboard

**New Tools:**
- `rc_generate_evidence_report` - 證據專屬報告
- `rc_export_evidence_timeline` - 時序圖
- `rc_export_evidence_matrix` - 關聯矩陣

---

## 📈 實作優先序

| Priority | Phase | 工作量 | Impact | 說明 |
|----------|-------|--------|--------|------|
| **P0** | Phase 1 | 1 週 | 🔥 High | 無此基礎無法前進 |
| **P1** | Phase 2 | 2 週 | 🔥 High | 品質評估是核心價值 |
| **P2** | Phase 3 | 1 週 | 🟠 Med | 強化現有功能 |
| **P3** | Phase 4 | 1 週 | 🟢 Low | 錦上添花 |

**總計**: 5 週可達成 Evidence-Based RCA

---

## 🎯 結論

### 當前狀態評分

| 層級 | 完成度 | 說明 |
|------|--------|------|
| Evidence Collection | 80% | 可附加證據，但無結構 |
| Evidence Linking | 30% | 缺乏 Entity 與關聯 |
| Quality Assessment | 0% | 完全缺失 |
| Evidence-Based Verification | 20% | 有框架但無證據引用 |
| Evidence Reporting | 10% | 只有基礎匯出 |
| **Overall** | **28%** | **尚未達成 Evidence-Based** |

### 回答問題

> **Q: "Evidence-Based Root Cause" 這樣描述會比較好嗎？**

✅ **YES** - 更專業、更符合醫學語言、更能凸顯與 AI 直接推理的差異。

> **Q: 但具體我們離這樣還有多遠？**

📊 **28% 完成度**，距離真正的 Evidence-Based 還需要：
- **5 週開發** (依上述 Phase 1-4)
- **核心缺失**: Evidence 不是 First-Class Entity
- **可用但不完整**: 現在是「Evidence-Aware」而非「Evidence-Based」

### 建議

#### Option A: 現在就宣稱 "Evidence-Based" ❌

**風險**: 過度承諾 (Over-promise)
- 目前只有 28% 的 Evidence-Based 功能
- 可能被專家質疑

#### Option B: 誠實表述 + Roadmap ✅

**推薦**: 

```markdown
## 🎯 Vision

Transform AI insights into **evidence-grounded**, auditable organizational intelligence.

**Current State**: Evidence-Aware (tools support evidence attachment)
**Roadmap**: Evidence-Based (5-week plan for full EBM-grade evidence management)
```

**優點**:
- 誠實但不自貶
- 展示清晰 roadmap
- 承諾可實現

#### Option C: 先實作 Phase 1 再宣稱 ✅

**推薦**: 花 1 週實作 Evidence Entity，然後：

```markdown
## 🎯 Transform AI Insights into Evidence-Based Organizational Intelligence

✅ **Evidence-First Design**: Every cause must be supported by structured evidence
✅ **Source Traceability**: Track evidence origin (file, line, timestamp)
✅ **Quality Assessment**: AI-assisted evidence strength grading
⏳ **Coming Soon**: Evidence conflict detection, gap analysis, timeline visualization
```

---

## 📋 Action Items

- [ ] 決定是否採用 "Evidence-Based" 表述
- [ ] 若採用，需執行 Phase 1 (Evidence Entity)
- [ ] 更新 README.md 反映真實狀態
- [ ] 更新 ROADMAP.md 加入 Evidence-Based 計畫

---

**結論**: 我們有清晰的 roadmap 可以達成 Evidence-Based RCA，但現在誠實地說是「Evidence-Aware」更準確。
