#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest.py — 技能自检：确认全部脚本能跑、apply.py 的原子性成立。

用法:
    python selftest.py <任意一份 .tex 文件>

换到新环境后先跑一遍。它验证的是「脚本本身可用」，不是「你的论文没问题」。
"""
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tempfile

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = ['scan.py', 'xref.py', 'compliance.py', 'consistency.py',
           'refs.py', 'render.py', 'apply.py']
RUN_WITH_FILE = {'scan.py', 'xref.py', 'compliance.py'}


def run(args, **kw):
    return subprocess.run([sys.executable] + args, capture_output=True,
                          text=True, encoding='utf-8', errors='replace', **kw)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    sample = sys.argv[1]
    if not os.path.exists(sample):
        raise SystemExit('找不到样例文件: %s' % sample)

    fails = []

    print('=' * 74)
    print('1) 每个脚本都要能在无参数时打印用法（说明模块无导入期错误）')
    print('=' * 74)
    for s in SCRIPTS:
        p = os.path.join(HERE, s)
        r = run([p])
        ok = bool((r.stdout or '') + (r.stderr or '')) and 'Traceback' not in (r.stderr or '')
        print('  %-16s %s' % (s, 'ok' if ok else 'FAIL'))
        if not ok:
            fails.append('%s 无参数时崩溃: %s' % (s, (r.stderr or '')[:200]))

    print()
    print('=' * 74)
    print('2) 逐个跑真实文件，不得抛异常')
    print('=' * 74)
    for s in sorted(RUN_WITH_FILE):
        p = os.path.join(HERE, s)
        r = run([p, sample])
        ok = r.returncode in (0, 2) and 'Traceback' not in (r.stderr or '')
        print('  %-16s exit=%-3s %s' % (s, r.returncode, 'ok' if ok else 'FAIL'))
        if not ok:
            fails.append('%s 运行失败: %s' % (s, (r.stderr or '')[:200]))

    print()
    print('=' * 74)
    print('3) apply.py 原子性：一条断言失败 => 整体中止、文件零字节变化')
    print('=' * 74)
    tmp = tempfile.mkdtemp()
    target = os.path.join(tmp, 'probe.tex')
    shutil.copy(sample, target)
    editfile = os.path.join(tmp, 'edits.py')
    with open(editfile, 'w', encoding='utf-8') as f:
        f.write(
            'BS = chr(92)\n'
            'EDITS = [\n'
            '  ("good", "the", "THE", 99999),\n'      # 故意写一个不可能的期望次数
            ']\n')
    h1 = hashlib.sha256(open(target, 'rb').read()).hexdigest()
    r = run([os.path.join(HERE, 'apply.py'), target, editfile])
    h2 = hashlib.sha256(open(target, 'rb').read()).hexdigest()
    ok = (r.returncode == 1) and (h1 == h2)
    print('  exit=%-3s sha256 不变=%-5s %s' % (r.returncode, h1 == h2, 'ok' if ok else 'FAIL'))
    if not ok:
        fails.append('apply.py 原子性被破坏')
    shutil.rmtree(tmp, ignore_errors=True)

    print()
    print('=' * 74)
    if fails:
        print('结果：%d 项失败' % len(fails))
        for f in fails:
            print('  !! ' + f)
        return 1
    print('结果：全部通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
