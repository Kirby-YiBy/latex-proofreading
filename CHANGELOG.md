# Changelog

本文件记录每个版本的改动。格式参考 [Keep a Changelog](https://keepachangelog.com/)，
版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

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
