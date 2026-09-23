#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apply.py — 原子化替换：全通过才写盘，否则原文件一个字节都不动。

用法:
    python apply.py <target.tex> <edits.py> [--dry-run]

edits.py 需定义一个名为 EDITS 的列表，每项为四元组：
    (编号, 旧串, 新串, 期望出现次数)

为什么必须原子化：校稿是在作者的手稿上动刀，一次静默的错配就会污染文件。
本脚本逐条断言「旧串在文件中出现的次数 == 期望次数」，任何一条不符就整体中止。
（实测中，这个机制拦下过两次真实错配——都在写盘前中止，文件完好。）

换行符安全：以二进制读取 + UTF-8 解码，改完原样写回，不触碰 CRLF。
所以 edits.py 里的换行统一写 '\\n' 即可，脚本会自动适配文件实际的换行符。
"""
import io
import os
import sys
import hashlib

try:  # Windows 控制台默认 GBK，中文会乱码
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass


def load_edits(path):
    ns = {}
    src = open(path, encoding='utf-8').read()
    # 只 exec EDITS 字面量，允许文件里还有其他内容
    if 'EDITS' not in src:
        raise SystemExit('edits 文件里找不到 EDITS 定义: %s' % path)
    exec(compile(src, path, 'exec'), ns)
    return ns['EDITS']


def detect_newline(raw):
    if raw.count(b'\r\n'):
        return '\r\n'
    return '\n'


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry = '--dry-run' in sys.argv
    if len(args) != 2:
        raise SystemExit(__doc__)
    target, edits_path = args

    raw = open(target, 'rb').read()
    text = raw.decode('utf-8')
    nl = detect_newline(raw)
    edits = load_edits(edits_path)

    print('目标   : %s' % target)
    print('换行符 : %r  (%d 处)' % (nl, raw.count(nl.encode())))
    print('条目数 : %d' % len(edits))
    print('原文件 sha256: %s' % hashlib.sha256(raw).hexdigest())
    print('-' * 72)

    fails, applied = [], []
    for item in edits:
        if len(item) != 4:
            fails.append('条目格式错误（应为四元组）: %r' % (item,))
            continue
        eid, old, new, want = item
        o = old.replace('\n', nl)
        n = new.replace('\n', nl)
        got = text.count(o)
        if got != want:
            fails.append('%-12s 期望 %d 次，实际 %d 次  |  %s' % (eid, want, got, old[:90]))
            continue
        text = text.replace(o, n)
        applied.append(eid)
        print('  ok  %-12s x%d' % (eid, want))

    if fails:
        print('-' * 72)
        print('中止：%d 条未通过断言，文件未改动。' % len(fails))
        for f in fails:
            print('  !! ' + f)
        return 1

    print('-' * 72)
    if dry:
        print('dry-run：%d 条全部通过，未写盘。' % len(applied))
        return 0

    out = text.encode('utf-8')
    open(target, 'wb').write(out)
    print('已写盘：%d 条。新 sha256: %s' % (len(applied), hashlib.sha256(out).hexdigest()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
