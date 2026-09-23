# 已知的坑

这些都是**实际踩过**的，不是理论上的可能。

---

## LaTeX

### `\eqref` / `\ref` 渲染什么，取决于模板

在 Elsevier 的 neptune 模板里，`\eqref{...}` 输出的是 **`Eq. (7)`**，自带 "Eq." 前缀。在它前面补 "Equation" 会排成 **"Equation Eq. (7)"**。

**源码里看不出来**——你必须渲染，或者去类文件里找定义。

```bash
python scripts/render.py proof.pdf --page 4 --dpi 400 --crop 250,2400,1600,300
grep -rn 'eqref' *.cls *.sty 2>/dev/null
```

### `\_` 是字面下划线，不是智能占位符

表格里写 `& \_` 会渲染成一个**位于基线以下的孤立下划线**，和其他单元格格格不入。除非模板真的特殊处理它，否则它就是个下划线字符。

放大确认（实测有效）：
```bash
python scripts/render.py proof.pdf --page 4 --dpi 1200 --crop 2400,1900,320,130
```

### `--` 与 `---` 是两种东西

- `--` = en dash，用于**复姓连接**（`Runge--Kutta`、`Navier--Stokes`）和数值范围
- `---` = em dash，用于插入语和停顿

**不要为了"统一破折号风格"去动复姓连接。** 那会让 `Runge--Kutta` 变成一个别的东西。

### 按行过滤 LaTeX 会漏掉绝大部分内容

不要写 `if '\\' in line: continue` —— LaTeX 论文里几乎每行都有 `\citep{}`。要**把命令剥掉再分析**，而不是跳过整行。

剥命令时注意：

| 陷阱 | 后果 |
|---|---|
| `\?{XYZ}` 只匹配 `?{XYZ}` 而不吃反斜杠 | 留下孤立 `\`，随后被"删命令"那步连单词一起删掉 |
| 拼接正则用 `BS + r'end\{...\}'` | `\e` 是非法转义，直接抛异常。要用 `re.escape(BS + 'end')` |
| 剥完命令后 `\newtheorem{theorem}{Theorem}` 变成 "theorem Theorem" | 误报为重复词。要排除导言区与定义类命令 |
| 排除区域时用 `'\n'` 填充 | 文件是 CRLF 时这些行不会被切分，**后续行号整体前移**。要用文件实际的换行符 |

### 表格收尾

本模板末行不写 `\\`，由 `\botline` 收尾。这是**正常写法**，不是缺漏。别的模板可能不同，先确认再报。

### 不要把脚本命名为标准库模块名

把数字一致性脚本命名为 `numbers.py` 会**遮蔽 Python 标准库的 `numbers` 模块**。
因为脚本所在目录排在 `sys.path` 最前，同目录下的任何脚本一旦 `import statistics`，
就会走进 `statistics → fractions → decimal → from numbers import Number` 这条链，
拿到你自己的 `numbers.py`，然后抛 `AttributeError: module 'numbers' has no attribute 'Number'`。

**症状**：一个完全不相关的脚本（比如 `scan.py`）突然报 `decimal` / `fractions` 的导入错误。

**避开**：不要用 `numbers.py`、`types.py`、`json.py`、`code.py`、`string.py`、`token.py`、`copy.py` 等标准库名。
本技能里它叫 `consistency.py`，就是踩过之后改的名。

---

## CrossRef / DOI 核对

CrossRef 是权威源，但它的数据有已知偏差。**自动比对报出的差异，大部分不是 bib 的错。**

| 现象 | 真相 | 处理 |
|---|---|---|
| `issued` 年份与 bib 年份不同 | `issued` 常是**在线首发日期**，不等于卷期所属年份 | 只有「bib 年份与**卷号所属年份**矛盾」才是真错。实测里报出的年份差异，多数属于前者 |
| 姓名字段里塞着全名 | CrossRef 偶尔把 `Jane Q. Doe` 整个放进 `family` | 人工看，bib 多半是对的 |
| 姓名顺序颠倒 | CrossRef 偶尔记成 `Doe, Jane`（实际是 `Jane Doe`） | 人工看，bib 多半是对的 |
| 给名只有首字母 | CrossRef 元数据不全 | 不是错误 |
| DOI 返回 404 | CNKI 学位论文、部分会议论文不在 CrossRef 库内 | **正常现象**，不代表引用错误 |
| 同名作者导致逐对比较误报 | 一篇文献里有两位同姓作者时，逐对匹配会错配 | **改用集合比较**（`refs.py` 已如此实现） |
| 题名里带 `<sub>2</sub>`、`<i>t</i>` | CrossRef 存的是 JATS 标记 | 比较前必须剥 HTML 标签 |
| 题名里带 `\?{...}` 出版社标记 | bib 侧 | 比较前必须剥出版社标记，**且正则要连反斜杠一起吃掉** |

**结论**：DOI 核对的价值在于「确认 DOI 没指向另一篇文献」，而不是「逐字比对题名」。相似度阈值设 0.75 左右，低于此值才报，其余交给人工看提示。

---

## 环境

### Windows Git Bash 的 heredoc 会吞反斜杠

用 `python - <<'EOF' ... EOF` 传含反斜杠的代码会被静默破坏（`\\` 变 `\`），报出莫名其妙的 `SyntaxError`。

**用 Write 工具把脚本写成文件再运行**，不要用 heredoc 传代码。

### 控制台编码

Windows 控制台默认 GBK，Python 输出中文会乱码。脚本开头加：

```python
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
```

（第二行容易忘，但 `raise SystemExit(__doc__)` 走的是 stderr。）

### 读写文件不要用文本模式

`open(path, encoding='utf-8')` 会做换行转换（CRLF → LF），写回时可能改变文件换行符。

**一律二进制读写**：
```python
raw = open(path, 'rb').read()
text = raw.decode('utf-8')
nl = '\r\n' if raw.count(b'\r\n') else '\n'
...
open(path, 'wb').write(text.encode('utf-8'))
```

### 可用工具情况

| 工具 | 说明 |
|---|---|
| `pdftoppm` / `pdfinfo` / `pdftotext` | TeXLive 或 poppler 自带，通常已有 |
| `pypdf` / `PyPDF2` / `fitz` | **不需要** —— `render.py` 走 `pdftoppm`，不必装这些 |
| `aspell` / `hunspell` / `ispell` | **不需要** —— 见下 |
| `pyspellchecker`（Python 包） | 仅 `spell.py` 需要：`pip install pyspellchecker` |
| `api.crossref.org` | 仅 `refs.py` 需要，可公开访问 |

所以 PDF 只能靠 `pdftoppm` 渲染成图片看。

拼写检查**是有工具的**：`scripts/spell.py`，基于 `pyspellchecker`（Python 包自带英文词典，
**不需要**系统级 `aspell` / `hunspell`）。先剥掉 LaTeX 命令与数学模式再逐词比对，
正文与参考文献分区报告。

但它**只抓"非词"错误**（`recieve` / `teh` / 字母转置），
**抓不到"用词错误"**（`form`↔`from`、`complement`↔`compliment`、`discrete`↔`discreet`）——
后者的每个词拼写都对，只有上下文能判。所以"拼写检查通过"**不等于**"用词无误"。
它的价值在于：把一类人工阅读**系统性跳过**的错误（`a effect` 那一类）
从"靠人读"变成"机器确认"，与深挖式/扫读式细读是**正交**的第四个视角。

**实测噪声来源**（别误判为作者笔误）：宏包选项（`fleqn` / `leqno` / `draft`）、
`\begin{tabular}{LLLL}` 这类列格式、算法宏（`algorithm2e` 的 `\SetKw*`）、
LaTeX 标识符，以及**你所在领域的术语与专有名词**。

经验法则：**词典判"未知"≠ 文章写错了**。命中项必须逐条回读上下文。
本技能**刻意不内置任何学科的词表**——你自己的领域词用 `--words my-words.txt` 传入，
或写成论文同目录的 `paper.tex.words` 自动加载。

浏览器打印的 PDF（Producer 是 `Skia/PDF`）**没有文字层**，`pdftotext` 抽不出内容，只能渲染成图片。

---

## 关于「AI 味」

**不要用标点习惯去判断文本是否 AI 生成。** 这不可靠，而且方向常常是反的。

真正有点区分度的是**分布**与**残留错误**，不是某几个标点：

- 人类写的工程论文句长分布**很不均匀**——短句与长句混杂、跨度很大；
  AI 生成文本的句长分布明显更均匀。
- **文中残留的非母语搭配错误是强反证**：AI 不会写出
  `the measurement quality exhibits poor characteristics` 这类生硬搭配，
  也不会成串丢失冠词、或把同一个参数写出三种记号。
- 反过来不成立：em dash、`delve` / `tapestry` / `pivotal` 这类"AI 味关键词"
  在真实论文里也完全可以一个都没有，**不能据此反向推断**。

**唯一值得做的**是铁律 2：不要引入原文里没有的风格特征。
那是"与文档自身基线一致"的问题，不是"躲检测"的问题。

如果作者确实担心，**唯一值得做的**是：不要引入原文里没有的风格特征（例如给一篇 0 个 em dash 的论文加 em dash）。这属于铁律 2，是"与文档自身基线一致"的问题，不是"躲检测"的问题。
