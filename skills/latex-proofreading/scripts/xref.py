#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xref.py — 交叉引用完整性：悬空引用、重复标签、定义了但从未引用的标签。

用法:
    python xref.py <file.tex>
    python xref.py <file.tex> --macros xref,tabref,eqref   # 自定义要检查的引用宏

能查的是「引用能不能解析」；**不能**判断「这个引用指得对不对」——
后者需要人读，或渲染 PDF 看实际编号。
"""
import io
import re
import sys
from collections import defaultdict

try:  # Windows 控制台默认 GBK，中文会乱码
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

BS = chr(92)
DEFAULT_MACROS = ('xref', 'tabref', 'eqref', 'stmxref', 'ref')


def read(path):
    raw = open(path, 'rb').read()
    nl = '\r\n' if raw.count(b'\r\n') else '\n'
    return raw.decode('utf-8'), nl


def collect_labels(lines):
    """标签来源：\\xlabel{}（本模板）与 \\label{}（标准 LaTeX）。"""
    labels = defaultdict(list)
    for i, l in enumerate(lines, 1):
        for mac in ('xlabel', 'label'):
            for m in re.finditer(re.escape(BS + mac) + r'\{([^}]+)\}', l):
                # 一个 \label 可能带逗号分隔的多个键
                for key in re.split(r'[,\s]+', m.group(1)):
                    key = key.strip()
                    if key:
                        labels[key].append(i)
    return labels


def collect_refs(lines, macros):
    refs = []
    for i, l in enumerate(lines, 1):
        for mac in macros:
            for m in re.finditer(re.escape(BS + mac) + r'\{([^}]+)\}', l):
                for key in m.group(1).split(','):
                    key = key.strip()
                    if key:
                        refs.append((i, mac, key))
    return refs


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 1:
        raise SystemExit(__doc__)
    macros = DEFAULT_MACROS
    for a in sys.argv[1:]:
        if a.startswith('--macros'):
            macros = tuple(x.strip() for x in a.split('=', 1)[1].split(','))

    path = args[0]
    text, nl = read(path)
    lines = text.split(nl)
    labels = collect_labels(lines)
    refs = collect_refs(lines, macros)

    print('文件: %s' % path)
    print('标签: %d 个    引用: %d 处    检查的宏: %s'
          % (len(labels), len(refs), ', '.join(BS + m for m in macros)))

    dangling = [(n, mac, k) for n, mac, k in refs if k not in labels]
    print()
    print('=' * 74)
    print('悬空引用（引用了不存在的标签）—— 这类必须修')
    print('=' * 74)
    if not dangling:
        print('  （无）')
    for n, mac, k in dangling:
        print('  L%-6d %s{%s}' % (n, mac, k))

    dupes = {k: v for k, v in labels.items() if len(v) > 1}
    print()
    print('=' * 74)
    print('重复标签（同一标签定义多次）')
    print('=' * 74)
    if not dupes:
        print('  （无）')
    for k, v in sorted(dupes.items()):
        print('  %-40s L%s' % (k, v))

    used = set(k for _, _, k in refs)
    never = sorted(set(labels) - used)
    print()
    print('=' * 74)
    print('定义了但未被引用的标签')
    print('=' * 74)
    print('  说明：多数是公式标签（由 \\eqref 引用，若 --macros 未含 eqref 会误列），')
    print('        或本模板用 \\stmxref 特殊引用的算法标签。先确认再判为问题。')
    if not never:
        print('  （无）')
    for k in never:
        print('  %-40s L%s' % (k, labels[k]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
