# 从零到发布：把技能做成别人能装的插件

这份文档记录本仓库是怎么搭起来的，以及**每一步为什么必须有**。
以后再写第二个技能、或要发一个新版本，照这里做即可。

---

## 一、先搞清三个概念

这三个词最容易混。用一句话钉死：

| 概念 | 是什么 | 在本仓库里 |
|---|---|---|
| **Skill（技能）** | 一份**给 Claude 看的说明书**：一个 `SKILL.md`（含 `name` 与 `description` frontmatter）＋它需要的参考文档和脚本。Claude 读到 `description` 后判断「这个任务该不该用它」 | `skills/latex-proofreading/` |
| **Plugin（插件）** | 一个**可安装的分发包**，把技能（以及可选的 commands / agents / hooks）装进一个带清单的盒子 | 本仓库整体（`.claude-plugin/plugin.json`） |
| **Marketplace（市场）** | 一个**目录**，告诉 Claude Code「从哪儿能装到哪些插件」。它就是一个 git 仓库，里面放一个 `marketplace.json` | 本仓库整体（`.claude-plugin/marketplace.json`） |

**关键点**：一个仓库可以**同时**是 marketplace 和 plugin。
本仓库就是——`marketplace.json` 里列的插件 `source: "./"` 指向仓库根，
所以「加市场」和「装插件」都发生在同一个仓库上。

> 为什么不能只丢一个 `SKILL.md` 给人？
> 可以（复制到 `~/.claude/skills/` 就行），但那样**没有版本、没有更新、
> 没有依赖声明**。做成插件后，别人一条命令装上，你改完 `version` 一推，
> 大家 `/plugin marketplace update` 就能拿到新版。

### 为什么 marketplace 里还要再列一次 `skills`

`plugin.json` 是插件的自我介绍；`marketplace.json` 的 `plugins[]` 里那一份
是**面向安装器的**，`skills: [...]` 显式列出技能目录。
两边都写、且 `version` 保持一致，是稳妥做法。

---

## 二、仓库结构：每个文件为什么在这儿

```
latex-proofreading/
├── .claude-plugin/          ← 这个目录名是**规定死的**，只放清单，别放别的
│   ├── plugin.json          ← 插件清单：名字、版本、作者、许可、关键词
│   └── marketplace.json     ← 市场注册表：本仓库提供哪些插件
├── skills/
│   └── latex-proofreading/  ← 技能本体
│       ├── SKILL.md         ← 【最重要】frontmatter 里的 description 决定它何时被触发
│       ├── references/      ← 按需加载的参考文档（Claude 只在需要时读）
│       └── scripts/         ← 可执行脚本
├── docs/
│   └── SANITIZATION.md      ← 发布前的脱敏记录
├── README.md                ← 面向**使用者**：这是什么、怎么装、依赖什么
├── PUBLISHING.md            ← 面向**你**：本文件
├── LICENSE                  ← 没有它，法律上默认「保留所有权利」，别人不敢二次分发
├── CHANGELOG.md             ← 改动记录；发版时更新
└── .gitignore               ← 别把备份、渲染图、稿件、密钥带进仓库
```

### `SKILL.md` 的 frontmatter 是命门

```yaml
---
name: latex-proofreading          # 小写 + 连字符，与目录名一致
description: Use when ...         # 这里写"什么时候该用我"
---
```

`description` **不是简介，是触发器**。Claude 靠它在每次对话里判断要不要加载这个技能。
所以要写「**症状**」而不是「功能」——比如列上用户可能说的原话
（`"校稿"`、`"proofread my .tex"`、`"verify the DOIs"`），而不只是
"一个校稿工具"。

写得太窄 → 该用的时候不触发；写得太宽 → 每次都加载、浪费上下文。

---

## 三、别人怎么装（两条命令）

```
/plugin marketplace add <owner>/<repo>
/plugin install <plugin-name>@<marketplace-name>
```

在本仓库就是：

```
/plugin marketplace add Kirby-YiBy/latex-proofreading
/plugin install latex-proofreading@latex-proofreading
```

`add` 把仓库克隆到 `~/.claude/plugins/marketplaces/<marketplace 名>/`；
`install` 把插件启用到 `~/.claude/plugins/cache/` 并写进 `~/.claude/settings.json`：

```jsonc
{
  "extraKnownMarketplaces": {
    "latex-proofreading": { "source": { "source": "git",
                                        "url": "https://github.com/...git" } }
  },
  "enabledPlugins": { "latex-proofreading@latex-proofreading": true }
}
```

也可以 `/plugin marketplace add` 一个**本地路径** —— 这一点很有用，
**可以推 GitHub 之前就把整个安装链路验一遍**。

> **安装后路径会变**：插件被复制到 `cache/` 下，不是原地运行。
> 所以技能里**绝不能写死** `~/.claude/skills/...` 这种路径——
> 对任何消费者都不成立。要么用相对技能目录的路径（本仓库的做法），
> 要么用插件根目录变量。

---

## 四、从零发布的完整步骤

```bash
# 1. 在本地把仓库搭好（本文件所在目录）
cd /path/to/latex-proofreading

# 2. 本地验证：先确认清单能被解析、技能能被识别
claude plugin marketplace add "$(pwd)"
claude plugin marketplace list
claude plugin details latex-proofreading

# 3. 真装一遍，确认脚本的相对路径在安装后仍能解析
claude plugin install latex-proofreading@latex-proofreading
#   再跑一个脚本试试，例如：
python <安装路径>/scripts/selftest.py <任意 .tex>

# 4. 初始化 git
git init -b main
git add -A
git status                    # ← 提交前**逐行看一遍**，确认没有密钥/稿件/本机路径
git commit -m "feat: latex-proofreading 1.0.0"

# 5. 在 GitHub 网页新建**空**仓库
#    不要勾选 README / .gitignore / LICENSE —— 勾了就会和本地冲突

# 6. 关联并推送
git remote add origin https://github.com/<owner>/latex-proofreading.git
git push -u origin main

# 7. 用远端再验一次消费者路径
claude plugin marketplace add <owner>/latex-proofreading
```

### 为什么第 5 步要建**空**仓库

GitHub 建仓库时勾「Add a README」会替你先提交一个 commit。
你本地也提交过，两边历史无关 → `push` 会被拒（non-fast-forward），
得先 `git pull --allow-unrelated-histories` 去合并，多一堆麻烦。
建空库就完全绕开这件事。

---

## 五、发新版本

1. 改代码/文档
2. **更新两个清单里的 `version`**（`plugin.json` 与 `marketplace.json` 的 `plugins[0].version`），
   保持两者一致
3. 在 `CHANGELOG.md` 记一笔
4. `git commit` → `git push`
5. 使用者侧：`/plugin marketplace update <marketplace 名>` 拉新版

版本号遵循语义化版本：**MAJOR** 破坏兼容（改了触发条件/脚本参数），
**MINOR** 加功能，**PATCH** 修 bug。

---

## 六、这次踩到的坑（下次直接避开）

| 坑 | 现象 | 对策 |
|---|---|---|
| **路径写死在本机** | 技能里让人 `cd ~/.claude/skills/xxx`；别人装上后目录在 `cache/` 下，全断 | 一律相对技能目录 |
| **把真实工作内容带进仓库** | 技能是在真实项目里长出来的，示例、数字、路径都带项目指纹 | 发布前做一次「**如果这段被 Google 搜到会怎样**」的自查；把案例改写成合成案例 |
| **内置了领域词表** | 把技能绑死在某个学科，且词表本身成为可识别的特征 | 默认词表只留跨学科通用词，领域词走 `--words` 外部文件 |
| **占位邮箱发给第三方 API** | `example.org` 是保留域名；CrossRef polite pool 要真实邮箱 | 改成由使用者通过参数/环境变量提供；没提供就照实提示，不伪造 |
| **仓库建在含密钥的目录里** | 某些工具目录（如 `~/.claude/`）里有明文 token，整体入仓即泄露 | 仓库建在独立目录；`.gitignore` 里预先排除 `settings.json` / `.env` / `*.key` |
| **manifest 靠记忆写** | 字段名记错，加载失败 | 找一个**正在被正常加载的**插件，读它的清单当模板 |

最后一条最值得记住：**规范的最佳来源是一个真在跑的实例**，不是回忆。
本仓库的两个清单就是照着一个已上线的插件逐字段对齐的。

---

## 七、要不要做 eval

`claude plugin eval <path>` 可以对插件跑评测用例（`evals/**/case.yaml`）。
本仓库暂未包含——校稿质量的好坏主要由**作者的采纳率**体现，
不容易写成自动判分的用例。若以后要加，合适的用例形态是：

- 给一份**故意埋了已知错误**的合成 `.tex`
- 打分标准：是否找出了那些错误、是否**误报**了干净文本、是否遵守了「不改标签名」

第三个维度尤其重要——技能文档里反复强调的「误报比漏报贵」，
正适合用评测固化下来。
