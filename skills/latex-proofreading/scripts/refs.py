#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""refs.py — 参考文献核对：DOI 是否指向正确文献、作者名是否与 CrossRef 一致。

用法:
    python refs.py paper.tex --doi         只核对 DOI
    python refs.py paper.tex --authors     只核对作者名
    python refs.py paper.tex --all         两者都核对
    python refs.py refs.bib --all          也支持标准 .bib 文件
    python refs.py paper.tex --all --mailto you@example.com
                                           附带真实邮箱（**建议**，见下）

支持两种格式：本模板的 \\begin{bibwrite} 内嵌条目，以及标准 .bib 文件。

只能核对**有 DOI 的条目**。无 DOI 的（学位论文、软件工具）会单独列出，需人工核。

**请提供真实邮箱**：CrossRef 的 polite pool 要求 User-Agent 里带可联系的邮箱，
用占位域名会被降级、甚至限流。用 `--mailto` 传入，或设环境变量 `CROSSREF_MAILTO`。
使用本脚本即表示你同意 CrossRef 的
[REST API 条款](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)，
请遵守其速率限制（脚本已内置请求间隔）。

设计上刻意保守，因为 CrossRef 的数据本身有已知偏差（详见 references/pitfalls.md）：
  - `issued` 常是**在线首发日期**，不等于卷期年份 → 只警告，不判错
  - 偶尔把全名塞进 family 字段 → 自动降级为"需人工看"
  - 偶尔把姓名顺序写反 → bib 可能才是对的
  - 同姓作者会让逐对比较误报 → 改为集合比较
"""
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

try:  # Windows 控制台默认 GBK，中文会乱码
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

BS = chr(92)
BASE_UA = 'latex-proofreading/1.0'
# CrossRef 的 polite pool 要求 User-Agent 里带**真实可联系**的邮箱。
# 这里刻意不写死任何邮箱（占位域名不合规，写死别人的邮箱更不合规），
# 由 --mailto 或环境变量 CROSSREF_MAILTO 提供，见 set_mailto()。
UA = {'User-Agent': BASE_UA}
API = 'https://api.crossref.org/works/'


def set_mailto(addr):
    """把联系邮箱放进 User-Agent。没提供就照实提示，不伪造。"""
    if addr:
        UA['User-Agent'] = '%s (mailto:%s)' % (BASE_UA, addr)
    else:
        print('提示: 未提供 --mailto，CrossRef 会按匿名请求处理，可能被限流。')
        print('     建议: python refs.py paper.tex --all --mailto 你的邮箱')
        print()


# ---------------------------------------------------------------- 解析

def read(path):
    return open(path, 'rb').read().decode('utf-8')


def split_entries(text):
    """切出 @type{key, ...} 条目，花括号配对。"""
    out = []
    i = 0
    pat = re.compile('@(' + BS + 'w+)' + BS + '{([^,]+),')
    while True:
        m = pat.search(text, i)
        if not m:
            break
        j, depth = m.end(), 1
        while j < len(text) and depth > 0:
            if text[j] == '{':
                depth += 1
            elif text[j] == '}':
                depth -= 1
            j += 1
        out.append((m.group(2).strip(), text[m.end():j - 1]))
        i = j
    return out


def field(body, name):
    m = re.compile(re.escape(name) + BS + r's*=' + BS + r's*' + BS + '{').search(body)
    if not m:
        return None
    j, depth, buf = m.end(), 1, []
    while j < len(body) and depth > 0:
        c = body[j]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                break
        buf.append(c)
        j += 1
    return ''.join(buf).strip()


def strip_html(s):
    """CrossRef 的题名里带 JATS 标记：<sub>2</sub>、<i>t</i> 等，比较前必须去掉。"""
    s = re.sub(r'<[^>]+>', ' ', s or '')
    return s


def clean(s):
    """去掉出版社标记与 LaTeX 命令，留下可比较的文本。

    注意第一个正则必须连反斜杠一起吃掉（\\\\\\?{...}）。
    只匹配 '?{...}' 会留下孤立的反斜杠，随后被「删除反斜杠命令」那一步
    连同后面的单词一起删掉——第一版就是这样把 \\?{IMU} 整块吃没的。
    """
    if not s:
        return ''
    # LaTeX 重音宏先还原成基本字母：M\"uller -> Muller，否则会被判成名字不一致
    s = re.sub(BS + BS + r"['`^\"~=.´]", '', s)
    s = re.sub(BS + r"['`^\"~=.]([A-Za-z])", r'\1', s)
    s = re.sub(BS + r"[uvHckrdb]\{([A-Za-z])\}", r'\1', s)
    s = re.sub(BS + BS + '?' + BS + '{([^}]*)}', r'\1', s)
    s = re.sub(BS + BS + r'(rvt|rvtiop)\w+', ' ', s)
    s = re.sub(BS + BS + r'\w+', ' ', s)
    s = s.replace(BS, ' ')
    for ch in '{}':
        s = s.replace(ch, ' ')
    return re.sub(BS + r's+', ' ', s).strip()


def deaccent(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')


def words(s):
    return set(w for w in re.split(r'[^A-Za-z]+', deaccent(clean(s)).lower()) if len(w) > 1)


def parse_authors(astr):
    out = []
    for a in re.split(r'\s+and\s+', astr or ''):
        a = clean(a)
        if not a:
            continue
        if ',' in a:
            fam, _, giv = a.partition(',')
        else:
            p = a.split()
            fam, giv = (' '.join(p[:-1]), p[-1]) if len(p) > 1 else (a, '')
        out.append((fam.strip(), giv.strip()))
    return out


def fetch(doi):
    url = API + urllib.parse.quote(doi, safe='')
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)['message']


# ---------------------------------------------------------------- 核对

def check_doi(entries):
    print('=' * 74)
    print('DOI 核对')
    print('=' * 74)
    stat = {'ok': 0, 'title_mismatch': 0, 'neterr': 0, 'nodoi': 0}
    problems = []
    for key, body in entries:
        doi = field(body, 'doi')
        bibtitle = clean(field(body, 'title'))
        if not doi:
            stat['nodoi'] += 1
            continue
        try:
            d = fetch(doi)
        except Exception as e:
            stat['neterr'] += 1
            problems.append((key, doi, '取不到（%s）' % str(e)[:40], bibtitle, '',
                             'CNKI 学位论文等不在 CrossRef 库内时 404 属正常'))
            continue
        cr_title = strip_html((d.get('title') or [''])[0])
        A, B = words(bibtitle), words(cr_title)
        sim = len(A & B) / float(len(A | B)) if (A or B) else 0.0
        if sim < 0.75:
            stat['title_mismatch'] += 1
            problems.append((key, doi, '题名不匹配 (相似度 %.2f)' % sim, bibtitle, cr_title,
                             'DOI 可能指向了另一篇文献'))
        else:
            stat['ok'] += 1
        time.sleep(0.12)

    print('  有 DOI 且题名匹配 : %d' % stat['ok'])
    print('  题名不匹配        : %d' % stat['title_mismatch'])
    print('  取不到            : %d' % stat['neterr'])
    print('  无 DOI（需人工）  : %d' % stat['nodoi'])
    if problems:
        print()
        for key, doi, why, bt, ct, note in problems:
            print('  [%s] %s' % (key, doi))
            print('       %s' % why)
            if bt:
                print('       bib: %s' % bt[:100])
            if ct:
                print('       cr : %s' % ct[:100])
            if note:
                print('       %s' % note)
    return stat


def check_year_volume(entries):
    print()
    print('=' * 74)
    print('年份 / 卷 / 页 与 CrossRef 的差异（仅供参考，不要直接判错）')
    print('=' * 74)
    print('  注意：CrossRef 的 issued 常是**在线首发日期**，与卷期所属年份不同。')
    print('        只有「bib 年份与卷号所属年份矛盾」才是真错，需人工判断。')
    print()
    n = 0
    for key, body in entries:
        doi = field(body, 'doi')
        if not doi:
            continue
        try:
            d = fetch(doi)
        except Exception:
            continue
        bib_y = (clean(field(body, 'year')) or '')[:4]
        bib_v = clean(field(body, 'volume')) or ''
        cr_y = str((d.get('issued', {}).get('date-parts') or [['']])[0][0] or '')
        cr_v = str(d.get('volume', '') or '')
        if bib_y and cr_y and bib_y != cr_y:
            n += 1
            print('  %-26s year bib=%s  cr=%s' % (key, bib_y, cr_y))
        if bib_v and cr_v and bib_v.replace('Vol.', '').strip() != cr_v:
            n += 1
            print('  %-26s vol  bib=%s  cr=%s' % (key, bib_v, cr_v))
        time.sleep(0.12)
    if n == 0:
        print('  （无差异）')


def check_authors(entries):
    print()
    print('=' * 74)
    print('作者名核对')
    print('=' * 74)
    print('  方法：把 bib 里所有作者名的词与 CrossRef 返回的词做**集合**比较。')
    print('        用集合而非逐对比较，可避开同姓作者造成的假阳性。')
    print()
    flagged, ok, nodoi = 0, 0, 0
    for key, body in entries:
        doi = field(body, 'doi')
        if not doi:
            nodoi += 1
            continue
        try:
            d = fetch(doi)
        except Exception:
            continue
        bib = set()
        for fam, giv in parse_authors(field(body, 'author')):
            bib |= words(fam) | words(giv)
        bib.discard('and')
        cr = set()
        for a in d.get('author', []):
            cr |= words(a.get('family', '')) | words(a.get('given', ''))
        missing = sorted(bib - cr)
        if missing:
            flagged += 1
            print('  [%s] bib 里有、CrossRef 里没有的词: %s' % (key, missing))
            print('        bib 作者: %s' % ' | '.join('%s %s' % (g, f)
                  for f, g in parse_authors(field(body, 'author'))))
            print('        cr  作者: %s' % ' | '.join(
                '%s %s' % (a.get('family', ''), a.get('given', '')) for a in d.get('author', [])))
            print('        提示：CrossRef 偶尔把全名塞进 family 字段、或把姓名顺序写反 ——')
            print('              遇到这两种情况，bib 可能才是对的，必须人工判断。')
        else:
            ok += 1
        time.sleep(0.12)
    print('  作者名一致 : %d' % ok)
    print('  需人工看   : %d' % flagged)
    print('  无 DOI 跳过: %d' % nodoi)


def main():
    argv = list(sys.argv[1:])
    mailto = os.environ.get('CROSSREF_MAILTO')
    if '--mailto' in argv:                 # 带值的选项：先取值再摘掉，避免被当成位置参数
        i = argv.index('--mailto')
        if i + 1 < len(argv):
            mailto = argv[i + 1]
            del argv[i:i + 2]
        else:
            raise SystemExit('--mailto 缺少取值\n\n' + __doc__)
    args = [a for a in argv if not a.startswith('--')]
    flags = set(a for a in argv if a.startswith('--'))
    if len(args) != 1 or not (flags & {'--doi', '--authors', '--year', '--all'}):
        raise SystemExit(__doc__)
    set_mailto(mailto)
    text = read(args[0])
    entries = split_entries(text)
    print('文件: %s   解析到 %d 条条目' % (args[0], len(entries)))
    print()
    if flags & {'--doi', '--all'}:
        check_doi(entries)
    if flags & {'--year', '--all'}:
        check_year_volume(entries)
    if flags & {'--authors', '--all'}:
        check_authors(entries)
    return 0


if __name__ == '__main__':
    sys.exit(main())
