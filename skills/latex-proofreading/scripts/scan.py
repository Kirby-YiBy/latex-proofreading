#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scan.py — 机械扫描：只报「可用规则判定」的问题，不做语言判断。

用法:
    python scan.py <file.tex>
    python scan.py <file.tex> --dashes       只看破折号
    python scan.py <file.tex> --variants     只看术语变体冲突

输出每项都带「行号 + 逐字片段」，方便下游 grep 回查。

设计要点：**不跳过含 LaTeX 命令的行**，而是把命令剥掉后分析剩下的正文。
LaTeX 论文里几乎每行都有 \\citep{} / \\xref{}，按行跳过会漏掉绝大部分内容
（这个 bug 让本脚本第一版漏掉了若干处术语变体）。
"""
import io
import re
import sys
import statistics
from collections import defaultdict

try:  # Windows 控制台默认 GBK，中文会乱码
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

UNCOUNTABLE_PLURALS = (
    'noises', 'evidences', 'informations', 'equipments', 'researches',
    'knowledges', 'softwares', 'feedbacks', 'trainings', 'furnitures',
    'advices', 'progresses', 'accuracies', 'precisions', 'robustnesses',
)

LATEX_COMMENT = re.compile(r'(?<!\\)%.*$')
# 不该参与语言扫描的区域：参考文献 + 各类宏定义块
BIB_REGION = re.compile(
    r'\\begin\{(bibwrite|thebibliography|macros|additionalmacros|pkg|additionalpkgs)\}'
    r'.*?\\end\{\1\}', re.S)
# 定义类命令：剥掉花括号后会产出 "theorem Theorem" 这种假重复词
DEF_CMD = re.compile(
    r'\\\s*(?:new|renew|def|Declare|Set|usepackage|documentclass|RequirePackage|'
    r'newtheorem|newdefinition|newproof)\b')


def read(path):
    raw = open(path, 'rb').read()
    nl = '\r\n' if raw.count(b'\r\n') else '\n'
    return raw.decode('utf-8'), nl


def strip_latex(line):
    """把一行 LaTeX 变成可分析的纯文本。命令替换为空格，保留 {..} 内容。"""
    s = LATEX_COMMENT.sub('', line)
    s = re.sub(r'\$[^$]*\$', ' ', s)          # 行内公式
    s = re.sub(r'\\[A-Za-z]+\*?', ' ', s)     # 命令名
    s = s.replace('\\', ' ')
    for ch in '{}[]~':
        s = s.replace(ch, ' ')
    return re.sub(r'\s+', ' ', s).strip()


def prose_lines(text, nl):
    """返回 [(行号, 原始行, 剥离后的正文)]。

    排除两块非正文区域：
    - 参考文献区（bibwrite / thebibliography）
    - 导言区（\\begin{document} 之前），否则 \\newtheorem{theorem}{Theorem}
      会被剥成 "theorem Theorem" 而误报为重复词
    """
    doc_at = text.find('\\begin{document}')
    body = text[doc_at:] if doc_at >= 0 else text
    offset = text[:doc_at].count(nl) if doc_at >= 0 else 0
    # 用 nl 而不是 '\n' 填充：文件若是 CRLF，填 '\n' 会导致这些行不被切分，
    # 后续所有行号整体前移（第一版就是这样偏移了 12 行）。
    body = BIB_REGION.sub(lambda m: nl * m.group(0).count('\n'), body)
    out = []
    for i, raw in enumerate(body.split(nl), 1):
        if DEF_CMD.search(raw):
            continue
        stripped = strip_latex(raw)
        if stripped:
            out.append((i + offset, raw, stripped))
    return out


def section(title):
    print()
    print('=' * 74)
    print(title)
    print('=' * 74)


def report(hits, empty_msg='（无）', limit=40):
    if not hits:
        print('  ' + empty_msg)
        return
    for n, snippet, extra in hits[:limit]:
        print('  L%-6d %s' % (n, snippet))
        if extra:
            print('         %s' % extra)
    if len(hits) > limit:
        print('  ... 另有 %d 处' % (len(hits) - limit))


def scan_dashes(text):
    return [('em dash  ---', text.count('---')),
            ('en dash  -- ', text.count('--') - 2 * text.count('---'))]


def scan_variants(plines):
    """找「同一术语的两种写法」：如 pre-processing vs preprocessing。

    两个关键点，第一版都写错过：
    1. 必须**全文范围**比对，不能逐行比对 —— 两种写法通常分布在不同行。
    2. 无连字符形式必须是文中真实存在的独立单词，不能由连字符词派生，
       否则每个连字符词都会和自己"冲突"。
    """
    hyphen = defaultdict(set)
    plain = defaultdict(set)
    tok = re.compile(r'\b([A-Za-z]{3,}(?:-[A-Za-z]{3,})+)\b')
    word = re.compile(r'[A-Za-z]{3,}')
    for n, raw, s in plines:
        for m in tok.finditer(s):
            hyphen[m.group(1).lower()].add(n)
        for m in word.finditer(s):
            plain[m.group(0).lower()].add(n)
    pairs = []
    for h in sorted(hyphen):
        p = h.replace('-', '')
        if p in plain:
            pairs.append((h, len(hyphen[h]), sorted(hyphen[h])[:10],
                          p, len(plain[p]), sorted(plain[p])[:10]))
    return pairs


def scan_doubled(plines):
    pat = re.compile(r'\b([A-Za-z]{3,})\s+\1\b', re.I)
    return [(n, repr(m.group(0)), s[:110])
            for n, raw, s in plines for m in pat.finditer(s)]


def scan_double_space(plines):
    return [(n, s[:110], '') for n, raw, s in plines
            if re.search(r'[a-z]  +[A-Za-z]', raw)]


def scan_uncountable(plines):
    pat = re.compile(r'\b(%s)\b' % '|'.join(UNCOUNTABLE_PLURALS), re.I)
    out = []
    for n, raw, s in plines:
        for m in pat.finditer(s):
            out.append((n, m.group(0), '...' + s[max(0, m.start() - 45):m.start() + 45] + '...'))
    return out


def scan_quotes(lines):
    return [(n, '直引号不成对', l.strip()[:100])
            for n, l in enumerate(lines, 1)
            if l.count('"') % 2 == 1]


def sentence_stats(plines):
    sents = []
    for n, raw, s in plines:
        for x in re.split(r'(?<=[.])\s+(?=[A-Z])', s):
            w = len(x.split())
            if w >= 5:
                sents.append(w)
    return sents


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = set(a for a in sys.argv[1:] if a.startswith('--'))
    if len(args) != 1:
        raise SystemExit(__doc__)
    path = args[0]
    text, nl = read(path)
    lines = text.split(nl)
    plines = prose_lines(text, nl)
    only = flags & {'--dashes', '--variants'}

    print('文件  : %s' % path)
    print('行数  : %d   换行: %r   字符: %d' % (len(lines), nl, len(text)))
    print('正文行: %d（已剔除参考文献区）' % len(plines))

    if not only or '--dashes' in flags:
        section('破折号用量')
        for name, c in scan_dashes(text):
            print('  %-16s %d' % (name, c))
        print('  说明：--- 是 em dash（插入语/停顿），-- 是 en dash。')
        print('        复姓连接如 Levenberg--Marquardt 必须用 en dash，不要动。')
        if not only:
            loc = [(i, l.strip()[:100], '') for i, l in enumerate(lines, 1) if '---' in l]
            print('  em dash 出现位置：')
            report(loc, '（全文没有 em dash）')

    if not only or '--variants' in flags:
        section('术语变体冲突（同一词的不同写法并存）')
        pairs = scan_variants(plines)
        if not pairs:
            print('  （未发现同一术语同时存在带连字符与不带连字符两种写法）')
        for h, ch, hl, p, cp, pl in pairs:
            print('  %-24s %2d 次   L%s' % (h, ch, hl))
            print('  %-24s %2d 次   L%s' % (p, cp, pl))
            print('  -> 统一到哪个？判据是「哪个更规范」，不是「哪个多」。')
            print('     作定语时带连字符通常更规范；不要为了凑数量而向下对齐。')
            print()

    if only:
        return 0

    section('重复词（the the / of of 一类）')
    report(scan_doubled(plines), '（无）')

    section('多余空格（原始行，未剥离命令）')
    report(scan_double_space(plines), '（无）')

    section('不可数名词误加复数')
    report(scan_uncountable(plines), '（无）')

    section('直引号不成对')
    report(scan_quotes(lines), '（无）')

    section('句长分布（仅参考，不是判据）')
    s = sentence_stats(plines)
    if s:
        s.sort()
        print('  句数 %d   均值 %.1f   中位数 %d   标准差 %.1f   跨度 %d-%d'
              % (len(s), statistics.mean(s), s[len(s) // 2],
                 statistics.stdev(s), s[0], s[-1]))
    print('  提醒：不要用标点习惯或句长去推断文本是否 AI 生成——那不可靠。')
    print('        非母语写作留下的搭配错误反而是强反证，AI 不会那样写。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
