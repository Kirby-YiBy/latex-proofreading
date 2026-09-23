#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""spell.py — LaTeX 手稿的词级拼写检查（基于 pyspellchecker，不需要系统词典）。

用法:
    python spell.py paper.tex
    python spell.py paper.tex --words extra.txt     # 追加自定义词表（每行一个词）
    python spell.py paper.tex --bib '\\begin{bibwrite}'   # 指定参考文献区起点

若同目录存在 `paper.tex.words`，会自动作为词表加载。

能抓什么、不能抓什么 —— 一定要说清楚：
    能抓  "非词"错误：recieve / teh / 字母转置 / 多写少写字母
    抓不到 "用词错误"：form↔from、complement↔compliment、discrete↔discreet
            这些词每个拼写都对，只有上下文能判。

所以本脚本是**人工细读的补充，不是替代**。它的价值在于把一类人工阅读会
系统性跳过的错误（"太简单了不值得注意"）变成机器确认。
命中结果**必须逐条回读上下文**再判定 —— 词典的"未知"经常是正确写法
（宏包选项、`tabular` 列格式、出版社标识符、以及你所在领域的术语与专有名词）。
"""
import io
import os
import re
import sys
import collections

try:  # Windows 控制台默认 GBK，中文会乱码
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

try:
    from spellchecker import SpellChecker
except ImportError:
    raise SystemExit(
        '缺少 pyspellchecker。装法: python -m pip install pyspellchecker\n'
        '（纯 Python 包，自带英文词典，不需要系统级 aspell/hunspell）')

# 默认词表：**只放跨学科通用词**。
# 本技能刻意不内置任何学科的词汇——领域词（方法名、缩写、仪器名、自造词）
# 既会让词表变成可指纹化的特征，也会让其它领域的使用者读到别人的词。
# 你自己的领域词请用外部词表传入：
#     python spell.py paper.tex --words my-words.txt
# 或放在论文同目录的 paper.tex.words 里自动加载（每行一个词，# 后可写注释）。
DEFAULT_WORDS = """
rmse mae snr
mahalanobis levenberg marquardt gauss markov kalman
convolutional dataset datasets downweighting downweights hyperparameters
linearities misalignments thresholding unmodeled unphysical unregularized
multipath timestamps workflow overfitting
""".split()

# 剥命令的顺序有讲究：先把「键名类」命令连内容一起吃掉，再吃「格式类」命令的名字
RE_CMD_WITH_KEY = re.compile(
    r'\\(?:cite[pt]?|xref|tabref|eqref|stmxref|ref|label|xlabel)'
    r'(?:\[[^\]]*\])?(?:\{[^{}]*\}){1,2}', re.S)
RE_MATH_BLOCK = re.compile(r'\\\[.*?\\\]', re.S)
RE_MATH_ENV = re.compile(
    r'\\begin\{(?:equation|align|aligned|eqnarray|gather|split|array|tabular|tabularx)\*?\}'
    r'.*?\\end\{(?:equation|align|aligned|eqnarray|gather|split|array|tabular|tabularx)\*?\}',
    re.S)
RE_MATH_INLINE = re.compile(r'\$[^$]*\$', re.S)
RE_BEGIN_END = re.compile(r'\\(?:begin|end)\{[^{}]*\}')
RE_TEX_CMD = re.compile(r'\\[a-zA-Z@]+\*?')
RE_ESCAPE = re.compile(r'\\[^a-zA-Z]')
RE_WORD = re.compile(r"[A-Za-z][A-Za-z']+")


def strip_tex(line):
    """剥掉 LaTeX，保留 \\textbf{词} 这类命令的花括号内容。"""
    s = line
    s = RE_CMD_WITH_KEY.sub(' ', s)
    s = RE_MATH_BLOCK.sub(' ', s)
    s = RE_MATH_ENV.sub(' ', s)
    s = RE_MATH_INLINE.sub(' ', s)
    s = RE_BEGIN_END.sub(' ', s)
    s = RE_TEX_CMD.sub(' ', s)
    s = RE_ESCAPE.sub(' ', s)
    return s.replace('{', ' ').replace('}', ' ').replace('~', ' ')


def load_words(path):
    if not path or not os.path.exists(path):
        return []
    out = []
    for ln in open(path, 'rb').read().decode('utf-8', 'replace').splitlines():
        ln = ln.split('#')[0].strip()
        if ln:
            out.append(ln.lower())
    return out


def parse_args(argv):
    """返回 (paper, words_path, bib_marker)。带值的选项先把值吃掉，剩下的才是位置参数。"""
    opts, positional, i = {}, [], 0
    while i < len(argv):
        a = argv[i]
        if a in ('--words', '--bib'):
            if i + 1 >= len(argv):
                raise SystemExit('选项 %s 缺少取值\n\n%s' % (a, __doc__))
            opts[a] = argv[i + 1]
            i += 2
            continue
        if a.startswith('--'):
            raise SystemExit('未知选项 %s\n\n%s' % (a, __doc__))
        positional.append(a)
        i += 1
    if len(positional) != 1:
        raise SystemExit(__doc__)
    return positional[0], opts.get('--words'), opts.get('--bib', '\\begin{bibwrite}')


def main():
    path, words_path, bib_marker = parse_args(sys.argv[1:])

    raw = open(path, 'rb').read()          # 二进制读，别让 Python 动 CRLF
    text = raw.decode('utf-8')
    nl = '\r\n' if raw.count(b'\r\n') else '\n'
    lines = text.split(nl)

    spell = SpellChecker(language='en', distance=1)
    words = list(DEFAULT_WORDS)
    words += load_words(path + '.words')                 # 同目录同名词表
    words += load_words(words_path)
    spell.word_frequency.load_words(words)

    bib_at = next((i for i, ln in enumerate(lines) if bib_marker in ln), None)

    body, refs = collections.defaultdict(list), collections.defaultdict(list)
    for i, ln in enumerate(lines, start=1):
        if ln.lstrip().startswith('%'):      # 注释行（含出版社标记）不查
            continue
        bucket = refs if (bib_at is not None and i - 1 >= bib_at) else body
        for w in RE_WORD.findall(strip_tex(ln)):
            bucket[w.lower()].append(i)

    print('文件   : %s' % path)
    print('行数   : %d   换行: %r' % (len(lines), nl))
    print('词表   : %d 个自定义词' % len(words))
    print()

    for title, hits in (('正文', body), ('参考文献区', refs)):
        unknown = sorted(spell.unknown(list(hits)))
        print('=' * 72)
        print('%s —— 未知词 %d / 不同词 %d' % (title, len(unknown), len(hits)))
        print('=' * 72)
        if not unknown:
            print('  （无）')
        for w in unknown:
            where = hits[w]
            print('  %-22s x%-3d L%s' % (w, len(where), ','.join(map(str, where[:6]))))
            cand = sorted(spell.candidates(w) or [])[:4]
            if cand:
                print('  %-22s 候选: %s' % ('', ', '.join(cand)))
        print()

    print('提醒：未知 ≠ 错误。宏包选项、tabular 列格式、出版社标识符里的哈希串、')
    print('      缩写、专有名词、以及你所在领域的术语都会命中。')
    print('      **每一条都要回读上下文再判定。**')


if __name__ == '__main__':
    main()
