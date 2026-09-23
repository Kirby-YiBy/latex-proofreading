# Changelog

本文件记录每个版本的改动。格式参考 [Keep a Changelog](https://keepachangelog.com/)，
版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

## [1.1.0] - 2026-09-23

补上两类**此前完全没写进技能**的检查项——它们都来自实战中被作者明确肯定过的发现，
但只落在了当次报告里，没有沉淀成规则。

### 新增

- **`checks.md` H 节：作者信息与单位**
  - 机构英文名是否完整（有上级单位的一般要带）、机构名内的标点、邮编与现址、
    `\author[N]` ↔ `\affiliation[N]` 对应、通讯作者标记、ORCID、贡献声明姓名集合
  - 点明最典型的漏写形态：**"几处 affiliation 里两处带上级、一处不带"**
  - 三条纪律：机构名是专有名词不可凭语感改、`cp={}` 之类空字段不报、值得联网核
- **`checks.md` I 节：「改了一半」的系统性检法**
  - 给出可直接跑的正则（一句内两次 `is/are + 过去分词`）与变体
  - 强调**命中≠错误**：并列句完全合法，实测该模式全文仅 1 处真阳性
- **`pitfalls.md`：作者会从旧副本编辑，把已改好的地方改回去**
  - 记录实测中同一批 5 处修复被回退两次的现象、症状与对策
  - 关键提醒：重复回退通常是**流程问题**，且不要因为"以前改过"就盲目改回
- **`SKILL.md`**：P1 阶段新增这两项检查的指引；配套文件说明更新为 A–I 九大类

### 说明

- H 节的示例与 `pitfalls.md` 的案例均使用**合成实例**，不含任何真实机构名或稿件信息

## [1.0.0] - 2026-09-23

首次公开发布。

### 包含

- **技能本体** `SKILL.md`：8 条铁律 + P0–P6 六阶段工作流 + A–F 报告分节规范
- **参考文档**
  - `references/checks.md` — 七大类检查清单，每项含「怎么验」
  - `references/pitfalls.md` — 宏渲染、CrossRef 数据偏差、Windows 环境陷阱
  - `references/case-study.md` — **合成案例**（RED/GREEN 对照、有效手段实测）
- **9 个校验脚本**（7 个仅依赖 Python 标准库）
  `scan.py` / `xref.py` / `compliance.py` / `consistency.py` / `spell.py` /
  `refs.py` / `render.py` / `apply.py` / `selftest.py`

### 公开发布前做的改动

- 案例文件由真实稿件改写为**合成案例**，剥离全部稿件识别信息
  （详见 [docs/SANITIZATION.md](docs/SANITIZATION.md)）
- `spell.py` 的默认词表**移除全部学科专属词汇**，改为通过 `--words` 外部加载
- `refs.py` 新增 `--mailto` / `CROSSREF_MAILTO`，以符合 CrossRef polite pool 的
  「真实可联系邮箱」要求（原先写死的占位邮箱既不合规也不该由本技能代替用户声明）
- 脚本与文档里的示例路径改为相对于技能目录
