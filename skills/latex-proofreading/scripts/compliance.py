#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""compliance.py — 期刊格式合规检查（Elsevier 默认值，可用参数覆盖）。

用法:
    python compliance.py <file.tex>
    python compliance.py <file.tex> --highlights-max 85 --abstract-max 250 --keywords-max 6

为什么单列一个脚本：**语言修正会撞上格式约束**。
实测里，补两个冠词把一条 highlight 从 83 字符推到 88，越过了 Elsevier 的
85 字符上限——语言改对了，格式却坏了。任何涉及 highlight / 标题 / 摘要的修改，
改完都要立刻量长度。
"""
import io
import re
import sys

try:  # Windows 控制台默认 GBK，中文会乱码
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

BS = chr(92)

DEFAULTS = {
    'highlights-min': 3,
    'highlights-max': 5,
    'char-per-highlight': 85,   # Elsevier: "maximum 85 characters, including spaces, per bullet point"
    'abstract-max': 250,
    'keywords-max': 6,
}


def read(path):
    raw = open(path, 'rb').read()
    nl = '\r\n' if raw.count(b'\r\n') else '\n'
    return raw.decode('utf-8'), nl


def strip_tex(s):
    """把 LaTeX 片段变成渲染后会看到的纯文本，用于数长度。"""
    s = re.sub(r'(?<!\\)%.*$', '', s)
    s = re.sub(re.escape(BS + BS) + r'([A-Za-z]+)', r'\1', s)
    s = re.sub(re.escape(BS) + r'([A-Za-z]+)', ' ', s)
    s = s.replace(BS, ' ')
    for ch in '{}~':
        s = s.replace(ch, ' ')
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def find_braced(text, macro, start=0):
    """抓 \\macro{...} 的配对花括号内容。"""
    m = re.compile(re.escape(BS + macro) + r'\s*(?:\[[^\]]*\])?\s*\{').search(text, start)
    if not m:
        return None, -1
    j, depth, out = m.end(), 1, []
    while j < len(text) and depth > 0:
        c = text[j]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                break
        out.append(c)
        j += 1
    return ''.join(out), m.start()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    cfg = dict(DEFAULTS)
    for a in sys.argv[1:]:
        if a.startswith('--') and '=' in a:
            k, v = a[2:].split('=', 1)
            if k in cfg:
                cfg[k] = int(v)
    if len(args) != 1:
        raise SystemExit(__doc__)
    path = args[0]
    text, nl = read(path)
    lines = text.split(nl)
    ok = True

    print('文件: %s' % path)
    print('阈值: highlight %d-%d 条、每条 <= %d 字符; 摘要 <= %d 词; 关键词 <= %d 个'
          % (cfg['highlights-min'], cfg['highlights-max'],
             cfg['char-per-highlight'], cfg['abstract-max'], cfg['keywords-max']))

    # ---------- 标题 ----------
    title, _ = find_braced(text, 'title')
    print()
    print('=' * 74)
    print('标题')
    print('=' * 74)
    if title is None:
        print('  （未找到 \\title{}，跳过）')
    else:
        t = strip_tex(title)
        print('  %d 字符' % len(t))
        print('  %s' % t)

    # ---------- 摘要 ----------
    print()
    print('=' * 74)
    print('摘要')
    print('=' * 74)
    abs_blocks = re.findall(
        re.escape(BS) + r'begin\{abstract\}(?:\[[^\]]*\])?(.*?)' +
        re.escape(BS) + r'end\{abstract\}', text, re.S)
    if not abs_blocks:
        print('  （未找到 abstract 环境，跳过）')
    for bi, blk in enumerate(abs_blocks, 1):
        plain = strip_tex(re.sub(r'\\item', ' ', blk))
        words = len(plain.split())
        flag = ''
        if words > cfg['abstract-max']:
            flag = '  <== 超出上限'
            ok = False
        print('  块 %d: %d 词 / %d 字符%s' % (bi, words, len(plain), flag))

    # ---------- Highlights ----------
    print()
    print('=' * 74)
    print('Highlights（Elsevier 每条 <= %d 字符，含空格）' % cfg['char-per-highlight'])
    print('=' * 74)
    items = []
    for bi, blk in enumerate(abs_blocks, 1):
        if re.escape(BS) + 'item' in blk or '\\item' in blk:
            for m in re.finditer(re.escape(BS) + r'item\s*(.*?)(?=' +
                                 re.escape(BS) + r'item|' + re.escape(BS) + r'end\{itemize\}|\Z)',
                                 blk, re.S):
                items.append((bi, strip_tex(m.group(1))))
    if not items:
        print('  （未发现 \\item 形式的 highlights，可能本刊不要求，跳过）')
    for bi, t in items:
        mark = 'OK ' if len(t) <= cfg['char-per-highlight'] else '!!!'
        if len(t) > cfg['char-per-highlight']:
            ok = False
        print('  [%s] %3d 字符  %s' % (mark, len(t), t))
    if items:
        n = len(items)
        print('  共 %d 条（要求 %d-%d 条）%s'
              % (n, cfg['highlights-min'], cfg['highlights-max'],
                 '' if cfg['highlights-min'] <= n <= cfg['highlights-max'] else '  <== 数量不合规'))
        if not (cfg['highlights-min'] <= n <= cfg['highlights-max']):
            ok = False

    # ---------- 关键词 ----------
    print()
    print('=' * 74)
    print('关键词')
    print('=' * 74)
    kw, _ = find_braced(text, 'keywords')
    if kw is None:
        print('  （未找到 \\keywords{}，跳过）')
    else:
        parts = [p.strip() for p in re.split(re.escape(BS + 'sep') + r'|;|,', kw) if p.strip()]
        print('  %d 个%s' % (len(parts), '' if len(parts) <= cfg['keywords-max'] else '  <== 超出上限'))
        for p in parts:
            print('    - %s' % strip_tex(p))
        if len(parts) > cfg['keywords-max']:
            ok = False

    print()
    print('=' * 74)
    print('结论：%s' % ('全部合规' if ok else '有项目不合规，见上面标 <== 的行'))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
