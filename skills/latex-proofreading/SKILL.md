---
name: latex-proofreading
description: Use when proofreading a LaTeX manuscript, journal proof, or camera-ready paper for language and textual defects - grammar, spelling, collocation, punctuation, terminology consistency, numeric consistency between text and tables, cross-reference integrity, citation/DOI and author-name errors, or journal format compliance. Also use when asked not to fix the paper but to report findings, or when asked whether a manuscript "reads like AI wrote it". Symptoms that signal this skill applies: "校稿", "检查语病", "有没有拼写错误", "proofread my .tex", "check my references", "verify the DOIs", "the proof stage corrections", a .tex file plus an author asking what is wrong with it.
---

# LaTeX 校稿

## 这个技能解决什么

给已投稿/在校稿阶段的 LaTeX 论文做语言与文本层面的校对，产出一份**作者可逐条把关**的问题清单，并在作者圈选后**安全地**应用修改。

**不是**审稿：不评价方法学、创新性、实验设计、数学推导是否正确。

**这不是"通读一遍挑错"。** 实测：让一个没有本技能的 agent 单遍通读一篇约 1700 行的论文，
它只找到真实问题总数的**约一成**，而且同时犯下两个会污染文件的错误。
本技能的价值在于方法、验证手段和安全机制。

## 铁律

### 1. 不许假设 LaTeX 宏的渲染结果

`\eqref{...}` 在不同模板里渲染不同。在 Elsevier 的 neptune 模板里它输出 **`Eq. (7)`**，不是 `(7)`。在它前面补 "Equation" 会排成 **"Equation Eq. (7)"**。

**基线测试中，一个没有本技能的 agent 独立犯下了完全相同的错误**，
还给出了自信的理由（"这个名词上文刚出现过，此处显然是漏掉了"）。

改任何引用措辞前，先确定宏输出什么：

```bash
# 有排好版的 PDF：渲染对应页，用眼睛看
python scripts/render.py proof.pdf --page 4 --out p4.png
# 没有 PDF：去模板文件里找宏定义
grep -rn "eqref" *.cls *.sty 2>/dev/null
```

### 2. 改动要过「与文档自身基线的一致性」这一关

统计量是判据，直觉不是。**先数，再改。**

一篇全文 em dash 出现 0 次的论文，你加进去 3 个 `---`，那就是突兀的——不管每个破折号单看是否"语法正确"。无技能的基线 agent 和有技能的我，都栽在这里。

```bash
python scripts/scan.py paper.tex --dashes     # 改之前数一次
# 改完再数一次，确认没有意外引入
```

同理适用于：术语的连字符写法、大小写风格、引号样式。

注意区分两类情形：
- **没有规范答案的纯风格选择**（引号用直引号还是弯引号、标题大写还是句首大写）→ 向文档自身的多数写法靠拢，不要引入新风格。
- **有规范答案的写法**（作定语时的连字符）→ 看哪个更规范，**不要数数量**。见下一条。

### 3. 「少数服从多数」是错的判据

术语统一的方向要看**哪个更规范**，不是哪个出现得多。

实例：`scale-factor error` 少数几次、`scale factor error` 多数次。作定语时带连字符更规范，
所以正确结论是**不改**——为凑数量去去掉带连字符的那几处，是"向下对齐"。

### 4. 改文件必须原子化

**先备份，再断言，全通过才写盘。**

```bash
cp paper.tex paper.tex.bak
python scripts/apply.py paper.tex edits.py        # 任一条断言失败就整体中止，文件零字节变化
```

不要用逐条 Edit、不要用全局 find-replace。基线 agent 直接改文件、无备份、无断言；一旦错配就污染了作者的手稿。实测中这套断言机制拦下过两次真实错配。

### 5. 改完必须回读整句，不能只看片段

基线的失败样本：把 `deviates from its nominal range` 改成 `deviate from their nominal range`，动词改了、物主代词改了，**但主语仍是单数** —— `the mean deviation ... deviate` 依然不一致。改一半比不改更糟。

每一处替换后，回读整个句子。

### 6. 出版社生成的标识符不要动

`\ubrk`（断行点）、`\?{}`（出版社"请核对"标记）、`\rvtissn*`（期刊名宏）、段落外的 `{...}` 分组、以及**标签名**（如 `\xlabel{Fig_Comparision_Plot}` 里那个拼错的 Comparision）—— 这些通常是排版系统产出，可能已被写进 XML ID，改动有断链风险。

**单独列一节报告并注明"可能不是你造成的"，不要给修改建议。** 基线 agent 擅自全局重命名了 11 处标签。

### 7. 误报比漏报贵

作者要逐条判断每一条建议；一条错的会消耗信任，十条错的会让整份报告被丢弃。

把握 < 90% 的，**降级到"润色建议"或直接丢弃**。确认不了的，写"未能核实"，不要含糊带过。

### 8. 内容层面的缺失只报告，不代笔

符号未定义、公式与文字不符、结论与数据矛盾——这些需要作者的专业判断，改动后语义由谁负责要说清楚。报，但不要替他们写。

## 六阶段工作流

**P0 建基线**

**先问清一件事：备份放哪。** 作者常会说「目录里只有这几个文件，请只操作它们」。
在工作目录里新建 `.bak` / `.sha256` 可能违反这个约束——**默认放到临时目录**，或先征得同意：

```bash
# 默认：备份到临时目录，不污染作者的目录
BAK=$(mktemp -d)/paper.bak
cp paper.tex "$BAK" && sha256sum paper.tex | tee "$BAK.sha256"

# 只有作者同意时，才在工作目录里建备份
# cp paper.tex paper.tex.bak && sha256sum paper.tex > paper.sha256
```

```bash
python scripts/selftest.py paper.tex    # 换新环境先跑一次，确认脚本可用
```

确认：文件编码、换行符（CRLF/LF）、期刊与阶段（定稿校样？投稿稿？）。
若目录里有出版社或投稿系统导出的元数据文件、以及排好版的 proof PDF，**读它们**——
能确定期刊名与稿件是否已被录用，这直接决定你能改多少。

**P1 机械扫描 + 自己通读一遍**
```bash
python scripts/scan.py paper.tex          # 破折号/术语变体/重复词/双空格/异常复数
python scripts/xref.py paper.tex          # 悬空引用/重复标签
python scripts/compliance.py paper.tex    # highlight 字符数/摘要词数/关键词数
python scripts/spell.py paper.tex         # 词级拼写（未知≠错误，须逐条回读）
```
扫描只覆盖能规则化的部分。自己完整读一遍——但要知道这一遍的召回率很低（见开头）。

**P1 还要顺手做两件容易被整个跳过的事**（详见 `references/checks.md` 的 H、I 两节）：

- **查作者与单位**：机构英文名是否完整（有上级单位的要带）、标点、邮编、
  `\author[N]` ↔ `\affiliation[N]` 对应、通讯作者标记、贡献声明姓名集合是否一致。
  **"几处 affiliation 里两处带上级、一处不带"是最典型的漏写。** 机构名是专有名词，联网核。
- **查"改了一半"**：拿到的稿子可能已经被别人改过，留下双谓语这类半截改动。
  `grep -nE '\b(is|are) [a-z]+ed\b.*\b(is|are) [a-z]+ed\b' paper.tex`
  生成候选后**逐条人工判断**——并列句完全合法，命中≠错误。

`spell.py` 补的是"非词"错误这一类 —— 它便宜、可复跑，值得每次改稿后都跑一遍。
但它的输出**必须逐条回读上下文**：宏包选项、`tabular` 列格式、出版社标识符、
**你所在领域的术语与专有名词**都会命中。词典判"未知"不等于文章写错了。

**P2 分区并行，多路独立细读**

按行段切 2–3 路，派给不同 agent（`superpowers:dispatching-parallel-agents`）。每路的指令必须包含：

- 只报**能定位**的问题，必须给**逐字原文引用**（下游要 grep 回查）
- 分类标注：语法 / 拼写 / 标点 / 单复数 / 时态 / 搭配 / 冗余 / 中式英语 / 一致性
- 严格区分 `ERROR`（确定错）与 `STYLE`（可改可不改）；把握 < 90% 一律 STYLE
- **不要碰**：`\ubrk`、`\?{}`、`\rvtissn*`、`{...}` 分组、宏本身、公式内部、参考文献条目
- 明说"**如果这个区域是干净的，就说干净**"——否则 agent 会为了凑数硬报

给每路明确的行范围。让它们各自读，不要共享上下文。

**有两种注意力模式，必须分工，不能只派一种：**

| 模式 | 指令要点 | 擅长发现 | 系统性盲区 |
|---|---|---|---|
| **深挖式** | "找语义与结构层面的问题：悬垂修饰、平行结构、符号一致性、引用指向" | 结构错误、逻辑不搭 | **低级错误**（a/an、拼写、单复数）——它们"不值得注意" |
| **扫读式** | "逐词扫过去，专找 a/an、拼写、单复数、明显搭配错误；不要分析句子结构" | a/an、拼写、简单搭配 | 结构错误 |

**实证**：案例里 `a effect`（应为 `an effect`）这个 a/an 错误，
在三路深挖式细读 + 一遍人工通读 + 两轮补充排查中**全部漏掉**，
最后是被一个"没有方法论、只是随便读读"的对照 agent 发现的。
深挖会让人（和 agent）跳过"太简单"的文本——必须专门派一路做扫读才能补上。

**P3 逐条回查（防误报的闸门）**

把各路结果取并集，**每一条**都用 grep 回到原文验证：
- 行号对不对
- 引用片段是否逐字一致
- 是不是出版社标记

不符的直接丢弃。这一步会砍掉相当一部分。

**P4 分类报告**（见下节）

**P5 作者圈选后应用**
```bash
python scripts/apply.py paper.tex edits.py --dry-run   # 先干跑
python scripts/apply.py paper.tex edits.py             # 再写盘
```
edits.py 格式：`EDITS = [(编号, 旧串, 新串, 期望出现次数), ...]`

**P6 改后全量回归**
```bash
diff <(sed 's/\r$//' paper.tex.bak) <(sed 's/\r$//' paper.tex)   # 改动是否符合预期
python scripts/scan.py paper.tex          # 没有引入新问题
python scripts/xref.py paper.tex          # 结构与改动前一致
```
结构不变性：总行数、花括号平衡、`\begin`/`\end` 配对数、标签与引用数 —— 改前后应完全一致。

## 输出规范

报告分节，作者要能一眼看出「哪些必须改」：

```
A. 硬错误          —— 确认是错的，建议必改
B. 润色建议        —— 可改可不改，作者取舍
C. 数字一致性      —— 摘要/正文/表格互相对账
D. 交叉引用        —— 引用能不能解析，指向对不对
E. 参考文献        —— DOI、作者名、年份卷期
F. 标记异常        —— 出版社产出，仅提示
```

表格列固定为：`编号 | 行号 | 逐字原文 | 类别 | 严重度 | 说明 | 建议改法`
严重度只有两档：`ERROR` / `STYLE`。

**每条硬错误都要给出可直接套用的修改后原文。**

改动应用后，另出一份 diff 对照表：`行 | 编号 | 改动前 | 改动后 | 说明`，只列片段、不贴整行。

## 红旗 —— 出现这些就停下来重做

- 我准备在 `\eqref`/`\ref` 前加 "Equation"/"equation" → **先去确认宏输出什么**
- 我要加 em dash / 改标点风格 → **先数一遍原文的基线**
- 我在用"哪个写法多"来决定术语统一方向 → **去查哪个更规范**
- 我要直接改文件 → **备份了吗？断言了吗？**
- 我只检查了改动片段，没读整句 → **回读整句**
- 我在改标签名、`\ubrk`、`\?{}` → **这多半是出版社的，别碰**
- 这一条我只有七成把握却标了 ERROR → **降级或丢弃**
- 我通读了一遍觉得"差不多了" → **实测这一遍只能找到约 10% 的问题**

## 配套文件

- `references/checks.md` — 九大类检查清单（A–I），每项含「怎么验」。
  **H = 作者与单位**（最易整个漏掉），**I = 「改了一半」的系统性检法**
- `references/pitfalls.md` — 宏渲染、CrossRef 数据偏差、环境陷阱
- `references/case-study.md` — **合成案例**：每条铁律的实证来源（RED/GREEN 对照）

下面所有 `scripts/xxx.py` 的路径**都相对于本技能目录**。
先 `cd` 到本技能目录，或写成绝对路径。

脚本一览（全部无参数运行即打印用法）：

| 脚本 | 用途 | 需要联网 |
|---|---|---|
| `scan.py` | 破折号 / 术语变体 / 重复词 / 双空格 / 异常复数 | 否 |
| `xref.py` | 悬空引用 / 重复标签 | 否 |
| `compliance.py` | highlight 字符数 / 摘要词数 / 关键词数 | 否 |
| `consistency.py` | 数值定位（`--find`）/ 百分比复算（`--improve`） | 否 |
| `spell.py` | 词级拼写检查（`pyspellchecker`，正文/文献分区） | 否 |
| `render.py` | PDF 渲染成图片，做渲染级验证（需 `pdftoppm`） | 否 |
| `refs.py` | DOI 与作者名核对 | **是**（CrossRef API） |
| `apply.py` | 原子化替换 | 否 |
| `selftest.py` | 自检：脚本可用性 + `apply.py` 原子性 | 否 |

```bash
python scripts/refs.py paper.tex --all      # DOI + 年份卷期 + 作者名
python scripts/spell.py paper.tex           # 词级拼写（未知 ≠ 错误，须逐条回读）
```

**`spell.py` 的定位**：它只抓"非词"错误（`recieve` / `teh` / 字母转置），
抓不到"用词错误"（`form`↔`from`、`discrete`↔`discreet`）。所以它是
深挖式/扫读式细读**之外的第四个正交视角**，不是替代。命中项**必须逐条回读上下文** ——
宏包选项、`tabular` 列格式、出版社标识符、你所在领域的术语都会命中。

它**不内置任何学科的词汇**（避免把技能绑死在某个领域）。你自己的领域词
用 `--words my-words.txt` 传入，或写成论文同目录的 `paper.tex.words` 自动加载。
