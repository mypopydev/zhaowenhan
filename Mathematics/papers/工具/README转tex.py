#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""README转tex.py —— 把 README.md 的「题目溯源」一节排成一份独立的 LaTeX 报告

用法
----
    python3 工具/README转tex.py          # 生成 源码/溯源.tex
    make trace                           # 上面这一步 + 编译出 溯源/题目溯源.pdf

为什么这样分工（改这个脚本前先读）
----------------------------------
  · **段落、标题、列表、引用块交给 pandoc**（`pandoc -f gfm -t latex`）。实测它对这些都
    处理得干净：`**加粗**`→`\\textbf{}`、`` `代码` ``→`\\texttt{}`（连 `\\item`、`_`、`%`
    都转义正确）、`>`→`quote` 环境、有序/无序列表、`$…$`→`\\(…\\)`。
  · **表格绝不能交给 pandoc**：它出的是 `longtable{@{}lcl@{}}`，`l` 列**根本不换行**，
    逐卷核对表里有一格长达 1145「汉字宽」，交给它必然冲出页面。9 张表由本脚本自己生成
    `xltabular`，列宽按内容算。
  · **Unicode 数学符号 pandoc 不会转**（实测 `× → · ≥ ② ▲ ★ ① ⊕ ↔ ≤ ≈ ² ∧ ± ₀ ⇒` 原样输出），
    由本脚本后处理。**只动数学模式外**的符号——README 里 `≥` 有时在 `$…$` 内
    （`$r\\ge0.71$`）、有时在正文（`≥ 12 字`），一律替换会把前者弄坏。

踩过的坑
--------
  ① **表格列宽不能用「最大值」算**：逐卷核对表第 3 列有一格长 1145 单位，按最大值分配
     会把前两列（「高一05」「9 张 / 18 题」）饿死到不可读。改用「表头宽与列内容宽的
     **P60** 的较大者」，再夹逼到 [1.1cm, 52% 文本宽]。
  ② **列间距要扣**：longtable 每列两侧各有 `\\tabcolsep`（默认 6pt），5 列就是 2.1cm。
     不扣就会撑出文本宽——这是 xltabular 最常见的溢出原因。
  ③ **单元格要批量送 pandoc**：逐个单元格调用 pandoc 是 350 次进程、十几秒。用哨兵行
     `CELLSEP` 把 350 格拼成一份文档一次转换，再按哨兵切回来（实测哨兵原样通过）。
  ④ **数学模式内的长公式不会断行**：`p{}` 列里 `$…$` 是一个原子，TeX 不给断点。故在
     单元格的数学里于 `=` `+` `,` `\\mid` `\\cup` `\\cap` `\\subseteq` 等之后插 `\\allowbreak`。
     验收标准是「编译日志无 Overfull \\hbox」。
  ⑤ **①–⑳ 不要映射**：它们已在 `common.sty` 的 `xeCJKDeclareCharClass` 里走中文字体，
     映射成数学命令反而会把中文引号排坏。★▲ 同理走字符类（`common.sty` 里已补两段）。
"""
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAPERS = os.path.normpath(os.path.join(HERE, '..'))
README = os.path.join(PAPERS, 'README.md')
OUT = os.path.join(PAPERS, '源码', '溯源.tex')

SECT = '## 题目溯源'          # 只转这一节（到下一个 `## ` 为止）
TITLE = '题目溯源'
RUN_DATE = '2026-09-28'      # 口径标签上的日期；溯源比对.py 的 RUNHEAD 要与之保持一致

# geometry 边距 2.5cm、A4 → 文本宽 16cm；longtable 每列两侧各 \tabcolsep
TEXTWIDTH_CM = 21.0 - 2 * 2.5
TABCOLSEP_PT = 6.0
PT_PER_CM = 28.4527

CELLSEP = 'CELLSEP'
# 表格占位符。**必须定长**（零填充）：早年写成 `TABPLACEHOLDER%d`，于是 `TABPLACEHOLDER1`
# 成了 `TABPLACEHOLDER10` 的**前缀**——表数涨到 11 张时，替换第 2 张表那一步会把第 11 张的
# 占位符一起吃掉（`TABPLACEHOLDER10` → `<第2张表的 tex>0`），结果**最后一张表整块丢失、
# 第 2 张表在文里出现两遍**，而且 A 闸（README ↔ tex 字符多重集）**照样能过**——
# 因为「丢的内容」与 README 的差异要到 B 闸才露出来。2026-09-28 加第 11 张表
# （①机判「未计入」台账）时才踩到：症状是 A 闸报「少 1400 字」、B 闸报「缺小节／缺特征词」、
# 页数从 62 掉到 57。零填充后不存在谁是谁的前缀。
PLACEHOLDER = 'TABPLACEHOLDER%03d'

# 扉页那几个数（份数 / 题数 / 参考库 / 跨卷对数 / 两档组数）**一律从 README 的「核对摘要」表抽**，
# 不在脚本里写死——写死过一次：2026-09-22 并入高一25—28 后，扉页还印着「87,571 对、24 组、12 组」
# （口径已到 118,828 对、26 组、14 组），而 计数核对.py 管不到扉页，静默过期了一整轮。
# 溯源比对.py 里有一道闸盯这些数是否真的印到了 PDF 首页。
COVER_RE = {
    '份': r'\*\*(\d+) 份试卷的 (\d+) 道\*\*',
    '库': r'参考库的 \*\*([\d,]+) 道\*\*高考真题',
    '对': r'跨卷两两 \*\*([\d,]+) 对\*\*',
    '档': r'\*\*逐字同题 (\d+) 组 \+ 同模板变体 (\d+) 组\*\*',
}

# Unicode → LaTeX。左边一列在**数学模式外**出现时才替换。
# 不在表里的三类：
#   ① ①–⑳、★、▲ —— 走 common.sty 的 xeCJKDeclareCharClass（中文字体里有这些字形）。
#      ★ 试过映射成 $\bigstar$，排出来是 ⋆（U+22C6），与 README 的 ★（U+2605）不是同一个字，
#      故不映射、改走字符类——这样 PDF 里的字形与 README 完全一致。
#   ② – — · 「」（）等标点 —— 字体里有字形，动了反而会把中文标点排坏。
#   ③ 行内代码（\texttt）里的符号 —— 见 map_unicode 的保护段。
UNI = [
    ('×', r'$\times$'), ('→', r'$\to$'), ('≥', r'$\geqslant$'), ('≤', r'$\leqslant$'),
    ('≈', r'$\approx$'),
    ('⊕', r'$\oplus$'), ('↔', r'$\leftrightarrow$'), ('⇒', r'$\Rightarrow$'),
    ('⟹', r'$\Longrightarrow$'), ('∧', r'$\wedge$'), ('±', r'$\pm$'),
    ('²', r'$^{2}$'), ('₀', r'$_{0}$'),
    ('∈', r'$\in$'), ('∉', r'$\notin$'), ('⊆', r'$\subseteq$'), ('⊊', r'$\subsetneq$'),
    ('⊂', r'$\subset$'), ('∅', r'$\varnothing$'), ('∁', r'$\complement$'),
    ('∪', r'$\cup$'), ('∩', r'$\cap$'), ('≠', r'$\neq$'), ('∞', r'$\infty$'),
    ('⋯', r'$\cdots$'), ('…', r'$\ldots$'),
]

# 数学模式内可作断点的符号（见「坑④」）
# ⚠ 必须按长度降序、且加「后不接字母」守卫：`\subset` 是 `\subsetneq`／`\subseteq` 的前缀，
#   先替换短的会把 `\subsetneq` 拆成 `\subset\allowbreak neq`，排出来是 `⊄=`。
#   2026-09-15 第一版就踩了这个（出处表那一行的 $\varnothing\subsetneq M\subsetneq\mathbb R$）。
BREAK_AFTER = [r'\subseteq', r'\subsetneq', r'\setminus', r'\geqslant', r'\leqslant',
               r'\subset', r'\mid', r'\cup', r'\cap', r'\to', r'\times', '=', '+', ',']


def thousands(s):
    """1234567 → '1{,}234{,}567'（LaTeX 里直接写 1,234,567 会被当 punct，间距不对）"""
    n = int(str(s).replace(',', ''))
    return '{:,}'.format(n).replace(',', '{,}')


def readme_stats():
    """从 README「核对摘要」表抽出扉页要用的 6 个数，返回 (文本, 数表)"""
    txt = io.open(README, encoding='utf-8').read()
    m = {k: re.search(v, txt) for k, v in COVER_RE.items()}
    miss = [k for k, v in m.items() if not v]
    if miss:
        sys.exit('❌ README 里读不出扉页数字（%s）——核对摘要表的措辞改了？'
                 '同步改 COVER_RE' % '、'.join(miss))
    return {'份': m['份'].group(1), '题': m['份'].group(2),
            '库': thousands(m['库'].group(1)), '对': thousands(m['对'].group(1)),
            '逐字': m['档'].group(1), '变体': m['档'].group(2)}


# ---------------------------------------------------------------- 切分与分块
def read_section():
    """切出 `## 题目溯源` 到下一个 `## ` 之间的正文（不含标题行本身）"""
    lines = io.open(README, encoding='utf-8').read().split('\n')
    try:
        i = lines.index(SECT)
    except ValueError:
        sys.exit('❌ README 里找不到 `%s`' % SECT)
    j = i + 1
    while j < len(lines) and not lines[j].startswith('## '):
        j += 1
    sec = lines[i + 1:j]
    # 表格必须顶层。写成引用块（行首 `> |`）时 split_blocks 认不出，会整块丢给 pandoc；
    # pandoc 在 quote 环境里排 longtable，编译报 `No counter 'none' defined`，PDF 只编到一半、
    # 而 A 闸（字符多重集）却仍可能过——2026-09-26 踩过，症状是 B 闸「PDF 侧只抽出 5 千字」。
    bad = [k for k, l in enumerate(sec, i + 2) if re.match(r'^\s*>\s*\|', l)]
    if bad:
        sys.exit('❌ README「%s」节第 %s 行把表格写进了引用块（行首 `> |`）。\n'
                 '   请把表格移出引用块——本仓库的表一律顶层，README转tex.py 才认得出并按列宽生成 '
                 'xltabular。' % (SECT, '、'.join(map(str, bad))))
    return sec


def split_blocks(lines):
    """切成 [('md', [行])] / [('table', [行])]；表格块 = 连续的 `|` 行"""
    blocks, cur, kind = [], [], None

    def flush():
        if cur:
            blocks.append((kind, list(cur)))
        del cur[:]

    for l in lines:
        k = 'table' if re.match(r'^\s*\|', l) else 'md'
        if kind and k != kind:
            flush()
        kind = k
        cur.append(l)
    flush()
    return blocks


def parse_table(rows):
    """GFM 表 → (header, aligns, data)。aligns ∈ {'l','c','r'}"""
    def cells(l):
        s = l.strip()
        if s.startswith('|'):
            s = s[1:]
        if s.endswith('|'):
            s = s[:-1]
        return [c.strip() for c in re.split(r'(?<!\\)\|', s)]

    header = cells(rows[0])
    aligns = []
    for c in cells(rows[1]):
        left, right = c.startswith(':'), c.endswith(':')
        aligns.append('c' if left and right else 'r' if right else 'l')
    data = [cells(r) for r in rows[2:]]
    # 补齐/截断，防止行列数不齐
    n = len(header)
    for r in data:
        r += [''] * (n - len(r))
        del r[n:]
    return header, aligns, data


# ---------------------------------------------------------------- 显示宽度
def disp_width(md_text):
    """估一行 markdown 的显示宽度：汉字/全角算 2，其余算 1；数学按源码长度打六折"""
    t = re.sub(r'\*\*|`', '', md_text)
    total = 0.0
    for part in re.split(r'(\$[^$]*\$)', t):
        if part.startswith('$') and part.endswith('$') and len(part) > 1:
            total += len(part) * 0.6
        else:
            total += sum(2 if (0x4e00 <= ord(c) <= 0x9fff or 0x3000 <= ord(c) <= 0x303f
                               or 0xff00 <= ord(c) <= 0xffef) else 1 for c in part)
    return total


def col_widths(header, data):
    """列宽（cm）。见「坑①」「坑②」"""
    n = len(header)
    need = []
    for k in range(n):
        lens = sorted(disp_width(r[k]) for r in data) or [4.0]
        p60 = lens[min(len(lens) - 1, int(0.6 * len(lens)))]
        need.append(max(disp_width(header[k]), p60, 4.0))
    avail = TEXTWIDTH_CM - 2 * TABCOLSEP_PT / PT_PER_CM * n
    tot = sum(need)
    ws = [x / tot * avail for x in need]
    lo, hi = 1.1, avail * 0.52
    for _ in range(6):
        ws = [min(max(w, lo), hi) for w in ws]
        s = sum(ws)
        ws = [w / s * avail for w in ws]
    s = sum(ws)
    return [w / s * avail for w in ws]


# ---------------------------------------------------------------- pandoc
def pandoc(md, shift=None):
    cmd = ['pandoc', '-f', 'gfm', '-t', 'latex', '--wrap=preserve']
    if shift:
        cmd += ['--shift-heading-level-by=%d' % shift]
    p = subprocess.run(cmd, input=md, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit('❌ pandoc 失败：\n' + p.stderr)
    return p.stdout


def cells_to_tex(texts):
    """一批单元格文本 → 逐格 LaTeX（一次 pandoc，见「坑③」）"""
    if not texts:
        return []
    md = ('\n\n%s\n\n' % CELLSEP).join(texts)
    out = pandoc(md)
    parts = out.split('\n%s\n' % CELLSEP)
    parts = [p.strip() for p in parts]
    if len(parts) != len(texts):
        sys.exit('❌ 单元格切分失败：送 %d 格、回 %d 段' % (len(texts), len(parts)))
    return parts


# ---------------------------------------------------------------- 后处理
def strip_labels(tex):
    """删掉 pandoc 给标题自动加的 \\label{ux…}（中文标题会变成一串 ux5c0f…）"""
    return re.sub(r'(\\section\{[^{}]*\})\\label\{[^{}]*\}', r'\1', tex)


def map_unicode(tex):
    """把数学模式外的 Unicode 符号换成 LaTeX 命令（见「坑⑤」）

    先按「受保护段 / 普通段」切开，只对普通段替换。受保护段有三类：
      `\\(…\\)` `\\[…\\]` 数学，以及 `\\texttt{…}`（代码里塞 `$\\bigstar$` 会直接报错）。
    """
    segs, buf, i, n = [], [], 0, len(tex)
    while i < n:
        if tex.startswith(r'\(', i):
            end = tex.find(r'\)', i)
            end = n if end < 0 else end + 2
        elif tex.startswith(r'\[', i):
            end = tex.find(r'\]', i)
            end = n if end < 0 else end + 2
        elif tex.startswith(r'\texttt{', i):
            k, d = i + len(r'\texttt{'), 1
            while k < n and d > 0:
                d += (tex[k] == '{') - (tex[k] == '}')
                k += 1
            end = k
        else:
            buf.append(tex[i])
            i += 1
            continue
        segs.append((False, ''.join(buf)))
        buf = []
        segs.append((True, tex[i:end]))
        i = end
    segs.append((False, ''.join(buf)))
    out = []
    for prot, s in segs:
        if prot:
            out.append(s)
        else:
            for a, b in UNI:
                s = s.replace(a, b)
            out.append(s)
    return ''.join(out)


def breakable(tex):
    """单元格数学里插断行点（见「坑④」）；只处理 `\\(…\\)` 内。

    BREAK_AFTER 已按长度降序，配合「后不接字母」守卫，`\\subsetneq` 不会被 `\\subset` 吃掉。
    """
    pat = re.compile('(' + '|'.join(re.escape(t) for t in BREAK_AFTER) + r')(?![A-Za-z])')

    def fix(m):
        return pat.sub(lambda x: x.group(1) + r'\allowbreak ', m.group(0))
    return re.sub(r'\\\(.*?\\\)', fix, tex, flags=re.S)


def break_paths(tex):
    """让 `\\texttt{…}`（行内代码）在 `/` 与 `-` 之后可以断行。

    `\\texttt` 里的内容既不拆词也不断行，而这一节里有好几条整段路径与文件名
    （`~/Sources/AI/Gaokao-Math-Problems-Compilation`、`figures/venn_MP_minus_S.png`），
    实测会撑出 44pt 的 Overfull \\hbox。只在这两种字符后加断点，不加连字符。
    """
    out, i, n = [], 0, len(tex)
    while i < n:
        if tex.startswith(r'\texttt{', i):
            k, d = i + len(r'\texttt{'), 1
            while k < n and d > 0:
                d += (tex[k] == '{') - (tex[k] == '}')
                k += 1
            inner = tex[i + len(r'\texttt{'):k - 1]
            inner = re.sub(r'([/-])', r'\1\\allowbreak{}', inner)
            out.append(r'\texttt{' + inner + '}')
            i = k
        else:
            out.append(tex[i])
            i += 1
    return ''.join(out)


# ---------------------------------------------------------------- 表格
def cell_polish(c):
    """单元格最终处理：Unicode 映射 → 代码路径可断 → 数学可断"""
    return breakable(break_paths(map_unicode(c)))


def table_tex(header, aligns, data, index):
    """一张表 → xltabular。**单元格要单独走 cell_polish**：正文的映射与断行处理
    跑在表格替换之前，表格是后生成的，不补这一步就会把 ★▲ 与长路径原样留在单元格里（踩过）。"""
    htex = [cell_polish(c) for c in cells_to_tex(header)]
    flat, pos = [], []
    for r in data:
        for c in r:
            pos.append(len(flat))
            flat.append(c)
    ctex = [cell_polish(c) for c in cells_to_tex(flat)]
    rows = []
    for r in range(len(data)):
        rows.append([ctex[pos[r * len(header) + c]] for c in range(len(header))])

    ws = col_widths(header, data)
    pre = {'l': r'>{\raggedright\arraybackslash}',
           'c': r'>{\centering\arraybackslash}',
           'r': r'>{\raggedleft\arraybackslash}'}
    spec = ''.join(pre[a] + 'p{%.2fcm}' % w for a, w in zip(aligns, ws))

    # 表头：两处都排（首页 endfirsthead、续页 endhead）。以前续页只有「（续上表）」没有表头，
    # 翻到宽表的第二页就看不出列的含义了；表头用 `\rowcolor{white}` 从交替底纹里摘出来。
    # 但**不能直接把表头文本写两遍**——溯源比对.py 的 A 闸是「README ↔ tex 字符多重集」，
    # 写两遍就多一份，闸必然挂。故定义一次宏、用两次：
    # 宏名只含字母（\tabhdrA…），被 A 闸的「删 LaTeX 命令」一步整条抹掉，不留残字；
    # 而定义那一行里的表头文本照常被数一次，与 README 侧一一对应。
    mac = r'\tabhdr' + 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[index]

    L = [r'\newcommand{%s}{\rowcolor{white} %s \\}' % (mac, ' & '.join(htex)),
         r'\rowcolors{1}{white}{rowgray}',
         r'\begin{xltabular}{\textwidth}{@{}%s@{}}' % spec,
         r'\toprule',
         mac,
         r'\midrule',
         r'\endfirsthead',
         r'\multicolumn{%d}{r}{\footnotesize（续上表）} \\' % len(header),
         r'\midrule',
         mac,
         r'\midrule',
         r'\endhead',
         r'\bottomrule',
         r'\endlastfoot']
    for r in rows:
        L.append(' & '.join(r) + r' \\ \addlinespace[1pt]')
    L += [r'\end{xltabular}']
    # 4 列及以上的表降到 \small：少折两行，宽表不至于长得看不到头
    if len(header) >= 4:
        L = [r'\begingroup\small'] + L + [r'\endgroup']
    return '\n'.join(L)


# ---------------------------------------------------------------- 模板
def preamble(body, st):
    # 模板里用 @@…@@ 占位再 replace，不用 `%` 格式化——LaTeX 的注释里全是单个 `%`
    # （\providecommand{\tightlist}{%} 这种），`%` 运算符会把它们当转换符。
    head = r'''%% 溯源.tex —— 「题目溯源」报告（@@FEN@@ 份口径）
%% **本文件由 工具/README转tex.py 从 ../README.md 的「题目溯源」一节自动生成，不要手改**：
%% 改内容请改 README，改排版请改那个脚本，然后 `make trace` 重生成。
%% 编译：xelatex 溯源.tex（跑两遍，第二遍才有目录与交叉引用）
\documentclass[a4paper,11pt]{article}
\usepackage{common}
\usepackage{booktabs}
\usepackage{xltabular}          % longtable + 固定列宽（宽表见 README 的「题目溯源」）
\usepackage{colortbl}           % 宽表交替底纹（\rowcolors）：行高 3—4 行的表不串行
\usepackage{fancyhdr}
\usepackage{lastpage}           % 页脚「第 N 页 / 共 M 页」
\usepackage{hyperref}
\hypersetup{colorlinks=true,linkcolor=solblue,urlcolor=solblue,
            bookmarksopen=true,bookmarksopenlevel=1,pdfstartview=FitH,
            pdftitle={题目溯源},pdfsubject={上海高一上数学 · 跨卷同题与真题出处考证}}
\setlength{\parskip}{0.28em}
\setlength{\parindent}{0pt}
\renewcommand{\arraystretch}{1.12}
\definecolor{rowgray}{gray}{0.955}   % 交替底纹：比白纸略深一点，不抢正文

%% pandoc 的列表里会插 \tightlist，它只在 pandoc 自带模板里定义，独立编译要自己补，
%% 否则报 `Undefined control sequence \tightlist`（踩过）。定义与 pandoc 模板同文。
\providecommand{\tightlist}{%
  \setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}

\pagestyle{fancy}
\fancyhf{}
%% 右眉显示**当前节名**：翻到中间页时不至于不知道在哪一节（以前右眉是死的口径标签）。
\fancyhead[L]{\small\color{solblue} 题目溯源}
\fancyhead[R]{\small\nouppercase{\rightmark}}
\fancyfoot[L]{\small @@FEN@@ 份口径（@@DATE@@）}
\fancyfoot[C]{\small 第 \thepage 页 / 共 \pageref{LastPage} 页}
\renewcommand{\headrulewidth}{0.4pt}
\renewcommand{\footrulewidth}{0.4pt}

\begin{document}

\begin{titlepage}
\centering
\vspace*{2.6cm}
{\Huge\bfseries 题目溯源}\\[0.9em]
{\Large 上海高一上数学 · 跨卷同题与真题出处考证}\\[2.6em]
{\large @@FEN@@ 份试卷 @@TI@@ 道一级题干 $\times$ 参考库 @@KU@@ 道高考真题}\\[0.35em]
{\large 跨卷两两 @@DUI@@ 对 \quad|\quad 逐字同题 @@ZIZU@@ 组、同模板变体 @@BIANTI@@ 组}\\[3.2em]
\begin{minipage}{0.8\textwidth}\small\raggedright
本文件由 \texttt{工具/README转tex.py} 从 \texttt{README.md} 的「题目溯源」一节自动生成，
内容与该节逐字一致。判定口径、阈值与踩过的坑见末节「方法与局限」；
两档同题表的每一行都注明了该对「变在哪」，跨卷同题的成员已逐题回 \texttt{原图/} 核过。
\end{minipage}
\end{titlepage}

%% 目录本身也进书签（以前 9 个书签只有 9 节，目录不在里面）
\pdfbookmark[1]{\contentsname}{toc}
\tableofcontents
\newpage
'''
    tail = r'''

\end{document}
'''
    # 注意括号：`head + body + tail` 要整体再 replace——只给 tail 加 replace 的话，
    # 扉页那几个占位符会原样留在 tex 里（踩过一次）。
    return (head + body + tail) \
        .replace('@@FEN@@', st['份']).replace('@@TI@@', st['题']) \
        .replace('@@KU@@', st['库']).replace('@@DUI@@', st['对']) \
        .replace('@@ZIZU@@', st['逐字']).replace('@@BIANTI@@', st['变体']) \
        .replace('@@DATE@@', RUN_DATE)


# ---------------------------------------------------------------- 主流程
def main():
    lines = read_section()
    blocks = split_blocks(lines)
    tables = []

    md = []
    for kind, blk in blocks:
        if kind == 'table':
            tables.append(parse_table(blk))
            md += ['', PLACEHOLDER % (len(tables) - 1), '']
        else:
            md += blk

    body = pandoc('\n'.join(md), shift=-2)
    body = strip_labels(body)
    # 每个 \section 前另起一页：以前节与节连排，会出现「上节的表格续页 + 正文 + 下一节标题」
    # 挤在同一页（39 页那版第 18 页就是），翻到中间页看不出自己在哪一节。
    body = re.sub(r'(?m)^\\section\{', r'\\clearpage\n\\section{', body)
    body = break_paths(map_unicode(body))
    for i, (h, a, d) in enumerate(tables):
        body = body.replace(PLACEHOLDER % i, table_tex(h, a, d, i))

    tex = preamble(body, readme_stats())
    io.open(OUT, 'w', encoding='utf-8').write(tex)
    print('✅ 生成 %s' % os.path.relpath(OUT, PAPERS))
    print('   README 该节 %d 行 → %d 张表、正文 %d 行' % (len(lines), len(tables), len(body.split(chr(10)))))


if __name__ == '__main__':
    main()
