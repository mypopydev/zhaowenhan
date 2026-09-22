#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""溯源比对.py —— 校验「溯源/题目溯源.pdf」与 README「题目溯源」一节内容一致

用法
----
    python3 工具/溯源比对.py          # 两道闸都跑
    make trace                       # 生成 tex + 编译 PDF + 跑本脚本

两道闸（A 精确、B 抽查）
------------------------
**A. README ↔ 源码/溯源.tex（精确，决定退出码）**
  把两边都归一化成「有意义字符」（汉字、数字、`★▲⊕①–⑳`）后比字符多重集，必须**完全相同**。
  这条闸不经 PDF 抽取，所以没有噪声，能抓住转换器的一切丢字：漏掉的表格单元、没生效的
  `**强调**`（`**` 会原样留在纸上）、被 `\\allowbreak` 拆坏的数学命令（`\\subsetneq` 曾被
  拆成 `\\subset\\allowbreak neq`）……
  两个要注意的地方：
    · tex 侧要**先把 `UNI` 的映射反回来**（`$\\oplus$` → `⊕`），否则映射过的符号会被当成丢字；
    · tex 侧只取 `\\tableofcontents` 之后的正文——扉页那段说明是手写的，不属于 README 的内容。

**B. 生成的 tex ↔ 编译出的 PDF（抽查，只报不判）**
  PDF 的文本靠 `pdftotext` 抽，而 `pdftotext` 对**密集多列表**天生会并字/拆字/丢几个字符
  （实测：变体表那 4 列里，净差 −14 个数字、占 4,592 个数字的 0.3%，且随抽取模式而变：
  默认 −91、`-layout` −6、`-raw` +32）。所以这一闸**不用多重集判成败**，只查三件事：
    · 9 个小节标题是否都在；
    · 几个特征词（孤立元／和谐集／调和子集…）是否都在；
    · `★▲⊕①–⑳` 的计数是否与 README 一致（这几个是「静默丢字」最敏感的地方）。
  并把多重集的残差打印出来，供人工判断是不是宽表抽取所致。
"""
import collections
import difflib
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAPERS = os.path.normpath(os.path.join(HERE, '..'))
README = os.path.join(PAPERS, 'README.md')
TEX = os.path.join(PAPERS, '源码', '溯源.tex')
PDF = os.path.join(PAPERS, '溯源', '题目溯源.pdf')
SECT = '## 题目溯源'

KEEP = re.compile(r'[\u4e00-\u9fff0-9★▲⊕◆①-⑳]')
# 扉页那几个数（与 工具/README转tex.py 的 COVER_RE 保持一致）：README 抽出来后必须真的
# 印到 PDF 首页——2026-09-22 之前它们写死在脚本里，口径从 24 份走到 28 份时静默过期了一整轮
# （扉页还印着 87,571 对 / 24 组 / 12 组），而 A、B 两闸都不看扉页。
COVER_RE = {
    '份': (r'\*\*(\d+) 份试卷的 (\d+) 道\*\*', '{0} 份试卷 {1} 道'),
    '库': (r'参考库的 \*\*([\d,]+) 道\*\*高考真题', '{0} 道高考真题'),
    '对': (r'跨卷两两 \*\*([\d,]+) 对\*\*', '跨卷两两 {0} 对'),
    '档': (r'\*\*逐字同题 (\d+) 组 \+ 同模板变体 (\d+) 组\*\*',
           '逐字同题 {0} 组、同模板变体 {1} 组'),
}
MARKERS = '★▲⊕◆' + ''.join(chr(c) for c in range(0x2460, 0x2474))   # ★▲⊕◆①–⑳
HEADER, RUNHEAD = '题目溯源', '28 份口径（2026-09-22）'

# 与 工具/README转tex.py 的 UNI 保持一致（只列「映射成数学命令」的那些，★▲ 不映射）
UNI = [('×', r'$\times$'), ('→', r'$\to$'), ('≥', r'$\geqslant$'), ('≤', r'$\leqslant$'),
       ('⊕', r'$\oplus$'), ('↔', r'$\leftrightarrow$'), ('⇒', r'$\Rightarrow$'),
       ('⟹', r'$\Longrightarrow$'), ('∧', r'$\wedge$'), ('±', r'$\pm$'),
       ('²', r'$^{2}$'), ('₀', r'$_{0}$'),
       ('∈', r'$\in$'), ('∉', r'$\notin$'), ('⊆', r'$\subseteq$'), ('⊊', r'$\subsetneq$'),
       ('⊂', r'$\subset$'), ('∅', r'$\varnothing$'), ('∁', r'$\complement$'),
       ('∪', r'$\cup$'), ('∩', r'$\cap$'), ('≠', r'$\neq$'), ('∞', r'$\infty$'),
       ('⋯', r'$\cdots$'), ('…', r'$\ldots$')]


# ---------------------------------------------------------------- README 侧
def section_lines():
    lines = io.open(README, encoding='utf-8').read().split('\n')
    i = lines.index(SECT) + 1
    j = i
    while j < len(lines) and not lines[j].startswith('## '):
        j += 1
    return lines[i:j]


def headings():
    return [l[4:].strip() for l in section_lines() if l.startswith('### ')]


def _demath(m):
    s = re.sub(r'\\[a-zA-Z]+', '', m.group(0))
    return re.sub(r'[{}$^_\\]', '', s)


def readme_side():
    out = []
    for l in section_lines():
        if re.match(r'^\s*\|[\s:|-]*\|\s*$', l):        # 表格对齐行
            continue
        l = re.sub(r'\*\*(.+?)\*\*', r'\1', l)          # 生效的加粗
        l = re.sub(r'\*\*', '', l)                      # 不生效的加粗（会留字面 **）
        l = re.sub(r'`([^`]*)`', r'\1', l)              # 行内代码
        l = re.sub(r'\$[^$]*\$', _demath, l)            # 数学：只留数字
        l = re.sub(r'^\s*[>#]\s*', '', l)               # 引用/标题记号
        # 有序列表记号（tex 里是 \item）。**点后必须跟空白**——否则 `0.71 不是随手取的…`
        # 这种「数字开头的正文」会被当成列表项 `0.` 剥掉一个 0（踩过，闸 A 就是靠这一处抓到的）。
        l = re.sub(r'^\s*\d+\.\s+', '', l)
        out.append(l.replace('|', ''))
    return '\n'.join(out)


# ---------------------------------------------------------------- 闸 A：README ↔ tex
# rowcolors／rowcolor 也要整行跳过：`\rowcolors{1}{…}` 里的那个 1 是**参数不是正文**，
# 留在 tex 侧就会让 A 闸凭空多出 N 个「1」（每张表一个）。表头文本本身走 \tabhdrA 宏，
# 由 \newcommand 那一行提供唯一一次计数，见 README转tex.py 的 table_tex。
STRUCT = re.compile(r'^\s*\\(begin|end|toprule|midrule|bottomrule|endhead|endfirsthead'
                    r'|endlastfoot|multicolumn|item|label|rowcolors|rowcolor)\b')


def tex_side():
    t = io.open(TEX, encoding='utf-8').read()
    body = t[t.index(r'\tableofcontents'):t.index(r'\end{document}')]
    for ch, cmd in UNI:                                 # 先反映射，否则映射过的符号算丢字
        body = body.replace(cmd, ch)
    out = []
    for l in body.split('\n'):
        if l.strip().startswith('%') or STRUCT.match(l):
            continue
        l = l.replace(r'\addlinespace[1pt]', '').replace(r'\allowbreak{}', '')
        l = re.sub(r'\\label\{[^}]*\}', '', l)
        l = re.sub(r'\\[a-zA-Z]+', '', l)
        out.append(re.sub(r'[{}$^_\\]', '', l))
    return '\n'.join(out)


def check_a():
    a = ''.join(KEEP.findall(readme_side()))
    b = ''.join(KEEP.findall(tex_side()))
    ca, cb = collections.Counter(a), collections.Counter(b)
    d = {ch: cb[ch] - ca[ch] for ch in set(ca) | set(cb) if ca[ch] != cb[ch]}
    print('A. README ↔ 溯源.tex ：%d / %d 个有意义字符' % (len(a), len(b)))
    if not d:
        print('   ✅ 字符多重集完全一致——转换过程没有丢字、没有残留 `**`、数学命令完好')
        return True
    print('   ❌ 差异 %d 种：' % len(d))
    for ch, v in sorted(d.items(), key=lambda t: -abs(t[1]))[:20]:
        print('      %s  README %d → tex %d  (%+d)' % (ch, ca[ch], cb[ch], v))
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for tag, i1, i2, j1, j2 in [x for x in sm.get_opcodes() if x[0] != 'equal'][:6]:
        print('      [%s] README「…%s⟨%s⟩%s…」 tex「…%s⟨%s⟩%s…」'
              % (tag, a[max(0, i1 - 12):i1], a[i1:i2], a[i2:i2 + 12],
                 b[max(0, j1 - 12):j1], b[j1:j2], b[j2:j2 + 12]))
    return False


# ---------------------------------------------------------------- 闸 B：PDF 抽查
def pdf_text():
    if not os.path.exists(PDF):
        sys.exit('❌ 找不到 %s，先跑 make trace' % PDF)
    txt = subprocess.run(['pdftotext', '-layout', '-f', '3', PDF, '-'],
                         capture_output=True, text=True).stdout
    # 页眉在 -layout 下是**一整行**「题目溯源 …… <当前节名>」，只删子串会把
    # 「题目溯源」留在 PDF 侧（+30/页），必须整行删。
    # （2026-09-22 起右眉改显示当前节名、口径标签下移到页脚；页脚是另一整行
    #  「<口径标签> …… 第 N 页 / 共 M 页」，同样整行删。）
    # ⚠ 中间的分隔符必须写 [ \t]+ 不能写 \s+：\s 会跨行，于是「题目溯源」那一行的
    #   \s+ 一路吃到下一节的标题行，把「3 材料流转」一起删掉（踩过：B 闸连报 6 个缺小节）。
    #   右眉可能为空（节首那页的 \rightmark 还没换），故「后面还有内容」要写成可选。
    txt = re.sub(r'^[ \t\f]*%s([ \t]+.*)?$' % re.escape(HEADER), '', txt, flags=re.M)
    txt = re.sub(r'^[ \t]*%s[ \t]+第 \d+ 页 / 共 \d+ 页[ \t]*$' % re.escape(RUNHEAD),
                 '', txt, flags=re.M)
    txt = txt.replace('（续上表）', '')
    txt = re.sub(r'^\s*\d+\s*$', '', txt, flags=re.M)          # 页码行
    for h in headings():                                       # 章节标题前的自动序号
        txt = re.sub(r'^\s*\d+\s+%s' % re.escape(h), h, txt, flags=re.M)
    return txt


def cover_strings():
    """扉页上应该出现的几串数字（从 README 抽，格式化方式与 README转tex.py 一致）"""
    txt = io.open(README, encoding='utf-8').read()
    out = []
    for k, (pat, fmt) in COVER_RE.items():
        m = re.search(pat, txt)
        if not m:
            sys.exit('❌ README 里读不出扉页数字（%s）——核对摘要表的措辞改了？'
                     '同步改 COVER_RE（两处）' % k)
        out.append(fmt.format(*[g.replace('{,}', ',') for g in m.groups()]))
    return out


def check_cover():
    """C 闸：扉页数字必须是从 README 抽的当前值（防止再写死、再过期）"""
    txt = subprocess.run(['pdftotext', '-layout', '-f', '1', '-l', '1', PDF, '-'],
                         capture_output=True, text=True).stdout
    flat = re.sub(r'\s+', '', txt)
    miss = [s for s in cover_strings() if re.sub(r'\s+', '', s) not in flat]
    if miss:
        print('   ❌ 扉页缺（或已过期）：%s' % '、'.join(miss))
        return False
    print('   扉页数字（%s）：与 README 一致 ✅' % '、'.join(cover_strings()))
    return True


def check_b():
    txt = pdf_text()
    n = ''.join(KEEP.findall(txt))
    print('B. 溯源.tex ↔ 题目溯源.pdf ：PDF 侧抽出 %d 个有意义字符' % len(n))
    ok = True
    for h in headings():
        k = ''.join(KEEP.findall(h))
        if k not in n:
            print('   ❌ 缺小节：%s' % h)
            ok = False
    a = ''.join(KEEP.findall(readme_side()))
    # 特征词从 README 侧筛一遍：只在 README 里确实出现过的才作数（否则是探针自己编的词）
    probes = [p for p in ['孤立元', '和谐集', '调和子集', '可积数集', '特征数',
                          '伙伴关系集合', '含参二次方程', '封闭集', '单封集', '好集']
              if ''.join(KEEP.findall(p)) in a]
    miss = [p for p in probes if ''.join(KEEP.findall(p)) not in n]
    if miss:
        print('   ❌ 缺特征词：%s' % '、'.join(miss))
        ok = False
    ca, cb = collections.Counter(a), collections.Counter(n)
    d = {ch: cb[ch] - ca[ch] for ch in set(ca) | set(cb) if ca[ch] != cb[ch]}
    md = {ch: v for ch, v in d.items() if ch in MARKERS}
    print('   小节 %d 个、特征词 %d 个：%s' % (len(headings()), len(probes), '都在 ✅' if ok else '有缺 ❌'))
    print('   标记符计数（★▲⊕①–⑳）：%s'
          % ('与 README 一致 ✅' if not md else '差 %s ❌' % md))
    ok = check_cover() and ok
    if d:
        print('   多重集残差 %d 种（pdftotext 对密集多列宽表会并/拆/丢几个字符，'
              '默认模式 −91、-layout −6，属抽取噪声；量级要人工看一眼）：' % len(d))
        for ch, v in sorted(d.items(), key=lambda t: -abs(t[1]))[:10]:
            print('      %s  README %d → PDF %d  (%+d)' % (ch, ca[ch], cb[ch], v))
    return ok and not md


def main():
    a_ok = check_a()
    print()
    b_ok = check_b()
    print()
    if a_ok and b_ok:
        print('✅ 两道闸都通过')
        return 0
    print('❌ 有闸未过，见上')
    return 1


if __name__ == '__main__':
    sys.exit(main())
