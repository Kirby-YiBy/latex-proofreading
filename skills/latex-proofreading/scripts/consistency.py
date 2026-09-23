#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""consistency.py — 数字一致性辅助。

用途：同一个量往往在**摘要、正文叙述、表格**三处各出现一次，
     校稿时要确认三处对得上。这个脚本把三处摆到一起，并帮你复算百分比。

用法:
    # 1) 找某个数值在全篇出现的位置（把三处摆到一起看）
    python consistency.py paper.tex --find 12.34
    python consistency.py paper.tex --find 56.78

    # 2) 把表格导成「行标签 -> 数值」，方便逐表比对
    python consistency.py paper.tex --tables

    # 3) 复算改进率：(基线 - 新值) / 基线
    python consistency.py --improve 20.0 12.5
    python consistency.py --improve 4.0 1.5

    # 4) 批量复算：每行 "标签 基线 新值"
    python consistency.py --improve-file ratios.txt

注意：脚本**不做判断**，只把数字摆出来并算算术。
      「表格里的数是否支持正文的结论」需要人读——例如正文说某方法整体最优，
      但表里另一个方法在某一列更接近参考值，这种要人来发现。
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
# 注意：拼接正则时反斜杠要 re.escape，否则 \end 会被当成非法转义 \e
BEGIN = re.escape(BS + 'begin')
END = re.escape(BS + 'end')
BIB = re.compile(BEGIN + r'\{(bibwrite|thebibliography)\}.*?' + END + r'\{\1\}', re.S)
TABULAR = re.compile(BEGIN + r'\{tabular\}(.*?)' + END + r'\{tabular\}', re.S)


def read(path):
    raw = open(path, 'rb').read()
    nl = '\r\n' if raw.count(b'\r\n') else '\n'
    return raw.decode('utf-8'), nl


def find_number(text, nl, needle):
    print('查找: %s' % needle)
    print('=' * 74)
    hit = 0
    for i, l in enumerate(text.split(nl), 1):
        if needle in l:
            hit += 1
            for m in re.finditer(re.escape(needle), l):
                ctx = l[max(0, m.start() - 70):m.start() + 70].strip()
                print('  L%-6d ...%s...' % (i, ctx))
    if not hit:
        print('  （未找到。注意表格里的数值可能带单位或 LaTeX 命令，试试更短的片段）')
    print('  共 %d 行' % hit)
    print()
    print('  核对要点：摘要说的数、正文叙述的数、表格里的数，三处是否一致？')
    print('            若三处不一致，通常是四舍五入或不同批次实验造成的，需作者确认。')


def dump_tables(text):
    print('表格内容')
    print('=' * 74)
    tabs = TABULAR.findall(text)
    if not tabs:
        print('  （未找到 tabular 环境）')
    for ti, body in enumerate(tabs, 1):
        print()
        print('--- 表 %d ---' % ti)
        for raw in body.split(BS + BS):
            cells = [c.strip() for c in raw.split('&')]
            cells = [re.sub(r'\s+', ' ', c) for c in cells if c.strip()]
            if cells:
                print('  | ' + ' | '.join(cells))
    print()
    print('  提示：本模板用 \\botline 收尾，最后一行不写 \\\\\\\\ 属正常，不是缺漏。')


def improve(a, b, label=None):
    try:
        a, b = float(a), float(b)
    except ValueError:
        print('  无法解析: %s / %s' % (a, b))
        return
    if a == 0:
        print('  基线为 0，无法计算')
        return
    label = label or ('%.4g -> %.4g' % (a, b))
    print('  %-30s (%.4g - %.4g) / %.4g = %6.2f%%'
          % (label, a, b, a, (a - b) / a * 100.0))


def main():
    argv = sys.argv[1:]
    if not argv:
        raise SystemExit(__doc__)

    if argv[0] == '--improve' and len(argv) >= 3:
        improve(argv[1], argv[2])
        return 0

    if argv[0] == '--improve-file' and len(argv) >= 2:
        print('批量复算 (基线, 新值) -> 改进率')
        print('=' * 74)
        for line in open(argv[1], encoding='utf-8'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) >= 3:
                improve(parts[-2], parts[-1], ' '.join(parts[:-2]))
            elif len(parts) == 2:
                improve(parts[0], parts[1])
        return 0

    path = next((a for a in argv if not a.startswith('--')), None)
    if not path:
        raise SystemExit(__doc__)
    text, nl = read(path)
    text = BIB.sub('', text)

    if '--find' in argv:
        i = argv.index('--find')
        find_number(text, nl, argv[i + 1])
    elif '--tables' in argv:
        dump_tables(text)
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == '__main__':
    sys.exit(main())
