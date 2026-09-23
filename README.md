# latex-proofreading

给 **LaTeX 论文**做校稿的 Claude Code 技能：语言与文本层面的校对，
产出一份**你可以逐条把关**的问题清单，并在你圈选后**安全地**应用修改。

**不是**审稿 —— 它不评价方法学、创新性、实验设计或数学推导是否正确。
它只回答一个问题：**这篇稿子在文字、数字、引用、格式上，还有哪些明确的问题？**

> English: A Claude Code skill for proofreading LaTeX manuscripts at
> submission/proof stage — language defects, terminology and numeric consistency,
> cross-reference integrity, citation/DOI errors, and journal format compliance.
> Ships a methodology (8 rules + a 6-phase workflow), 9 standalone checker
> scripts, and a synthetic worked example.

---

## 安装

```
/plugin marketplace add Kirby-YiBy/latex-proofreading
/plugin install latex-proofreading@latex-proofreading
```

装完后，在对话里说「帮我校稿这份 paper.tex」「检查一下论文的引用和数字」之类即可触发。

不想用插件系统？也可以直接把 `skills/latex-proofreading/` 整个目录复制到
`~/.claude/skills/`（个人级）或你的项目里的 `.claude/skills/`（项目级）。

## 依赖

**核心功能零依赖** —— 9 个脚本里 7 个只用 Python 标准库。

| 可选依赖 | 用在 | 装法 |
|---|---|---|
| `pyspellchecker` | `spell.py` 词级拼写检查 | `pip install pyspellchecker` |
| `pdftoppm`（poppler 或 TeXLive 自带） | `render.py` 把 PDF 渲成图片 | 系统包管理器 |
| 可访问 `api.crossref.org` | `refs.py` 核对 DOI 与作者名 | 无需密钥 |

没有这些依赖时，其余脚本照常工作。

## 里面有什么

```
skills/latex-proofreading/
├── SKILL.md              技能本体：8 条铁律 + P0–P6 六阶段工作流 + 报告格式
├── references/
│   ├── checks.md         九大类检查清单（A–I），每项都写清「怎么验」
│   │                     H = 作者与单位（最易整个漏掉的一类）
│   ├── pitfalls.md       已知的坑：宏渲染、CrossRef 数据偏差、环境陷阱，
│   │                     同篇多表的数值对账，以及已交付建议的撤回纪律
│   └── case-study.md     合成案例：每条铁律的实证来源
└── scripts/              9 个可独立运行的脚本，全部无参数运行即打印用法
```

### 脚本

| 脚本 | 作用 |
|---|---|
| `scan.py` | 破折号 / 术语变体 / 重复词 / 多余空格 / 不可数名词误复数 / 直引号 |
| `xref.py` | 悬空引用 / 重复标签 / 定义未引用的标签 |
| `compliance.py` | highlight 字符数 / 摘要词数 / 关键词数（Elsevier 默认阈值，可覆盖） |
| `consistency.py` | 数值定位（`--find`）/ 表格导出（`--tables`）/ 百分比复算（`--improve`） |
| `spell.py` | 词级拼写检查，正文与参考文献分区（需 `pyspellchecker`） |
| `refs.py` | DOI 是否指向正确文献、作者名是否与 CrossRef 一致（需联网） |
| `render.py` | PDF 渲染成图片，做「渲染级验证」（需 `pdftoppm`） |
| `apply.py` | **原子化替换**：断言全部通过才写盘，否则文件零字节变化 |
| `selftest.py` | 自检脚本可用性 + 验证 `apply.py` 的原子性 |

所有脚本的路径都**相对于技能目录**，先 `cd` 过去或写绝对路径。
安装后的位置形如
`~/.claude/plugins/cache/<marketplace 名>/<插件名>/<版本>/skills/latex-proofreading/`：

```bash
cd ~/.claude/plugins/cache/latex-proofreading/latex-proofreading/*/skills/latex-proofreading
python scripts/scan.py             # 无参数即打印用法
python scripts/refs.py paper.tex --all --mailto you@example.com
```

（直接用 `~/.claude/skills/latex-proofreading/` 那种手动复制安装的话，就在那里跑。）

## 两条最容易被绕过、但最要紧的原则

**1. 不许假设 LaTeX 宏渲染成什么。**
`\eqref{...}` 在有些模板里自带 `Eq.` 前缀和括号。凭源码猜、然后"顺手补个 equation"，
会排成 `Equation Eq. (15)`。**先渲染或去类文件里查，再改。**

**2. 改动要与文档自身的基线一致 —— 先数，再改。**
一篇全文 em dash 计数为 0 的论文，你加三个 `---`，单看每个都"语法正确"，
相对它自己的行文基线却突兀。**统计量是判据，直觉不是。**

还有六条，都在 `SKILL.md` 里。

## 关于 `case-study.md`

案例是**合成的**——把多次真实校稿中反复出现的失效模式，组装成一个连贯的教学场景。
稿件、期刊、数值均为示意，**不对应任何一篇真实投稿**。
它的价值在方法论：RED（无技能）与 GREEN（有技能）的对照、
为什么必须同时派"深挖式"与"扫读式"两路、以及为什么**误报比漏报贵**。

## 许可

[MIT](LICENSE)。脚本无第三方代码，仅 `spell.py` 可选依赖 `pyspellchecker`（MIT）。

使用 `refs.py` 即表示你同意
[CrossRef REST API 的条款](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)——
请用 `--mailto` 提供真实邮箱，并遵守其速率限制（脚本已内置请求间隔）。
