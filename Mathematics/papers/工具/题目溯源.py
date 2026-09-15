#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""题目溯源 —— 本库题干 × 高考真题库 的骨架比对（README「方法与局限」一节的参考实现）

用法
----
    python3 题目溯源.py 全跑                  两库都抽，然后比对本库全部卷
    python3 题目溯源.py 全跑 高一10 高一11    只比对指定卷（卷号写 高一10 / 高一a 这样）
    python3 题目溯源.py 抽取                  只抽本库题干骨架（papers/源码/*.tex）
    python3 题目溯源.py 建库                  只抽高考库题干骨架
    python3 题目溯源.py 比对 高一10           用已有骨架做比对

    高考库路径默认取 /Users/barryjzhao/Sources/AI/Gaokao-Math-Problems-Compilation/content，
    可用环境变量 GAOKAO_MATH_LIB 覆盖。中间结果写到系统的临时目录（不污染仓库）。

判据（与 README 完全一致）
--------------------------
  · 骨架 = 去掉 LaTeX 命令，**保留汉字、数字与数学符号**（`\\cap` `\\cup` `\\subseteq`
    `\\varnothing` `\\mid` 等一律映射成符号，绝不剥成空串——剥了会把不同题判成同题）；
    **CJK 标点与 ①-⑳ 序号不计**、**选择题的选项按行首「A.」切掉**（选项是跨题复用的套话）。
  · 逐字同题：最长公共子串 ≥ 25 字且公共串含 ≥ 8 个汉字，或整段相似度 ≥ 0.95 且含 ≥ 5 个汉字。
  · 同模板变体：最长公共子串 ≥ 12 字且含 ≥ 8 个汉字，或整段相似度 ≥ 0.72 且含 ≥ 5 个汉字。
  · 汉字下限是必需的：元素表一类的**纯数字公共串**（`=1,2,3,4,5,6,7`）轻松凑够 12 字，
    不设下限就会给每道「含 7 个元素的集合题」刷出一屏假命中。

踩过的坑（改这个脚本前先读）
----------------------------
  ① **抽题干前必须先去 `%` 注释**：注释里的 `\\item`（如「压轴题：在其 \\item 前先量一下版面」）
     会被当成真题目，凭空多出两题（高一12、高一17 各一处，正是这个原因）。
  ② **短宏替换要加「后不接字母」的守卫**：`\\i`→i 会把 `\\item` 变成 `item`、`\\e`→∅ 会把 `\\end`
     变成 `∅nd`——前者让「2014 福建卷」那条该命中的题漏掉。
  ③ **题号要按 `\\setcounter{enumi}{K}` 换算**：节内序号 + K 才是卷面印号；不换算会把
     「第 3 题」当成「第 1 题」。附加题另起编号的卷（如 高一a）要单独看。
  ④ 改卷号/题号引用时（核对结果回写 README 用）注意「带前缀」与「裸编号」两种形态，
     且**必须用占位符做映射**，否则 `13→11→b` 会连环改坏。
"""
import difflib
import io
import json
import os
import re
import sys
import glob
import tempfile
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, '..', '源码'))
LIB = os.environ.get(
    'GAOKAO_MATH_LIB',
    '/Users/barryjzhao/Sources/AI/Gaokao-Math-Problems-Compilation/content')
OUT = os.path.join(tempfile.gettempdir(), '题目溯源')

# 与 高一b 同卷的对号副本，不重复计入统计
SKIP = ('高一16',)

# ---------------------------------------------------------------- 骨架化
SYM = [   # 数学符号一律保留（顺序有讲究：长命令在前，短宏带「后不接字母」守卫）
    (r'\varnothing', '∅'), (r'\emptyset', '∅'), (r'\complement', '∁'), (r'\setminus', '∖'),
    (r'\subseteq', '⊆'), (r'\subsetneq', '⊊'), (r'\subset', '⊂'), (r'\supseteq', '⊇'),
    (r'\supsetneq', '⊋'), (r'\supset', '⊃'), (r'\nsubseteq', '⊄'), (r'\notin', '∉'),
    (r'\in', '∈'), (r'\mid', '|'), (r'\leqslant', '≤'), (r'\geqslant', '≥'), (r'\neq', '≠'),
    (r'\le', '≤'), (r'\ge', '≥'), (r'\cap', '∩'), (r'\cup', '∪'), (r'\pm', '±'),
    (r'\times', '×'), (r'\cdot', '·'), (r'\div', '÷'), (r'\infty', '∞'),
    (r'\Rightarrow', '⇒'), (r'\Leftrightarrow', '⇔'), (r'\rightarrow', '→'),
    (r'\pi', 'π'), (r'\triangle', '△'), (r'\varphi', 'φ'), (r'\alpha', 'α'), (r'\beta', 'β'),
    (r'\theta', 'θ'), (r'\lambda', 'λ'), (r'\mu', 'μ'), (r'\overline', '~'), (r'\sqrt', '√'),
    (r'\mathbb{R}', 'R'), (r'\mathbb{N}', 'N'), (r'\mathbb{Z}', 'Z'), (r'\mathbb{Q}', 'Q'),
    (r'\mathbb{C}', 'C'),
    (r'\R(?![A-Za-z])', 'R'), (r'\N(?![A-Za-z])', 'N'), (r'\Z(?![A-Za-z])', 'Z'),
    (r'\Q(?![A-Za-z])', 'Q'), (r'\C(?![A-Za-z])', 'C'), (r'\i(?![A-Za-z])', 'i'),
    (r'\fillinblank', '____'), (r'\blankline', '____'), (r'\sub', '⊆'), (r'\bsub', '⊊'),
    (r'\e(?![A-Za-z])', '∅'), (r'\card', 'card'),
    (r'\operatorname', ''), (r'\text', ''), (r'\mathrm', ''),
    (r'\dfrac', ''), (r'\tfrac', ''), (r'\frac', ''), (r'\left', ''), (r'\right', ''),
    (r'\quad', ''), (r'\\', ''), (r'\,', ''), (r'\;', ''), (r'\!', ''), (r'\bigsec', ''),
]
CJK = re.compile(r'[\u4e00-\u9fff]')


def skeleton(t):
    """LaTeX 片段 → 骨架（汉字/数字/数学符号，标点与序号不计）"""
    t = re.sub(r'(?<!\\)%[^\n]*', '', t)                  # 注释（见「坑①」）
    for a, b in SYM:
        t = t.replace(a, b)
    t = re.sub(r'\\begin\{[^}]*\}|\\end\{[^}]*\}', '', t)
    t = re.sub(r'\\[a-zA-Z]+', '', t)
    t = re.sub(r'[{}$&~^_\\()\[\]]', '', t)
    t = re.sub(r'[，。；、：？！“”‘’（）《》〈〉【】—～·…]', '', t)   # CJK 标点
    t = re.sub(r'[①-⑳⑴-⒇]', '', t)                              # 序号
    t = t.replace('circlelist', '').replace('item', '')           # 库的列表环境残留
    return re.sub(r'[\s\u3000\u00a0]+', '', t)


def cjk(s):
    return len(CJK.findall(s))


def grams(s, n=12):
    return {s[i:i + n] for i in range(max(0, len(s) - n + 1))}


def judge(a, b):
    """返回 (档位, 最长公共子串长, 整段相似度, 公共串)；档位 ∈ {dup, var, None}"""
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    m = sm.find_longest_match(0, len(a), 0, len(b))
    blk, L, r, c = a[m.a:m.a + m.size], m.size, sm.ratio(), cjk(a[m.a:m.a + m.size])
    if (L >= 25 and c >= 8) or (r >= 0.95 and c >= 5):
        return 'dup', L, r, blk
    if (L >= 12 and c >= 8) or (r >= 0.72 and c >= 5):
        return 'var', L, r, blk
    return None, L, r, blk


# ---------------------------------------------------------------- 抽本库题干
def drop_braced(t, cmd):
    """删掉 \\cmd{...}（支持嵌套花括号）"""
    out, i, tag = [], 0, cmd + '{'
    while True:
        j = t.find(tag, i)
        if j < 0:
            out.append(t[i:])
            return ''.join(out)
        out.append(t[i:j])
        k, d = j + len(tag), 1
        while k < len(t) and d > 0:
            d += (t[k] == '{') - (t[k] == '}')
            k += 1
        i = k


def strip_answers(t):
    t = re.sub(r'(?<!\\)%[^\n]*', '', t)                  # 注释（坑①）
    t = re.sub(r'\\ifanswer.*?\\fi', '', t, flags=re.S)   # 解析块
    t = re.sub(r'\\ansspace\*?(\[[^\]]*\])?', '', t)
    t = drop_braced(t, '\\ansneed')
    t = drop_braced(t, '\\ans')                           # 行内答案
    return t


def our_stems():
    out = []
    for f in sorted(glob.glob(os.path.join(SRC, '高一*.tex'))):
        name = os.path.basename(f)[:-4]
        if name.startswith(SKIP):
            continue
        body = strip_answers(io.open(f, encoding='utf-8').read())
        body = body[body.index('\\begin{document}'):]
        segs = re.split(r'\\bigsec\{([^}]*)\}', body)     # [前言, 节名, 节体, ...]
        for k in range(1, len(segs), 2):
            sec, s = segs[k], segs[k + 1]
            mo = re.search(r'setcounter\{enumi\}\{(\d+)\}', s)
            off = int(mo.group(1)) if mo else 0           # 坑③
            toks = list(re.finditer(r'\\begin\{enumerate\}|\\end\{enumerate\}|\\item\b', s))
            depth = num = 0
            for idx, m in enumerate(toks):
                g = m.group(0)
                if g.startswith('\\begin'):
                    depth += 1
                    continue
                if g.startswith('\\end'):
                    depth -= 1
                    continue
                if depth != 1:                            # 只收一级 \item
                    continue
                end = toks[idx + 1].start() if idx + 1 < len(toks) else len(s)
                num += 1
                stem = re.split(r'\\begin\{enumerate\}', s[m.end():end])[0]
                opt = re.search(r'\n\s*A[.．]\s*[\\$\u4e00-\u9fff]', stem)
                if opt:                                   # 选项不入骨架
                    stem = stem[:opt.start()]
                lab = '附加%d' % (off + num) if '附加' in sec else str(off + num)
                out.append({'paper': name, 'sec': sec, 'num': off + num, 'lab': lab,
                            'raw': stem.strip(), 'sk': skeleton(stem)})
    return out


# ---------------------------------------------------------------- 抽高考库
def lib_stems():
    out = []
    for f in sorted(glob.glob(os.path.join(LIB, '**', '*.tex'), recursive=True)):
        txt = io.open(f, encoding='utf-8').read()
        marks = [(m.start(), m.group(1), m.group(2))
                 for m in re.finditer(r'\\(chapter|section)\{([^}]*)\}', txt)]
        for m in re.finditer(r'\\begin\{problem\}(.*?)\\end\{problem\}', txt, re.S):
            chap = sec = ''
            for p0, kind, nm in marks:
                if p0 >= m.start():
                    break
                chap, sec = (nm, sec) if kind == 'chapter' else (chap, nm)
            stem = re.split(r'\\choices|\\begin\{answer\}|\\begin\{solution\}', m.group(1))[0]
            out.append({'src': chap, 'sec': sec, 'file': os.path.relpath(f, LIB),
                        'raw': stem.strip(), 'sk': skeleton(stem)})
    return out


# ---------------------------------------------------------------- 比对
def load(path):
    return json.load(io.open(path, encoding='utf-8'))


def cmd_extract():
    os.makedirs(OUT, exist_ok=True)
    st = our_stems()
    json.dump(st, io.open(os.path.join(OUT, 'our_stems.json'), 'w', encoding='utf-8'),
              ensure_ascii=False)
    c = Counter(x['paper'] for x in st)
    print('本库题干 %d 道（%d 份，已排除 %s）' % (len(st), len(c), '／'.join(SKIP)))
    for k, v in sorted(c.items()):
        print('   %-42s %d' % (k, v))


def cmd_build():
    os.makedirs(OUT, exist_ok=True)
    st = lib_stems()
    json.dump(st, io.open(os.path.join(OUT, 'lib_stems.json'), 'w', encoding='utf-8'),
              ensure_ascii=False)
    print('高考库题干 %d 道（现读自 %s）' % (len(st), LIB))


def cmd_compare(targets):
    our = load(os.path.join(OUT, 'our_stems.json'))
    lib = load(os.path.join(OUT, 'lib_stems.json'))
    for x in our:
        x['g'] = grams(x['sk'])
    for y in lib:
        y['g'] = grams(y['sk'])
    if targets:
        our_t = [x for x in our if any(x['paper'].startswith(t) for t in targets)]
    else:
        our_t = our[:]

    print('① 与高考库比对（%d 道 × %d 道）' % (len(our_t), len(lib)))
    for x in our_t:
        rows = []
        for y in lib:
            if not (x['g'] & y['g']):
                continue
            kind, L, r, blk = judge(x['sk'], y['sk'])
            if kind:
                rows.append((kind, L, r, blk, y))
        rows.sort(key=lambda t: (t[0] != 'dup', -t[1]))
        head = '   第%s题 %s' % (x['lab'], x['sk'][:46])
        if not rows:
            print('%s —— 无命中' % head)
            continue
        print('%s' % head)
        for kind, L, r, blk, y in rows[:4]:
            print('      %-3s LCS=%-3d r=%.3f cjk=%-2d 出处=%s｜%s'
                  % (kind.upper(), L, r, cjk(blk), y['src'], y['sec']))
            print('          公共串：%s' % blk[:56])

    print()
    print('② 跨卷两两（%d 道 → %d 对）' % (len(our), len(our) * (len(our) - 1) // 2))
    dup, var = [], []
    for i in range(len(our)):
        for j in range(i + 1, len(our)):
            a, b = our[i], our[j]
            if a['paper'] == b['paper'] or not (a['g'] & b['g']):
                continue
            kind, L, r, blk = judge(a['sk'], b['sk'])
            if kind == 'dup':
                dup.append((a, b, L, r, blk))
            elif kind == 'var':
                var.append((a, b, L, r, blk))
    par = {}

    def find(x):
        par.setdefault(x, x)
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    key = lambda z: (z['paper'], z['lab'])
    for a, b, *_ in dup:
        ra, rb = find(key(a)), find(key(b))
        if ra != rb:
            par[ra] = rb
    groups = defaultdict(list)
    for k in par:
        groups[find(k)].append(k)
    print('   逐字同题对 %d ；变体对 %d ；分组后逐字同题 %d 组' % (len(dup), len(var), len(groups)))
    for _, mem in sorted(groups.items(), key=lambda t: -len(t[1])):
        if len(mem) >= 2:
            print('      %d 份：%s' % (len(mem),
                                      '、'.join('%s#%s' % (m[0], m[1]) for m in sorted(mem))))
    print('   —— 含 %s 的变体对 ——' % '／'.join(targets) if targets else '')
    for a, b, L, r, blk in var:
        if not targets or any(a['paper'].startswith(t) or b['paper'].startswith(t) for t in targets):
            print('      %s#%s × %s#%s  LCS=%d r=%.3f | %s'
                  % (a['paper'], a['lab'], b['paper'], b['lab'], L, r, blk[:36]))


def main():
    argv = sys.argv[1:]
    cmd = argv[0] if argv else '全跑'
    targets = argv[1:]
    if cmd == '抽取':
        cmd_extract()
    elif cmd == '建库':
        cmd_build()
    elif cmd == '比对':
        cmd_compare(targets)
    elif cmd == '全跑':
        cmd_extract()
        cmd_build()
        cmd_compare(targets)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
