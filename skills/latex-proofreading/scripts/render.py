#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render.py — 把 PDF 页渲染成图片，用于「渲染级验证」。

用法:
    python render.py proof.pdf --page 4                 渲染第 4 页
    python render.py proof.pdf --page 4 --dpi 300       提高分辨率
    python render.py proof.pdf --page 4 --crop 250,2400,1600,300
                                                        裁切一小块并放大（看单个表格单元格）

为什么要这个工具：**源码里看到的和排版后看到的可能不是一回事。**
实证：`\\eqref{...}` 在源码里看着只输出编号，排版后却是 "Eq. (N)"。
凡是涉及「引用措辞、宏展开、表格单元格占位符」的判断，都应该渲染出来看一眼。

依赖 pdftoppm（TeXLive / poppler 自带）。无外部 Python 包依赖——
本例环境里 pypdf / PyPDF2 / fitz 都不可用，只能走这条路。
"""
import io
import os
import shutil
import subprocess
import sys

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass


VALUE_FLAGS = ('--page', '--dpi', '--crop', '--out')


def parse_argv(argv):
    """同时支持 --page=4 与 --page 4 两种写法。"""
    vals, positional = {}, []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in VALUE_FLAGS:
            vals[a[2:]] = argv[i + 1] if i + 1 < len(argv) else ''
            i += 2
        elif a.startswith('--') and '=' in a:
            k, v = a[2:].split('=', 1)
            vals[k] = v
            i += 1
        else:
            positional.append(a)
            i += 1
    return vals, positional


def main():
    vals, positional = parse_argv(sys.argv[1:])
    if len(positional) != 1:
        raise SystemExit(__doc__)
    pdf = positional[0]
    if not os.path.exists(pdf):
        raise SystemExit('找不到文件: %s' % pdf)

    tool = shutil.which('pdftoppm')
    if not tool:
        raise SystemExit(
            '找不到 pdftoppm。\n'
            '  TeXLive 自带：<texlive>/bin/windows/pdftoppm.exe\n'
            '  或安装 poppler-utils 后重试。')

    page = vals.get('page') or '1'
    dpi = vals.get('dpi') or '150'
    crop = vals.get('crop')
    out = vals.get('out') or ('page_%s.png' % page)

    cmd = [tool, '-f', page, '-l', page, '-r', dpi, '-png']
    if crop:
        try:
            x, y, w, h = [int(v) for v in crop.split(',')]
        except ValueError:
            raise SystemExit('--crop 需要四个整数: x,y,w,h')
        cmd += ['-x', str(x), '-y', str(y), '-W', str(w), '-H', str(h)]
    # pdftoppm 会在输出名后自动加 "-<页码>"
    base = out[:-4] if out.lower().endswith('.png') else out
    cmd += [pdf, base]

    print('执行: %s' % ' '.join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr, file=sys.stderr)
        raise SystemExit('渲染失败，返回码 %d' % r.returncode)

    produced = [f for f in os.listdir(os.path.dirname(os.path.abspath(base)) or '.')
                if f.startswith(os.path.basename(base)) and f.endswith('.png')]
    print()
    print('已生成:')
    for f in sorted(produced):
        p = os.path.join(os.path.dirname(os.path.abspath(base)), f)
        print('  %s  (%d 字节)' % (p, os.path.getsize(p)))
    print()
    print('提示：用 Read 工具打开图片查看。若要放大某个单元格，')
    print('      先用低 dpi 渲染整页定位坐标，再用 --crop 高位放大。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
