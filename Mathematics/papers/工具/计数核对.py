#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""计数核对.py —— 校验 README 里的「当前态计数」与源码／成品实测是否一致

用法
----
    python3 工具/计数核对.py
    make docs          # Makefile 里的入口（本脚本 + 说明）

为什么要单独一个脚本
--------------------
README 的「目录结构」「试卷清单」「答案版为什么这样排」「编译方式」「说明」几节里散着三十来处
**当前态**计数：份数、总页数、合订本页数、圈数字用了多少次、`\mbox` 与 `\keepwithprev` 各多少处、
标题前缀「学年度／年」各多少份……它们不是历史记录，而是对**仓库现状**的断言，每次加卷或改版式
都该同步——可这类数恰恰最容易漏改，因为它们藏在长段落里、也没有编译错误提醒你。

2026-09-16 并入高一22 那一轮就查出**三处已经写错很久**的数：`\mbox` 写 81（源码实为 77）、
标题前缀「学年度」写 12 份（名单自己就列了 13 个）、圈数字写 534 次/22 份（那一份贡献 27 次，
应为 561/23）。三处都是人工核出来的，靠的是「碰巧去看了」。这道闸把「碰巧」变成「每次必查」。

判据
----
每一条都是「README 里的一处断言 ↔ 一个可复算的实测值」。另有**两条不来自 README 的结构约束**，
直接约束源码形态（每枚 `\keepwithprev` 必须能归入「选项段」「小问」或「命题段」；每处 `\mbox{（\quad）`
所在的题目里必须有一枚守卫），期望值都写 0——它们是源码质量的回归守卫，不是文档同步。
两侧都从**当前工作区**现算：

  · **源码侧**：解析 `源码/高一*.tex`。**一律先剔掉整行 `%` 注释**——README 各处的口径都写明
    「按正文计、不含整行 `%` 注释」，两侧不同口径就会互相打架（`common.sty` 里那几行注释本身就
    含 `①②③`，不剔就会多算）。
  · **成品侧**：数 `试卷/`、`试卷紧凑/`、`答案/` 里的 PDF，页数取 `pdfinfo`。

四条刻意的设计
--------------
1. **断言找不到 = 失败**。README 一改措辞，正则就可能不再命中；此时脚本必须报「断言没找到」
   而不是静默跳过——否则这道闸会因为 README 被改写而悄悄失效，比没有还危险。
2. **`\keepwithprev` 要分类**。它有三个用途：插在**选择题选项段之前**（配对题干末尾的
   `\mbox{（\quad）`）、插在**解答题各小问之前**（高一19／20／21 那批起加的）、以及插在
   题干后紧跟的 **①②③④ 编号命题列之前**（高一26 第 4 题、高一28 第 15 题起有这一型）。
   分类只按形态判——看它后面第一个非注释行是不是以 `A.`／`（1）`／`①` 开头，
   **不猜排版意图**（与 `切页审计.py` 同一原则）。出现两不像的实例就报失败，逼着新卷遵守
   同一条写法约定。
3. **不核历史数字**。「当时 19 份」「12 份那一轮跑的」「此前记 385 次」这类是留档，本就该与现状
   不同，硬核会逼人篡改历史。需要人工判读的（原卷笔误、存疑条目、考据结论）同样不在此脚本范围。
4. **脚本里不写死任何份数**。「现 N 份为 a / b / c 页」那句里的 N 也一起核——早年这三条正则把
   份数写死成 24，加第 25 份时它们会报「找不到断言」，等于把一条本可自动跟上的检查变成手工维护项。
   同理，README 点名「**高一a** 是唯一没有 ② 的一份」，就**连名单一起断言**而不是只核份数：
   只核份数的话，「少了两份、总份数恰好没变」这类错会漏过去。

改这个脚本时的三条约定
----------------------
  · **每份 `.tex` 只读一次**：`check_source` 开头 `raws = [(f, load(f)) for f in srcs()]`，
    之后 body／header／标题／小问／配对全部从这份文本上算。四个函数各读一遍盘的老写法
    实测要读 130 次（每份 5～6 次），是白花 I/O，也容易让「读到的内容不一致」这类 bug 混进来。
  · **`body()` 收文本、不收路径**，因为它要按行剔注释，作用对象是原文；而 `classify_keep()`
    恰恰反过来——它必须看**带注释的原文行**（按行跳过注释、再找下一非注释行），不能改走 `body()`。
  · **改完把五条反向测试重跑一遍**（各改一处、跑完还原）：① 把 README 某个数改错 →
    应报「N 项不一致」；② 摘掉源码里一枚 `\keepwithprev` → 应报计数 + 配对、点名到卷；
    ③ 让某卷丢掉头部 ② → 应报份数 + 缺 ② 名单；④ 去掉某卷标题的「年／学年度」→ 应报标题异常；
    ⑤ 改写 README 措辞 → 应报「找不到这处断言」并把失配正则打出来。五条都要**报错并点名**。

退出码：全部一致 0，有任一不一致 1（经 `make docs` 调用时为 2，那是 make 的惯例，判成败只看非 0）。
"""
import glob
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAPERS = os.path.normpath(os.path.join(HERE, '..'))
README = os.path.join(PAPERS, 'README.md')
# 根 README（papers/ 的上一层）里也复述了一遍「已入库的 N 套卷子」——两份文档各写一遍的数，
# 只改一份是常见漏改，故一并核。
ROOT_README = os.path.normpath(os.path.join(PAPERS, '..', 'README.md'))

CIRCLED = re.compile(r'[\u2460-\u2473]')          # ①–⑳（README 说的「圈数字」）
MBOX = re.compile(r'\\mbox\{（\\quad）')           # 选择题干的答题括注（含带句点与不带句点两种）
KEEP = r'\keepwithprev'
# 「与原卷…排版差异」小节（高一b 作「与原卷的**两处**排版差异」，故中间放开）
DIFFSEC = re.compile(r'与原卷的.{0,6}排版差异')
TITLE = re.compile(r'\\examtitlest(?:\[\d\])?\{(.*?)\}')
SUBTITLE = re.compile(r'\\examtitlest(?:\[\d\])?\{.*?\}\{(.*?)\}')
ANS_FULL = re.compile(r'\\ans\{[^}]*（1）')

# 对号副本数：高一16≡高一b、高一18≡高一c，一套副本只算一套（README「试卷清单」的口径）
COPIES = 2

results = []          # (名称, README 值, 实测值, 说明)


# ----------------------------------------------------------------- 工具
def readme_text():
    return io.open(README, encoding='utf-8').read()


def trace_section_lines(md):
    """README「## 题目溯源」一节的正文行数（不含标题行本身）。

    README 的「编译方式」一节写着「`## 题目溯源` 一节抽出 N 行」，N 就是本函数的值；
    这个数原先没有任何闸，2026-09-26 发现它已从 709 静默漂到 797——改 README 该节时
    没人会想起还有这句话。口径与 工具/README转tex.py 的 read_section() 完全一致：
    标题行之后、下一个 `## ` 之前。
    """
    lines = md.split('\n')
    try:
        i = lines.index('## 题目溯源')
    except ValueError:
        raise AssertionError('README 里找不到 `## 题目溯源`——README转tex.py 的切入点，先补回这一节')
    j = i + 1
    while j < len(lines) and not lines[j].startswith('## '):
        j += 1
    return j - (i + 1)


def claim(md, pattern, name, conv=int):
    """从 README 里抠出一处断言；找不到就抛错（见模块头「设计 1」）。"""
    m = re.search(pattern, md)
    if not m:
        raise AssertionError(f'README 里找不到这处断言：{name}\n  正则：{pattern}')
    v = m.group(1)
    try:
        return conv(v)
    except ValueError:
        raise AssertionError(f'断言 {name} 的值不是数字：{v!r}')


def srcs():
    return sorted(glob.glob(os.path.join(PAPERS, '源码', '高一*.tex')))


def load(path):
    return io.open(path, encoding='utf-8').read()


def body(raw):
    """源码正文：剔掉整行 % 注释（README 各处「按正文计」的口径）。

    入参是**读好的源码文本**而不是路径——一个文件里要用到正文、文件头、标题、小问四处，
    传文本才能只读一次（早期版本四个函数各读一遍盘，同一文件被读 5～6 次）。
    """
    return '\n'.join(l for l in raw.split('\n') if not l.lstrip().startswith('%'))


def header(raw):
    """文件头：第一个 \\documentclass 之前的注释块。"""
    return raw.split(r'\documentclass')[0]


def next_code_line(lines, i):
    for j in range(i + 1, min(i + 8, len(lines))):
        l = lines[j].strip()
        if not l or l.startswith('%'):
            continue
        return l
    return ''


def classify_keep(raws):
    """把每枚 \\keepwithprev 按形态分成「选项段」与「小问」。返回 (计数, 无法分类的清单)。

    要的是**带注释的原文行**（它按行跳过注释、再找下一非注释行），故这里不能用 body()。
    """
    cnt = {'选项段': 0, '小问': 0, '命题段': 0}
    odd = []
    for f, raw in raws:
        lines = raw.split('\n')
        for i, l in enumerate(lines):
            if l.strip().startswith('%') or KEEP not in l:
                continue
            nxt = next_code_line(lines, i)
            if re.match(r'^A[.．]', nxt):
                cnt['选项段'] += 1
            elif re.match(r'^[①-⑳]', nxt):
                # 题干后紧跟 ①②③④ 编号命题列（高一26 第 4 题、高一28 第 15 题这一型）
                cnt['命题段'] += 1
            elif (re.match(r'^（\d+）', nxt) or nxt.startswith(r'\begin{enumerate}')
                  or nxt.startswith(r'\item')):
                cnt['小问'] += 1
            else:
                odd.append((os.path.basename(f).split('_')[0], nxt[:40]))
    return cnt, odd


def pdf_pages(path):
    out = subprocess.run(['pdfinfo', path], capture_output=True, text=True).stdout
    m = re.search(r'^Pages:\s+(\d+)', out, re.M)
    if not m:
        raise AssertionError(f'pdfinfo 读不出页数：{path}')
    return int(m.group(1))


def pdfs(pattern):
    return sorted(glob.glob(os.path.join(PAPERS, pattern)))


def add(name, expected, actual, note=''):
    results.append((name, expected, actual, note))


# ----------------------------------------------------------------- 源码侧
def check_source(md):
    raws = [(f, load(f)) for f in srcs()]      # 每个文件只读一次，后文都从这份文本上算
    n_tex = len(raws)
    n_mbox = n_circ = n_circ_files = n_xue = n_nian = 0
    n_sub_std = n_diff = 0
    n_ans_full = 0
    no_diff = []

    for f, raw in raws:
        b = body(raw)
        c = len(CIRCLED.findall(b))
        n_circ += c
        n_circ_files += (c > 0)
        n_mbox += len(MBOX.findall(b))
        if ANS_FULL.search(b):
            n_ans_full += 1
        t = TITLE.search(raw)
        if not t:
            raise AssertionError(f'读不出 \\examtitlest 标题：{f}')
        if '学年度' in t.group(1):
            n_xue += 1
        elif '年' in t.group(1):
            n_nian += 1
        else:
            raise AssertionError(f'标题既无「学年度」也无「年」：{f}')
        st = SUBTITLE.search(raw)
        n_sub_std += (st and st.group(1) == '集合与常用逻辑用语')
        if DIFFSEC.search(header(raw)):
            n_diff += 1
        else:
            no_diff.append(os.path.basename(f).split('_')[0])

    n_keep, odd = classify_keep(raws)

    add('套数', claim(md, r'全部 \*\*(\d+) 套\*\*', '套数'), n_tex - COPIES,
        f'{n_tex} 个 .tex − {COPIES} 个对号副本')
    if os.path.exists(ROOT_README):
        root = io.open(ROOT_README, encoding='utf-8').read()
        add('套数（根 README 复述处）', claim(root, r'已入库的 (\d+) 套卷子', '根 README 套数'),
            n_tex - COPIES, '两份文档各写一遍，只改一份是常见漏改')
    add('源码 .tex 份数', claim(md, r'LaTeX 源码（(\d+) 份试卷', '源码份数'), n_tex)
    add('圈数字次数', claim(md, r'\*\*(\d+) 次\*\*、遍布 \*\*', '圈数字次数'), n_circ)
    add('圈数字份数', claim(md, r'次\*\*、遍布 \*\*(\d+) 份\*\*', '圈数字份数'), n_circ_files)
    add('\\mbox 处数', claim(md, r'包成 `\\mbox`（全库 \*\*(\d+) 处', 'mbox 处数'), n_mbox)
    add('\\keepwithprev 总处数', claim(md, r'`\\keepwithprev` 共 \*\*(\d+) 处', 'keep 总'),
        n_keep['选项段'] + n_keep['小问'] + n_keep['命题段'])
    add('\\keepwithprev 选项段', claim(md, r'（(\d+) 处在选项段之前', 'keep 选项'),
        n_keep['选项段'])
    add('\\keepwithprev 小问', claim(md, r'、(\d+) 处在小问之前', 'keep 小问'),
        n_keep['小问'])
    add('\\keepwithprev 命题段', claim(md, r'、(\d+) 处在命题段之前', 'keep 命题'),
        n_keep['命题段'])
    add('标题前缀「学年度」份数', claim(md, r'作「学年度」的 (\d+) 份', '学年度'), n_xue)
    add('标题前缀「年」份数', claim(md, r'作「年」的 (\d+) 份', '年'), n_nian)
    add('副标题（惯例）份数', claim(md, r'标题的 (\d+) 份都是本稿补出', '副标题'), n_sub_std)
    add('源码头带 ② 的份数', claim(md, r'其中 \*\*(\d+) 份\*\*另有 ②', '带②份数'), n_diff)
    # README 点名「高一a 是唯一没有 ② 的一份」——这是可核的，故连名单一起断言
    # （只核份数的话，「少了两份、但总份数恰好没变」这类错就漏了）。
    add('缺 ② 的卷（README 点名高一a）', '高一a', '、'.join(sorted(no_diff)) or '（无）')
    add('\\ans 含全角（1）份数', claim(md, r'全稿 \*\*(\d+) 份\*\*含多小问答案', 'ans全角'),
        n_ans_full)

    # 形态约定：每枚 \keepwithprev 都必须能归入「选项段」「小问」或「命题段」
    add('\\keepwithprev 可归类', 0, len(odd),
        '；'.join(f'{a} 后接「{b}」' for a, b in odd) if odd else '全部可判')

    # 配对：每处 `\mbox{（\quad）` 所在的 \item 内必须有一枚 \keepwithprev
    unpaired = []
    for f, raw in raws:
        for item in body(raw).split(r'\item')[1:]:
            if MBOX.search(item) and KEEP not in item:
                unpaired.append(os.path.basename(f).split('_')[0])
    add('选择题干与 \\keepwithprev 配对', 0, len(unpaired),
        '缺守卫：' + '、'.join(sorted(set(unpaired))) if unpaired else '全部配对')


# ----------------------------------------------------------------- 成品侧
def check_output(md):
    t = pdfs('试卷/*_试卷.pdf')
    c = pdfs('试卷紧凑/高一*_试卷.pdf')
    a = pdfs('答案/*_答案.pdf')
    add('试卷版份数', claim(md, r'不含任何答案\*\*（(\d+) 份）', '试卷份数'), len(t))
    add('紧凑版份数', claim(md, r'只去掉解答题作答题区（(\d+) 份）', '紧凑份数'), len(c))
    add('答案版份数', claim(md, r'逐题【解析】（(\d+) 份', '答案份数'), len(a))
    add('三版合计 PDF 数', claim(md, r'合计 \*\*(\d+) 份 PDF\*\*', 'PDF 合计'), len(t) + len(c) + len(a))
    add('原图张数', claim(md, r'用于溯源（(\d+) 张', '原图张数'),
        len(glob.glob(os.path.join(PAPERS, '原图', '*', '*'))))
    add('溯源报告页数', claim(md, r'`题目溯源\.pdf`，(\d+) 页', '溯源页数'),
        pdf_pages(os.path.join(PAPERS, '溯源', '题目溯源.pdf')))
    add('溯源节抽出行数', claim(md, r'一节抽出 (\d+) 行', '溯源节行数'), trace_section_lines(md))
    bundle = os.path.join(PAPERS, '试卷紧凑', '合并打印版.pdf')
    add('合订本份数', claim(md, r'——(\d+) 份合订', '合订份数'), len(c) - COPIES)
    add('合订本页数', claim(md, r'份合订、(\d+) 页', '合订页数'), pdf_pages(bundle))

    tp = sum(pdf_pages(f) for f in t)
    cp = sum(pdf_pages(f) for f in c)
    ap = sum(pdf_pages(f) for f in a)
    # 「N 份」不写死：加卷后这句里的份数会同时变旧，所以份数与三个页数一起核
    #（写死 24 的话，加第 25 份时这里会报「找不到断言」，把一条本可自动跟上的检查变成手工维护项）。
    n = len(t)
    add('「现 N 份」那句里的份数', claim(md, r'现 (\d+) 份为 \d+ / \d+ / \d+ 页', '现 N 份'), n)
    add('三版总页数（试卷）', claim(md, r'现 \d+ 份为 (\d+) /', '试卷总页'), tp)
    add('三版总页数（紧凑）', claim(md, r'现 \d+ 份为 \d+ / (\d+) /', '紧凑总页'), cp)
    add('三版总页数（答案）', claim(md, r'现 \d+ 份为 \d+ / \d+ / (\d+) 页', '答案总页'), ap)
    add('紧凑版合计页数', claim(md, r'合计 \*\*\d+ → (\d+) 页\*\*', '紧凑合计'), cp)
    # 同一组页数在「说明」一节还复述了一遍（措辞不同，无「现」字），一并核
    add('三版总页数（复述处）', claim(md, r'未改版式，(\d+) 份为 \d+ / \d+ / \d+ 页', '复述份数'), n)


def main():
    md = readme_text()
    try:
        check_source(md)
        check_output(md)
    except AssertionError as e:
        print(f'❌ {e}')
        print('   处理：改了 README 措辞就要同步改本脚本里的正则（见文件头「设计 1」）。')
        return 1

    w = max(len(n) for n, *_ in results)
    bad = 0
    for name, exp, act, note in results:
        ok = exp == act
        bad += (not ok)
        print(f"  {'✔' if ok else '✘'} {name:<{w}}  README {exp} / 实测 {act}"
              + (f'　（{note}）' if note else ''))
    print(f'  {len(results)} 项：' + ('全部一致' if not bad else f'❌ {bad} 项不一致'))
    if bad:
        print('   处理：按「实测」列改 README（本脚本是现算的，实测列即当前仓库的真实值）。')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
