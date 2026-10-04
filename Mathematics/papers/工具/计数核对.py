#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""计数核对.py —— 校验 README 里的“当前态计数”与源码／成品实测是否一致

用法
----
    python3 工具/计数核对.py
    make docs          # Makefile 里的入口（本脚本 + 说明）

为什么要单独一个脚本
--------------------
README 的“目录结构”“试卷清单”“答案版为什么这样排”“编译方式”“说明”几节里散着三十来处
**当前态**计数：份数、总页数、合订本页数、圈数字用了多少次、`\mbox` 与 `\keepwithprev` 各多少处、
标题前缀“学年度／年”各多少份……它们不是历史记录，而是对**仓库现状**的断言，每次加卷或改版式
都该同步——可这类数恰恰最容易漏改，因为它们藏在长段落里、也没有编译错误提醒你。

2026-09-16 并入高一22 那一轮就查出**三处已经写错很久**的数：`\mbox` 写 81（源码实为 77）、
标题前缀“学年度”写 12 份（名单自己就列了 13 个）、圈数字写 534 次/22 份（那一份贡献 27 次，
应为 561/23）。三处都是人工核出来的，靠的是“碰巧去看了”。这道闸把“碰巧”变成“每次必查”。

判据
----
每一条都是“README 里的一处断言 ↔ 一个可复算的实测值”。另有**三条不来自 README 的结构约束**，
直接约束源码形态（每枚 `\keepwithprev` 必须能归入“选项段”“小问”或“命题段”；每处 `\mbox{（\quad）`
所在的题目里必须有一枚守卫），期望值都写 0——它们是源码质量的回归守卫，不是文档同步。
两侧都从**当前工作区**现算：

  · **源码侧**：解析 `源码/高一*.tex`。**一律先剔掉整行 `%` 注释**——README 各处的口径都写明
    “按正文计、不含整行 `%` 注释”，两侧不同口径就会互相打架（`common.sty` 里那几行注释本身就
    含 `①②③`，不剔就会多算）。
  · **成品侧**：数 `试卷/`、`试卷紧凑/`、`答案/` 里的 PDF，页数取 `pdfinfo`。

四条刻意的设计
--------------
1. **断言找不到 = 失败**。README 一改措辞，正则就可能不再命中；此时脚本必须报“断言没找到”
   而不是静默跳过——否则这道闸会因为 README 被改写而悄悄失效，比没有还危险。
2. **`\keepwithprev` 要分类**。它有三个用途：插在**选择题选项段之前**（配对题干末尾的
   `\mbox{（\quad）`）、插在**解答题各小问之前**（高一19／20／21 那批起加的）、以及插在
   题干后紧跟的 **①②③④ 编号命题列之前**（高一26 第 4 题、高一28 第 15 题起有这一型）。
   分类只按形态判——看它后面第一个非注释行是不是以 `A.`／`（1）`／`①` 开头，
   **不猜排版意图**（与 `切页审计.py` 同一原则）。出现两不像的实例就报失败，逼着新卷遵守
   同一条写法约定。
3. **不核历史数字**。“当时 19 份”“12 份那一轮跑的”“此前记 385 次”这类是留档，本就该与现状
   不同，硬核会逼人篡改历史。需要人工判读的（原卷笔误、存疑条目、考据结论）同样不在此脚本范围。
4. **脚本里不写死任何份数**。“现 N 份为 a / b / c 页”那句里的 N 也一起核——早年这三条正则把
   份数写死成 24，加第 25 份时它们会报“找不到断言”，等于把一条本可自动跟上的检查变成手工维护项。
   同理，README 点名“**高一a** 是唯一没有 ② 的一份”，就**连名单一起断言**而不是只核份数：
   只核份数的话，“少了两份、总份数恰好没变”这类错会漏过去。

改这个脚本时的三条约定
----------------------
  · **每份 `.tex` 只读一次**：`check_source` 开头 `raws = [(f, load(f)) for f in srcs()]`，
    之后 body／header／标题／小问／配对全部从这份文本上算。四个函数各读一遍盘的老写法
    实测要读 130 次（每份 5～6 次），是白花 I/O，也容易让“读到的内容不一致”这类 bug 混进来。
  · **`body()` 收文本、不收路径**，因为它要按行剔注释，作用对象是原文；而 `classify_keep()`
    恰恰反过来——它必须看**带注释的原文行**（按行跳过注释、再找下一非注释行），不能改走 `body()`。
  · **改完把五条反向测试重跑一遍**（各改一处、跑完还原）：① 把 README 某个数改错 →
    应报“N 项不一致”；② 摘掉源码里一枚 `\keepwithprev` → 应报计数 + 配对、点名到卷；
    ③ 让某卷丢掉头部 ② → 应报份数 + 缺 ② 名单；④ 去掉某卷标题的“年／学年度”→ 应报标题异常；
    ⑤ 改写 README 措辞 → 应报“找不到这处断言”并把失配正则打出来。五条都要**报错并点名**。

退出码：全部一致 0，有任一不一致 1（经 `make docs` 调用时为 2，那是 make 的惯例，判成败只看非 0）。
"""
import collections
import datetime
import glob
import importlib
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAPERS = os.path.normpath(os.path.join(HERE, '..'))
README = os.path.join(PAPERS, 'README.md')
# 根 README（papers/ 的上一层）里也复述了一遍“已入库的 N 套卷子”——两份文档各写一遍的数，
# 只改一份是常见漏改，故一并核。
ROOT_README = os.path.normpath(os.path.join(PAPERS, '..', 'README.md'))

CIRCLED = re.compile(r'[\u2460-\u2473]')          # ①–⑳（README 说的“圈数字”）
MBOX = re.compile(r'\\mbox\{（\\quad）')           # 选择题干的答题括注（含带句点与不带句点两种）
KEEP = r'\keepwithprev'
# “与原卷…排版差异”小节（高一b 作“与原卷的**两处**排版差异”，故中间放开）
DIFFSEC = re.compile(r'与原卷的.{0,6}排版差异')
TITLE = re.compile(r'\\examtitlest(?:\[\d\])?\{(.*?)\}')
SUBTITLE = re.compile(r'\\examtitlest(?:\[\d\])?\{.*?\}\{(.*?)\}')
ANS_FULL = re.compile(r'\\ans\{[^}]*（1）')

# 副标题口径（2026-09-26 起）：原卷自印的两份照录，其余**按本卷实际内容**补出、且只许用
# “知识模块”一节里的模块名、以“、”连接（见 README“说明”的“标题行”节）。
SELFSUB = {'高一14': '集合与逻辑单元练习', '高一24': '集合与逻辑、等式的性质'}
MODULES = ['集合与常用逻辑用语', '函数与导数', '三角函数', '数列',
           '立体几何', '解析几何', '概率统计', '不等式', '向量']

# 对号副本数：高一16≡高一b、高一18≡高一c，一套副本只算一套（README“试卷清单”的口径）
COPIES = 2
# 对号副本的**名单**（与 COPIES 互为印证；加卷时若多了一对副本，两处都要改）。
COPY_NAMES = ('高一16', '高一18')

results = []          # (名称, README 值, 实测值, 说明)


# ----------------------------------------------------------------- 工具
def readme_text():
    return io.open(README, encoding='utf-8').read()


def trace_section_lines(md):
    """README“## 题目溯源”一节的正文行数（不含标题行本身）。

    README 的“编译方式”一节写着“`## 题目溯源` 一节抽出 N 行”，N 就是本函数的值；
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


def missing_heduimian(md):
    """每个“### …专记”小节都必须含一段“**核对面**”。返回缺失的小节标题清单。

    “核对面”＝该卷回原图核对的那一段（几轮、谁做的、查出什么）。2026-09-26 立的口径：
    13 份专记份份都要有。这条以前没有闸，结果 6 份是空的、分四轮才补齐，故单列一条结构约束。
    """
    lines = md.split('\n')
    heads = [i for i, l in enumerate(lines) if l.startswith('### ') and '专记' in l]
    miss = []
    for n, i in enumerate(heads):
        j = heads[n + 1] if n + 1 < len(heads) else len(lines)
        if '**核对面**' not in '\n'.join(lines[i:j]):
            miss.append(lines[i][4:].strip())
    return miss


def claim(md, pattern, name, conv=int):
    """从 README 里抠出一处断言；找不到就抛错（见模块头“设计 1”）。"""
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
    """源码正文：剔掉整行 % 注释（README 各处“按正文计”的口径）。

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
    """把每枚 \\keepwithprev 按形态分成“选项段”与“小问”。返回 (计数, 无法分类的清单)。

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


# ----------------------------------------------------------------- 真题出处账目
# “真题出处”那张表是这一族数的**唯一真值源**：道数／条数／题位都从它逐行数出来。这三个数
# 在 README 里各写三遍（“核对摘要”那一行、本节标题、本节正文），此前**一处闸都没有**，
# 2026-09-28 才发现它们错了一整轮——上一轮（并入高一37—高一40）只加了表行、没改本节标题
# （标题停在“36 道／41 条／45 个题位”），而摘要那句“三个数与表逐行数出来的完全相同”
# 当时已是假的（摘要写 48 个题位、表逐行数是 50）。故这里按表全量复算，再与三处声明互校。
ZHENTI_HEAD = '| 本库题目 | 出处 | 关系 |'
# 表首格里的“本库题位”形态：高一06 第 9 题 / 高一15 附加 17 题 / 高一a 附加题第 2 题
ZHENTI_SLOT = re.compile(r'(高一[0-9a-c]+)\s*(附加)?\s*(?:题)?\s*(?:第)?\s*(\d+)\s*题')


def zhenti_key(s):
    """把出处栏归一到“哪一道真题”。

    规则：去标记／去“年”／去空格，末尾**光秃秃的题型词**（选择／填空／解答）去掉。
    这样“2015 上海卷（春）”“2015 年上海卷（春）选择”归一成同一道，而
    “2009 北京卷（文）填空 6‘孤立元’”与“2009 北京卷（文）选择 8”因为带着题号而分开——
    后者正是**同一份卷里的两道不同真题**，不能并。
    """
    s = re.sub(r'[\*★▲◆◇●]', '', s)
    s = s.replace('年', '').replace(' ', '')
    return re.sub(r'(选择|填空|解答)$', '', s)


def zhenti_rows(md):
    lines = md.split('\n')
    if lines.count(ZHENTI_HEAD) != 1:
        raise AssertionError(f'README 里 `{ZHENTI_HEAD}` 应恰好出现一次，实为 {lines.count(ZHENTI_HEAD)} 次')
    i = lines.index(ZHENTI_HEAD) + 2          # 跳过 `|---|` 分隔行
    rows = []
    while i < len(lines) and lines[i].startswith('|'):
        rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
        i += 1
    if len(rows) < 10:
        raise AssertionError(f'“真题出处”表只读到 {len(rows)} 行，像是被改坏了')
    return rows


def zhenti_slots(cells):
    """一组单元格里点到的本库题位集合（卷号, “附加”+题号 或 题号）。"""
    out = set()
    for c in cells:
        for m in ZHENTI_SLOT.finditer(c):
            out.add((m.group(1), ('附加' if m.group(2) else '') + m.group(3)))
    return out


def zhenti_facts(md):
    """按“真题出处”表逐行数出：

        (表行数, 题位数, 原题照录数, 改编数, 借定义数, 真题道数, {份数: 该份数的真题道数})

    “份数”= 该真题被几个**不同的卷**用到（按表首格点到的卷号去重）——这是 2026-09-28 补的：
    此前“几道被三份／两份用到”是手写的，没有任何东西核得了；现在与题位、道数互推。
    归并用 zhenti_key()（见那里的说明：同一份卷的两道真题靠题号区分开）。
    """
    rows = zhenti_rows(md)
    n_row = len(rows)
    slots = [zhenti_slots([r[0]]) for r in rows]
    n_slot = sum(len(s) for s in slots)
    rel = [re.sub(r'[\*★▲◆◇●]', '', r[2]) for r in rows]
    n_dd = sum(1 for r in rel if r.startswith('原题照录'))
    n_bj = sum(1 for r in rel if r.startswith('借'))
    groups = {}
    for r, s in zip(rows, slots):
        groups.setdefault(zhenti_key(r[1]), set()).update(x[0] for x in s)
    dist = {}
    for k, vols in groups.items():
        dist[len(vols)] = dist.get(len(vols), 0) + 1
    return n_row, n_slot, n_dd, n_row - n_dd - n_bj, n_bj, len(groups), dist


FENSHU = {4: '四份', 3: '三份', 2: '两份', 1: '单独'}


def _zhenti_g(pat, s, name, n=1, flags=0):
    m = re.search(pat, s, flags)
    if not m:
        raise AssertionError(f'README 里找不到这处断言：{name}\n  正则：{pat}')
    g = m.groups()
    return int(g[0]) if n == 1 else tuple(int(x) for x in g[:n])


# 逐字同题表里**已知“不是同一道题”**的成员（会与本组的其他成员一起被机判拉进同组，
# 但 README 已写明它们不是同题）——交叉闸要放行这些，否则会误报。
#   高一19 第 7 题：与 高一08 第 15 题 题干一字不差，但**图形不同**（$P$ 内含于 $S$、
#   答案也不同），2026-09-15 回原图核过后从两档剔除，见 README“回原图逐题核对”。
TONGPAI_NOT_SAME = {('高一19', '7')}
TONGTI_HEAD = '| 题目 | 份数 | 分布 |'
_TONGTI_SLOT = re.compile(r'(?:高一)?([0-9a-c]{1,2})\s*附加\s*题?\s*第?\s*(\d+)\s*题'
                          r'|(?:高一)?([0-9a-c]{1,2})\s*附加题(?![\d第])'
                          r'|(?:高一)?([0-9a-c]{1,2})\s*第\s*(\d+)\s*题')


def _tongti_members(cell):
    s = re.sub(r'[\*★▲◆◇●]', '', cell)
    out = set()
    for m in _TONGTI_SLOT.finditer(s):
        if m.group(1):
            n = m.group(1); out.add((('高一' + n.zfill(2)) if n.isdigit() else '高一' + n, '附加' + m.group(2)))
        elif m.group(3):
            n = m.group(3); out.add((('高一' + n.zfill(2)) if n.isdigit() else '高一' + n, '附加'))
        else:
            n = m.group(4); out.add((('高一' + n.zfill(2)) if n.isdigit() else '高一' + n, m.group(5)))
    return out


def check_zhenti(md):
    lines = md.split('\n')
    n_row, n_slot, n_dd, n_gb, n_bj, n_dao, dist = zhenti_facts(md)
    sm = next(l for l in lines if l.startswith('| 定到具体高考试卷 |'))      # 摘要那一行
    ti = next(l for l in lines if l.startswith('### 能考据到的高考出处：'))    # 本节标题
    zb = '\n'.join(lines[lines.index(ti) + 1:lines.index(ZHENTI_HEAD)])     # 本节正文

    sm_dd = _zhenti_g(r'\*\*(\d+) 道真题\*\*', sm, '摘要：真题道数')
    sm_tj, sm_dd2, sm_gb2, sm_bj2 = _zhenti_g(
        r'\*\*(\d+) 条对应\*\*：原题照录 (\d+)、改编 (\d+)、借定义／借集合另出题 (\d+)',
        sm, '摘要：条数／按关系分', n=4)
    sm_tw = _zhenti_g(r'对应本库 \*\*(\d+) 个题位\*\*', sm, '摘要：题位数')
    sm_4 = _zhenti_g(r'\*\*(\d+) 道\*\*真题被\*\*四份\*\*', sm, '摘要：被四份用到的道数')
    sm_3 = _zhenti_g(r'\*\*(\d+) 道\*\*真题被\*\*三份\*\*', sm, '摘要：被三份用到的道数')
    sm_2 = _zhenti_g(r'\*\*(\d+) 道\*\*各被两份用到', sm, '摘要：被两份用到的道数')

    ti_dd, ti_tj, ti_tw = _zhenti_g(r'出处：(\d+) 道真题（(\d+) 条对应／(\d+) 个题位）',
                                    ti, '节标题：道数/条数/题位', n=3)

    zb_dd = _zhenti_g(r'\*\*真题有 (\d+) 道\*\*', zb, '节正文：真题道数')
    zb_tw, zb_tj = _zhenti_g(r'对应本库 \*\*(\d+) 个题位\*\*、\*\*(\d+) 条对应关系\*\*',
                             zb, '节正文：题位数/条数', n=2)
    zb_dd2, zb_gb2, zb_bj2, zb_tj2 = _zhenti_g(
        r'原题照录 \*\*(\d+)\*\* 条、改编 \*\*(\d+)\*\* 条、借定义／借集合另出题 \*\*(\d+)\*\* 条 ＝ (\d+) 条',
        zb, '节正文：按关系分', n=4)
    a4, a3, b2, c1, tw_sum = _zhenti_g(
        r'(\d+) × 4 ＋ (\d+) × 3 ＋ (\d+) × 2 ＋ (\d+) × 1 ＝ \*\*(\d+) 个题位\*\*',
        zb, '节正文：题位算式', n=5)
    dd_sum = a4 + a3 + b2 + c1
    zb_4 = _zhenti_g(r'\*\*(\d+) 道\*\*真题被\*\*四份\*\*试卷用到', zb, '节正文：被四份用到')
    zb_3 = _zhenti_g(r'\*\*(\d+) 道\*\*真题被\*\*三份\*\*试卷用到', zb, '节正文：被三份用到')
    m2 = re.search(r'\*\*(\d+) 道\*\*各被两份用到（(.*?)）\s*\n\s*→', zb, re.S)
    if not m2:
        raise AssertionError('README 里找不到这处断言：节正文“被两份用到”及其名单')
    zb_2, names2 = int(m2.group(1)), m2.group(2)
    m4 = re.search(r'\*\*\d+ 道\*\*真题被\*\*四份\*\*试卷用到（(.*?)），\s*\n', zb, re.S)
    if not m4:
        raise AssertionError('README 里找不到这处断言：节正文“被四份用到”的名单')
    m3 = re.search(r'\*\*\d+ 道\*\*真题被\*\*三份\*\*试卷用到（(.*?)），\s*\n', zb, re.S)
    if not m3:
        raise AssertionError('README 里找不到这处断言：节正文“被三份用到”的名单')
    dd_ar, extra_dec, tj_ar = _zhenti_g(
        r'故 (\d+) ＋ (\d+) ＝ \*\*(\d+) 条对应\*\*', zb, '节正文：条数算式', n=3)
    m = re.search(r'第二种／第三种改法(.*?)→', zb, re.S)
    if not m:
        raise AssertionError('README 里找不到这处断言：节正文“第二种／第三种改法”的括号')
    extra_calc = m.group(1).count('两种') + 2 * m.group(1).count('三种')

    d4, d3, d2, d1 = dist.get(4, 0), dist.get(3, 0), dist.get(2, 0), dist.get(1, 0)
    add('真题出处：条数（三处 ↔ 表行数）', (sm_tj, ti_tj, zb_tj), (n_row,) * 3,
        f'表 {n_row} 行；三处为摘要／节标题／节正文')
    add('真题出处：题位数（三处 ＋ 算式 ↔ 表）', (sm_tw, ti_tw, zb_tw, tw_sum), (n_slot,) * 4,
        '表首格逐个数出的本库题位')
    add('真题出处：真题道数（三处 ＋ 算式 ↔ 表归并）',
        (sm_dd, ti_dd, zb_dd, dd_sum), (n_dao,) * 4,
        f'按出处栏归并（同卷两道真题靠题号区分）；算式 {a3} ＋ {b2} ＋ {c1} ＝ {dd_sum}')
    # 题位数与“份数分布”互为印证：Σ(份数 × 该份数的真题道数) 必须等于题位数
    add('真题出处：题位 ＝ Σ(份数 × 道数)（表内自洽）', n_slot, 4 * d4 + 3 * d3 + 2 * d2 + d1)
    add('真题出处：按关系分（摘要／节正文 ↔ 表）',
        ((sm_dd2, sm_gb2, sm_bj2), (zb_dd2, zb_gb2, zb_bj2)),
        ((n_dd, n_gb, n_bj),) * 2, '原题照录／改编／借定义')
    add('真题出处：按关系分之和 ＝ 条数', sm_dd2 + sm_gb2 + sm_bj2, n_row)
    add('真题出处：真题侧份数分布（摘要／节正文／算式 ↔ 表归并）',
        (sm_4, sm_3, sm_2, zb_4, zb_3, zb_2, a4, a3, b2, c1),
        (d4, d3, d2, d4, d3, d2, d4, d3, d2, d1),
        f'表归并得 {d4} 道被四份、{d3} 道被三份、{d2} 道被两份、{d1} 道单独')
    add('真题出处：被四份用到的名单条数', zb_4, m4.group(1).count('；') + 1)
    add('真题出处：被三份用到的名单条数', zb_3, m3.group(1).count('；') + 1)
    add('真题出处：被两份用到的名单条数', zb_2, names2.count('、') + 1, '名单里逐个点名的真题')
    add('真题出处：多改法条数', (extra_dec, dd_ar + extra_dec), (extra_calc, tj_ar),
        '“两种”记 1 条、“三种”记 2 条；右边同时核“道数 ＋ 多改法 ＝ 条数”')
    add('真题出处：算式两端的道数与条数', (dd_ar, tj_ar), (zb_dd, zb_tj))
    check_tongti(md, zhenti_slots([r[0] for r in zhenti_rows(md)]))


def check_tongti(md, reg):
    """交叉闸：**逐字同题组里只要有一个成员登记进了真题出处表，其余成员也必须登记**
    （放行 README 已写明“不是同一道题”的那几个，见 TONGPAI_NOT_SAME）。

    为什么需要：一道题若与某道已登记的题**逐字同题**，它自己也就是那道真题的一个题位；
    2026-09-28 就是这样查出两个漏登的题位（高一39 附加 21 题＝2010 湖南卷（文）、
    高一32 第 13 题＝1999 广东卷／全国卷）——当时机判都报过，只是没人登记，
    而先前的闸只核“表内自洽”，表里少了题位它看不见。
    """
    lines = md.split('\n')
    if lines.count(TONGTI_HEAD) != 1:
        raise AssertionError(f'README 里 `{TONGTI_HEAD}` 应恰好出现一次，实为 {lines.count(TONGTI_HEAD)} 次')
    i = lines.index(TONGTI_HEAD) + 2
    miss = []
    n_grp = 0
    while i < len(lines) and lines[i].startswith('|'):
        cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
        mem = _tongti_members(cells[2])
        if not mem:
            raise AssertionError(f'“逐字同题”表第 {i+1} 行的分布栏一个成员都读不出来（解析失效？）：'
                                 f'{cells[2][:60]}')
        n_grp += 1
        if mem & reg:                       # 本组里有成员已登记 → 其余也得登记
            for v in sorted(mem - reg - TONGPAI_NOT_SAME):
                miss.append(f'{v[0]} {v[1]} 题' if v[1].startswith('附加')
                            else f'{v[0]} 第 {v[1]} 题')
        i += 1
    if n_grp < 30:
        raise AssertionError(f'“逐字同题”表只读到 {n_grp} 行，像是被改坏了')
    add('真题出处：逐字同题组的成员都已登记', [], miss,
        f'{n_grp} 组；放行 {len(TONGPAI_NOT_SAME)} 个已注明“不是同一道题”的成员')


# ----------------------------------------------------------------- 共享题库那一族数
# “共享题库”一节的**逐字同题／同模板变体**两张表是这一族数的唯一真值源，可这几个数在 README 里
# 各写好几遍（核对摘要那一行、本节标题、本节正文、“方法与局限”里又复述一遍），此前**一处闸都没有**，
# 成员数更是**手写累加**的——2026-10-02 逐行复算才发现“逐字 96／仅变体 34／共 130”实为 103／34／137：
# 逐字档有 5 组是 3 份、1 组是 4 份，“组数 × 2”的累加一路少算，变体档还漏登了 07 第 17 题。
# 故这里按两张表全量复算，再与各处声明互校（与“真题出处”那一族同一套做法）。
BIANTI_HEAD = '| 题目 | 份数 | 分布 | 变在哪 |'
SHOUJI_HEAD = '| 题目 | 份数 | 分布 | $r$／LCS |'


def table_rows(md, head):
    """按表头读出一张表的所有数据行（表头必须在 README 里恰好出现一次）。"""
    lines = md.split('\n')
    if lines.count(head) != 1:
        raise AssertionError(f'README 里 `{head}` 应恰好出现一次，实为 {lines.count(head)} 次')
    i = lines.index(head) + 2          # 跳过 `|---|` 分隔行
    rows = []
    while i < len(lines) and lines[i].startswith('|'):
        rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
        i += 1
    if not rows:
        raise AssertionError(f'表 `{head}` 一行都没读到，像是被改坏了')
    return rows


def tongti_counts(md):
    """按两张表逐行数出：(逐字组数, 变体组数, 逐字成员, 仅变体成员, 两档合计, 手工补记对数, 手工补记行数)

    “成员”＝该档各组成员去重后的**本库题位**数；“仅变体”＝出现在变体档、但不在逐字档的成员。
    分布栏里“　”之后是备注（常提到已移出本组的题位），故只取它之前那段——否则会把备注里的
    题位也数进来。手工补记的**对数**＝Σ(该行成员数 − 1)（表自己写着“共 2 对”这类口径）。
    """
    zz = [_tongti_members(r[2].split('　')[0]) for r in table_rows(md, TONGTI_HEAD)]
    bt = [_tongti_members(r[2].split('　')[0]) for r in table_rows(md, BIANTI_HEAD)]
    sj = [_tongti_members(r[2].split('　')[0]) for r in table_rows(md, SHOUJI_HEAD)]
    zset = {x for g in zz for x in g}
    bset = {x for g in bt for x in g}
    return (len(zz), len(bt), len(zset), len(bset - zset), len(zset | bset),
            sum(len(g) - 1 for g in sj), len(sj))


def check_tongti_counts(md):
    n_zz, n_bt, n_zmem, n_bmem, n_all, n_pair, n_sj = tongti_counts(md)
    sm = next(l for l in md.split('\n') if l.startswith('| 跨卷同题（校际重复） |'))
    ti = next(l for l in md.split('\n') if l.startswith('### 上游是“共享题库”'))
    jz = md[md.index('### 上游是“共享题库”'):md.index('### 能考据到的高考出处：')]

    sm_zz, sm_bt = _zhenti_g(r'逐字同题 (\d+) 组 \+ 同模板变体 (\d+) 组\*\*', sm,
                             '摘要：逐字／变体组数', n=2)
    sm_all, sm_zmem, sm_bmem = _zhenti_g(
        r'两档成员共 \*\*(\d+) 道\*\*（逐字 (\d+) ＋ 只出现在变体档的 (\d+)）', sm,
        '摘要：两档成员数', n=3)
    ti_zz, ti_bt = _zhenti_g(r'“共享题库”：(\d+) 组逐字同题 \+ (\d+) 组同模板变体', ti,
                             '节标题：逐字／变体组数', n=2)
    jz_zz = _zhenti_g(r'\*\*逐字同题 (\d+) 组\*\*', jz, '节正文：逐字组数')
    jz_bt = _zhenti_g(r'\*\*同模板变体 (\d+) 组\*\*', jz, '节正文：变体组数')
    ff_zz, ff_bt = _zhenti_g(r'两档分开列（逐字 (\d+) 组 / 同模板变体 (\d+) 组）', md,
                             '“方法与局限”：逐字／变体组数', n=2)
    sj_pair, sj_row = _zhenti_g(r'判据之外手工补记 (\d+) 对（(\d+) 行）', jz,
                                '节正文：手工补记对数／行数', n=2)

    add('共享题库：逐字组数（四处 ↔ 表行数）', (sm_zz, ti_zz, jz_zz, ff_zz), (n_zz,) * 4,
        f'表 {n_zz} 行；四处为摘要／节标题／节正文／“方法与局限”')
    add('共享题库：变体组数（四处 ↔ 表行数）', (sm_bt, ti_bt, jz_bt, ff_bt), (n_bt,) * 4,
        f'表 {n_bt} 行')
    add('共享题库：手工补记对数／行数（↔ 表）', (sj_pair, sj_row), (n_pair, n_sj),
        '对数 ＝ Σ(每行成员数 − 1)')
    add('共享题库：两档成员数（↔ 两表逐行去重）', (sm_zmem, sm_bmem, sm_all),
        (n_zmem, n_bmem, n_all), f'逐字 {n_zmem}、仅变体 {n_bmem}、并集 {n_all}')
    add('共享题库：成员数自洽（逐字 ＋ 仅变体 ＝ 合计）', sm_zmem + sm_bmem, sm_all)


# ----------------------------------------------------------------- 材料流转对照表
# 那张表也是会静默过期的：2026-10-02 查它时发现**三份家长拍照卷只登了两行**（高一b 那行整行漏了），
# 而任何闸都管不到。故按源码现算“数字编号份数”（.tex 数 − 3 份字母卷）与表里的连载行数互校，
# 并把三份字母卷的**名单**也一起断言（只核份数的话，“少了高一b、多登一个连载号”会漏过去）。
LIUZHUAN_HEAD = '| 连载 N | 原文标题里的学校 · 作业 | 发布 | 本地编号 | 状态 |'


def check_liuzhuan(md, n_tex):
    rows = table_rows(md, LIUZHUAN_HEAD)
    # 连载号那一格有的行带加粗标记（表里 **10** 那一行），要先去 `*` 再判是不是数字
    num = [r for r in rows if r[0].strip().strip('*').strip().isdigit()]
    let = [r for r in rows if not r[0].strip().strip('*').strip().isdigit()]
    letters = sorted(re.search(r'高一([0-9a-c]+)', r[3]).group(1) for r in let)
    n_num = n_tex - len(letters)          # 数字编号份数（字母卷不占连载号）
    add('材料流转：连载表行数 ↔ 数字编号份数', len(num), n_num,
        f'{n_tex} 个 .tex − {len(letters)} 份字母卷')
    add('材料流转：字母卷名单', ['a', 'b', 'c'], letters,
        '三份家长拍照卷都要在表里各有一行（2026-10-02 查出 高一b 整整漏了一行）')
    for name, pat in (('“N 篇已收录连载原文”', r'(\d+) 篇已收录连载原文'),
                      ('“连载 a—b 共 N 篇”', r'连载 \d+—\d+ 共 (\d+) 篇'),
                      ('“数字编号现有…共 N 份”', r'数字编号现有 \*\*\d+—\d+ 共 (\d+) 份\*\*')):
        add(f'材料流转：{name}', claim(md, pat, name), n_num)


# ----------------------------------------------------------------- 副标题分布与其他随加卷漂移的数
# "其余 48 份由本稿补出……其中 31 份作'集合与常用逻辑用语'，另 17 份实为两章或纯不等式"
# 这两个数由源码的 `\examtitlest{…}{副标题}` 现算；根 README 里又复述了一遍。
# 另有两处“当前态”的份数是靠人改的（自定义名词那句的份数、“标题行”那句的套数），一并接进闸。
def check_subtitle_dist(md, root, n_tex):
    subs = {}
    for f in srcs():
        raw = load(f)
        st = SUBTITLE.search(raw)
        subs[os.path.basename(f).split('_')[0]] = st.group(1) if st else ''
    plain = {k: v for k, v in subs.items() if k not in SELFSUB}
    n_single = sum(1 for v in plain.values() if v == '集合与常用逻辑用语')
    n_multi = len(plain) - n_single
    a, b = _zhenti_g(r'其中 (\d+) 份作“集合与常用逻辑用语”，\*\*另 (\d+) 份', md,
                     '说明：副标题分布', n=2)
    add('副标题：作“集合与常用逻辑用语”的份数', a, n_single, f'本稿补出的 {len(plain)} 份里')
    add('副标题：标成两章或纯不等式的份数', b, n_multi)
    if root:
        c, d = _zhenti_g(r'副标题 \*\*(\d+) 份\*\*即“集合与常用逻辑用语”，\s*> \*\*另 (\d+) 份',
                         root, '根 README：副标题分布', n=2, flags=re.S)
        add('副标题：根 README 复述的份数', (c, d), (n_single, n_multi),
            '两份文档各写一遍，只改一份是常见漏改')
    n_set = n_tex - COPIES
    add('“自定义名词”那句的份数', claim(md, r'把 \*\*(\d+) 份\*\*试卷里的\*\*自定义名词\*\*',
                                  '自定义名词份数'), n_set)
    add('“标题行”那句的套数', claim(md, r'\*\*标题行\*\*：(\d+) 套卷子的标题', '标题行套数'), n_set)


# ----------------------------------------------------------------- 溯源可复现构建
# 溯源报告用固定 SOURCE_DATE_EPOCH 编译（见 源码/Makefile 的说明），PDF 的 /CreationDate 因此
# 恒等于那个 epoch。这里断言：**Makefile 里钉死的 epoch 与 README转tex.py 的口径日期（RUN_DATE）
# 是同一天**——两处都是“本轮口径的日期”，改一处忘另一处，PDF 元数据就会与页脚的口径标签自相矛盾。
def check_repro():
    mf = io.open(os.path.join(PAPERS, '源码', 'Makefile'), encoding='utf-8').read()
    gen = io.open(os.path.join(HERE, 'README转tex.py'), encoding='utf-8').read()
    m1 = re.search(r'(?m)^SOURCE_DATE_EPOCH\s*:?=\s*(\d+)', mf)
    m2 = re.search(r"(?m)^RUN_DATE\s*=\s*'(\d{4}-\d{2}-\d{2})'", gen)
    if not m1 or not m2:
        raise AssertionError('读不到 源码/Makefile 的 SOURCE_DATE_EPOCH 或 README转tex.py 的 RUN_DATE'
                             '（溯源报告的可复现构建靠这两处，改了名字要同步改这里的正则）')
    d = datetime.datetime.fromtimestamp(int(m1.group(1)), datetime.timezone.utc).strftime('%Y-%m-%d')
    add('溯源可复现构建：SOURCE_DATE_EPOCH ↔ 口径日期', m2.group(1), d,
        'Makefile 里的 epoch 与 README转tex.py 的 RUN_DATE 必须是同一天（改一处要改两处）')
    # 可复现构建的另一半：XeTeX 默认往 /Creator 写**编译时刻、精确到分**，SOURCE_DATE_EPOCH
    # 管不到它——靠 common.sty 里那条 pdf:docinfo special 覆盖成固定串。那条 special 一旦被删
    # 或改坏，“重编一遍 ⇒ 字节不变”就静默失效（实测只差 4 个字节，正文与逐页像素都完全相同，
    # 肉眼看不出、像素比对也查不出），故在这里断言它还在。
    sty = io.open(os.path.join(PAPERS, '源码', 'common.sty'), encoding='utf-8').read()
    m3 = re.search(r'\\special\{pdf:docinfo<<(/Creator\([^)]*\))', sty)
    if not m3:
        raise AssertionError('源码/common.sty 里找不到钉 /Creator 的 pdf:docinfo special'
                             '（可复现构建的一半靠它，见该处注释与 README“编译方式”）')
    add('可复现构建：common.sty 里钉住了 /Creator', '/Creator(Mathematics/papers - XeLaTeX)',
        m3.group(1), 'XeTeX 默认写的编译时刻（到分）不归 SOURCE_DATE_EPOCH 管')


# ----------------------------------------------------------------- ① 机判清单
# ① “与高考库比对”的命中清单（工具/真题命中清单.txt，由 题目溯源.py 生成）里，**每一个报过的
# 本库题位都必须在 README 里 disposition**：要么登记进“真题出处”表（说明它确实是那道真题的
# 题位），要么列在“① 机判报了、但未计入本表的题位”那张台账里。
# 2026-09-28 建这道闸——此前 ① 的命中只印在屏幕上、没人逐条看过：当天照它把 19 条候选摊开判，
# 查出 **2 道一直没登记的真题**（2023 全国乙卷（理）、2009 上海卷（秋文））。
HITLIST = os.path.join(HERE, '真题命中清单.txt')
NOTIN_HEAD = '| 机判报过的题位 | 机判出处 | 为什么不计入 |'


def _hitlist_rows():
    if not os.path.exists(HITLIST):
        raise AssertionError(f'读不到 {HITLIST}——先跑一次 `python3 工具/题目溯源.py 比对` 生成它')
    out = []
    for line in io.open(HITLIST, encoding='utf-8'):
        line = line.rstrip('\n')
        if not line or line.startswith('#'):
            continue
        k, _, v = line.partition('\t')
        paper, _, lab = k.partition('#')
        if not paper or not lab:
            raise AssertionError(f'{os.path.basename(HITLIST)} 有读不懂的行：{line[:60]}')
        out.append(((paper, lab), v))
    return out


def _notin_slots(md):
    """README“① 机判报了、但未计入本表的题位”台账里的题位集合（只看每行第一格）。"""
    lines = md.split('\n')
    if lines.count(NOTIN_HEAD) != 1:
        raise AssertionError(f'README 里 `{NOTIN_HEAD}` 应恰好出现一次，实为 {lines.count(NOTIN_HEAD)} 次')
    i = lines.index(NOTIN_HEAD) + 2
    out = set()
    while i < len(lines) and lines[i].startswith('|'):
        out |= zhenti_slots([lines[i].strip().strip('|').split('|')[0]])
        i += 1
    return out


def check_hitlist(md, reg):
    rows = _hitlist_rows()
    sys.path.insert(0, HERE)
    got = {(x['paper'].split('_')[0], x['lab'])
           for x in importlib.import_module('题目溯源').our_stems()}
    src_keys = {f'{p}#{l}' for p, l in got}
    lst_keys = {f'{p}#{l}' for (p, l), _ in rows}
    add('① 机判清单：题位与源码一致（清单未陈旧）', [], sorted(src_keys ^ lst_keys),
        f'清单 {len(lst_keys)} 个题位、源码现算 {len(src_keys)} 个；加卷/改题后要重跑 `比对` 重写清单')
    noted = _notin_slots(md)
    hit = {k for k, v in rows if v != '无命中'}
    def name(k):
        return f'{k[0]} {k[1]} 题' if k[1].startswith('附加') else f'{k[0]} 第 {k[1]} 题'
    add('① 机判清单：报过的题位都已 disposition', [],
        sorted(name(k) for k in hit - reg - noted),
        f'{len(hit)} 个题位有命中：登记进出处表 {len(hit & reg)} 个、记进“未计入”台账 {len(hit & noted)} 个')
    add('① 机判清单：台账里的题位都真是机判报过的', [],
        sorted(name(k) for k in noted - hit), '台账里不许出现机判没报过的题位')


# ----------------------------------------------------------------- 附加题账目
# “附加题专查”一节原先写“全稿共 5 份卷带附加题、合计 14 道”——那个“全稿”随加卷过期了
# （2026-09-28 查：实为 7 份 / 22 道）。份数与题数都按源码里 `\bigsec{…附加…}` 那一段的
# **顶层** `\item` 数出来（嵌套小问不算；注意 `\item（本题 5 分）` 这类 `\item` 后直接接全角
# 括号、无空格，所以判据用 `\\item(?![A-Za-z])`），对号副本（高一16≡高一b）不计入套数。
FUJIA_HEAD = re.compile(r'\\bigsec\{[^}]*附加[^}]*\}')


def fujia_facts():
    """{卷号: 附加题道数}——只收真有 `\\bigsec{…附加…}` 的源码（含对号副本）。"""
    out = {}
    for f in srcs():
        body_ = body(load(f))
        m = FUJIA_HEAD.search(body_)
        if not m:
            continue
        rest = body_[m.end():]
        b = rest.index('\\begin{enumerate}') + len('\\begin{enumerate}')
        depth, i = 1, b
        while i < len(rest) and depth > 0:          # 找与顶层 enumerate 配对的那个 \end
            if rest.startswith('\\begin{enumerate}', i):
                depth += 1; i += len('\\begin{enumerate}')
            elif rest.startswith('\\end{enumerate}', i):
                depth -= 1
                if depth == 0:
                    break
                i += len('\\end{enumerate}')
            else:
                i += 1
        n = d = 0
        for line in rest[b:i].split('\n'):
            if re.match(r'\s*\\begin\{enumerate\}', line):
                d += 1
            elif re.match(r'\s*\\end\{enumerate\}', line):
                d -= 1
            elif d == 0 and re.match(r'\\item(?![A-Za-z])', line):
                n += 1
        out[os.path.basename(f).split('_')[0]] = n
    return out


def check_fujia(md):
    counts = fujia_facts()
    assert len(COPY_NAMES) == COPIES, 'COPY_NAMES 与 COPIES 不一致（加卷时两处都要改）'
    real = {k: v for k, v in counts.items() if k not in COPY_NAMES}   # 套：排除对号副本
    m = re.search(r'全稿现共 (\d+) 份卷带附加题、合计 (\d+) 道', md)
    if not m:
        raise AssertionError('README 里找不到这处断言：附加题的全稿份数／题数')
    add('附加题：全稿份数（↔ 源码）', int(m.group(1)), len(real),
        '、'.join(f'{k} {v}' for k, v in sorted(real.items())))
    add('附加题：全稿题数（↔ 源码）', int(m.group(2)), sum(real.values()))
    m2 = re.search(r'最早带附加题的五份、合计 (\d+) 道\*\*：', md)
    if not m2:
        raise AssertionError('README 里找不到这处断言：附加题专查那节的“五份、合计 N 道”')
    sent = md[m2.end():md.index('。', m2.end())]
    names = re.findall(r'`(高一[0-9a-c]+)`', sent)
    add('附加题：该节点名的卷都真有附加题', [], [n for n in names if n not in counts])
    add('附加题：该节五份的题数（↔ 源码）', int(m2.group(1)),
        sum(counts[n] for n in names if n in counts), '、'.join(names))


# ----------------------------------------------------------------- 源码侧
def check_source(md):
    raws = [(f, load(f)) for f in srcs()]      # 每个文件只读一次，后文都从这份文本上算
    n_tex = len(raws)
    n_mbox = n_circ = n_circ_files = n_xue = n_nian = 0
    n_sub_std = n_diff = 0
    n_ans_full = 0
    no_diff = []
    bad_sub = []
    no_circ, no_choice, no_fig, tikz, refans = [], [], [], [], []

    for f, raw in raws:
        b = body(raw)
        bn = os.path.basename(f).split('_')[0]
        c = len(CIRCLED.findall(b))
        n_circ += c
        n_circ_files += (c > 0)
        if c == 0:
            no_circ.append(bn)
        if not re.search(r'(?m)^A[.．]', b):        # 没有选项段 ⇒ 全卷无选择题
            no_choice.append(bn)
        if not re.search(r'\\includegraphics', b) and 'tikzpicture' not in b:
            no_fig.append(bn)
        if 'tikzpicture' in b:
            tikz.append(bn)
        if '参考答案' in b:
            refans.append(bn)
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
            raise AssertionError(f'标题既无“学年度”也无“年”：{f}')
        # 副标题：高一14／高一24 是原卷自印、照录；其余按本卷实际内容补出，且只许由“知识模块”
        # 一节里的模块名以“、”连接（不许自造名、不许重复）——见 README“说明”的“标题行”节。
        st = SUBTITLE.search(raw)
        sub = st.group(1) if st else ''
        if bn in SELFSUB:
            if sub != SELFSUB[bn]:
                bad_sub.append(f'{bn}（原卷自印应为“{SELFSUB[bn]}”，实为“{sub}”）')
        else:
            n_sub_std += 1
            parts = sub.split('、')
            if not all(p in MODULES for p in parts) or len(set(parts)) != len(parts):
                bad_sub.append(f'{bn}（“{sub}”）')
        if DIFFSEC.search(header(raw)):
            n_diff += 1
        else:
            no_diff.append(bn)

    n_keep, odd = classify_keep(raws)

    add('套数', claim(md, r'全部 \*\*(\d+) 套\*\*', '套数'), n_tex - COPIES,
        f'{n_tex} 个 .tex − {COPIES} 个对号副本')
    # “套数”在 README 里还有**第二处、措辞不同**的表述——“编译方式”节里复述的定义式
    # “N 个 `.tex` 减去 2 个对号副本 = M 套”。早年只核了上面那条，这处静默停在“26 … 24”
    # （实为 38 … 36，2026-09-26 才发现），故把定义式两半各断一条。
    add('套数（定义式：.tex 数）',
        claim(md, r'(\d+) 个 `\.tex` 减去 2 个对号副本', '定义式 tex 数'), n_tex)
    add('套数（定义式：套数）',
        claim(md, r'减去 2 个对号副本 = (\d+) 套', '定义式套数'), n_tex - COPIES)
    if os.path.exists(ROOT_README):
        root = io.open(ROOT_README, encoding='utf-8').read()
        add('套数（根 README 复述处）', claim(root, r'已入库的 (\d+) 套卷子', '根 README 套数'),
            n_tex - COPIES, '两份文档各写一遍，只改一份是常见漏改')
        # 根 README 还把**定义式的两半**也复述了一遍（“N 个 `.tex` 里 高一16≡高一b…一套副本只算
        # 一套，故 M”）。此前只核了上面那条“N 套”，这两半在 2026-09-28 被发现静默停在
        # “38 个 `.tex` … 故 36”（当时实为 42 … 40）——正是“只核一处、另一处漂掉”的同型，
        # 故这里也各断一条。
        add('套数（根 README 定义式：.tex 数）',
            claim(root, r'：(\d+) 个 `\.tex` 里', '根 README 定义式 tex 数'), n_tex,
            '根 README 也复述了定义式两半')
        add('套数（根 README 定义式：套数）',
            claim(root, r'一套副本只算一套，故 (\d+)', '根 README 定义式套数'), n_tex - COPIES)
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
    add('标题前缀学年度份数', claim(md, r'作“学年度”的 (\d+) 份', '学年度'), n_xue)
    add('标题前缀年份数', claim(md, r'作“年”的 (\d+) 份', '年'), n_nian)
    add('副标题（本稿补出）份数', claim(md, r'标题的 (\d+) 份都是本稿补出', '副标题份数'), n_sub_std)
    add('副标题只用“知识模块”名', 0, len(bad_sub),
        '违规：' + '、'.join(bad_sub) if bad_sub else '全部合规（其余为高一14／高一24 原卷自印值）')
    add('源码头带 ② 的份数', claim(md, r'其中 \*\*(\d+) 份\*\*另有 ②', '带②份数'), n_diff)
    # README 点名“高一a 是唯一没有 ② 的一份”——这是可核的，故连名单一起断言
    # （只核份数的话，“少了两份、但总份数恰好没变”这类错就漏了）。
    add('缺 ② 的卷（README 点名高一a）', '高一a', '、'.join(sorted(no_diff)) or '（无）')
    add('\\ans 含全角（1）份数', claim(md, r'全稿 \*\*(\d+) 份\*\*含多小问答案', 'ans全角'),
        n_ans_full)

    # 形态约定：每枚 \keepwithprev 都必须能归入“选项段”“小问”或“命题段”
    add('\\keepwithprev 可归类', 0, len(odd),
        '；'.join(f'{a} 后接“{b}”' for a, b in odd) if odd else '全部可判')

    # 配对：每处 `\mbox{（\quad）` 所在的 \item 内必须有一枚 \keepwithprev
    unpaired = []
    for f, raw in raws:
        for item in body(raw).split(r'\item')[1:]:
            if MBOX.search(item) and KEEP not in item:
                unpaired.append(os.path.basename(f).split('_')[0])
    add('选择题干与 \\keepwithprev 配对', 0, len(unpaired),
        '缺守卫：' + '、'.join(sorted(set(unpaired))) if unpaired else '全部配对')

    # README 结构：每个“### …专记”小节都要有“**核对面**”段（2026-09-26 立的口径）
    miss = missing_heduimian(md)
    add('专记都有“核对面”段', 0, len(miss),
        '缺：' + '、'.join(miss) if miss else '全部有')

    # ---- 下面四条都是 README 里的**全称/唯一性断言**，2026-10-02 逐个回源码核时发现三条已经
    # 漂了（详见各自的说明）。这类句子没有“N 份”可核，只靠人眼最容易漏，故连名单一起断言。
    m = re.search(r'没用圈数字的 (\d+) 份\*\*是 ([^。]+)', md)
    if not m:
        raise AssertionError('README 里找不到这处断言：“没用圈数字的 N 份是…”')
    add('圈数字：没用的份数与名单', (int(m.group(1)), sorted(re.findall(r'高一[0-9a-c]+', m.group(2)))),
        (len(no_circ), sorted(no_circ)),
        '2026-10-02 前这里写“只有高一06 一份没用”，实为 4 份（40／43／46 入库后没用圈数字）')
    m = re.search(r'六份全卷无选择题', md)
    if not m:
        raise AssertionError('README 里找不到这处断言：“…六份全卷无选择题”')
    seg = md[md.rindex('——', 0, m.start()):m.end()]
    add('全卷无选择题的卷名单', sorted(re.findall(r'高一[0-9a-c]+', seg)), sorted(no_choice),
        '“无选择题”＝源码正文里没有以 A. 开头的选项段（2026-10-02 前这里只写了 高一27／34 两份）')
    add('全卷无插图的份数', claim(md, r'等\*\*(\d+) 份\*\*全卷无插图', '无插图份数'), len(no_fig),
        '“无插图”＝既无 `\\includegraphics`、也无 tikzpicture')
    m = re.search(r'另 2 份——(.+?)——用 TikZ 重绘', md)
    if not m:
        raise AssertionError('README 里找不到这处断言：“另 2 份——…——用 TikZ 重绘”')
    add('用 TikZ 重绘的卷', sorted(re.findall(r'高一[0-9a-c]+', m.group(1))), sorted(tikz),
        '全稿只有这几份的图是 TikZ 重绘、不是原卷截图')
    add('“参考答案”块只在 高一06', '高一06', '、'.join(sorted(refans)) or '（无）',
        '高一06 是唯一把解析集中在文末“参考答案”块的一份')


# ----------------------------------------------------------------- 逐份比对（试卷清单表／逐题核对表）
# 合计值早就进闸了，可“合计对”既掩盖得了“A 份多 1、B 份少 1”这种互补错，也掩盖不了
# “某一行从入库那天起就写错、合计却碰巧对上”。2026-10-02 就是这么查出两行错的：
# 逐题核对表把 高一20 写成 20 题（实为 19，同格自己写着“填空 3—12、选择 13—16、解答 17—21”）、
# 高一21 写成 16 题（实为 12，同格写着“填空 3—11、解答 12—14”）——两处都是**同格自相矛盾**。
QINGDAN_HEAD = '| 系列 | 学校 | 作业 | 页数 试卷/紧凑/答案 | 原图 | 原文 |'
ZHUTI_HEAD = '| 卷 | 原图/题数 | 核对结果 |'
# 对号副本的题数要按它的**原件**算——our_stems() 不收副本（见 COPY_NAMES 的口径）
COPY_OF = {'高一16': '高一b', '高一18': '高一c'}
# 逐题核对表里没有、结论写在“9 月中旬发布的五份‘讲评版’”那一节专记里的五份
ZHUANJI5 = ('高一12', '高一13', '高一14', '高一15', '高一17')


def vol_of(path):
    return os.path.basename(path).split('_')[0]


def yuantu_n(vol):
    """`原图/` 下该卷的图片张数（目录名形如 `高一02_大同中学_集合综合练习`）。"""
    return len(glob.glob(os.path.join(PAPERS, '原图', vol + '_*', '*')))


def check_qingdan(md, pt, pc, pa):
    rows = table_rows(md, QINGDAN_HEAD)
    bad_page, bad_img = [], []
    for r in rows:
        vol = r[0]
        m = re.match(r'(\d+) / (\d+) / (\d+)$', r[3])
        if not m:
            raise AssertionError(f'“试卷清单”表 {vol} 那行的页数读不出来：{r[3][:40]!r}')
        want = tuple(int(x) for x in m.groups())
        got = (pt.get(vol), pc.get(vol), pa.get(vol))
        if None in got:
            raise AssertionError(f'{vol} 在三版里缺成品 PDF（试卷／紧凑／答案各一份）')
        if want != got:
            bad_page.append(f'{vol}（README {want} / 实测 {got}）')
        n = yuantu_n(vol)
        if int(r[4]) != n:
            bad_img.append(f'{vol}（README {r[4]} / 实测 {n}）')
    add('试卷清单：逐份页数（↔ 三版 PDF）', [], bad_page, f'{len(rows)} 份')
    add('试卷清单：逐份原图张数（↔ 原图/）', [], bad_img, f'{len(rows)} 份')
    # README 说紧凑版“**每一份都变短或持平**”——这也是逐份的，不能只看合计
    grow = sorted(v for v in pc if pc[v] > pt[v])
    add('紧凑版每份都不长于试卷版', [], grow, 'README 写着“每一份都变短或持平”')


def check_hedui(md):
    """“回原图逐题核对”表每行的“N 张 / M 题” ↔ `原图/` 目录与源码的一级题干数。"""
    sys.path.insert(0, HERE)
    stems = collections.Counter(
        x['paper'].split('_')[0]
        for x in importlib.import_module('题目溯源').our_stems())
    rows = table_rows(md, ZHUTI_HEAD)
    bad = []
    for r in rows:
        vol = r[0]
        m = re.match(r'(\d+) 张 / (\d+) 题', r[1])
        if not m:
            raise AssertionError(f'“回原图逐题核对”表 {vol} 那行的“张数 / 题数”读不出来：{r[1][:40]!r}')
        z, t = int(m.group(1)), int(m.group(2))
        got_z, got_t = yuantu_n(vol), stems.get(COPY_OF.get(vol, vol))
        if (z, t) != (got_z, got_t):
            bad.append(f'{vol}（README {z} 张 / {t} 题，实测 {got_z} 张 / {got_t} 题）')
    add('逐题核对表：各卷张数/题数（↔ 原图/、源码）', [], bad,
        f'{len(rows)} 行；题数＝源码一级题干数（副本按原件算）')
    # 同一族数在“高一19—21 专记”里还以另一种措辞写了一遍（“**高一20**（N 题答案逐一验算一致”）——
    # 2026-10-02 这两处与表一样写着 20／16（实为 19／12），是**同一处错写了两遍**
    n_ti = []
    for vol, t in re.findall(r'\*\*(高一[0-9a-c]+)\*\*（(\d+) 题答案', md):
        if int(t) != stems.get(COPY_OF.get(vol, vol)):
            n_ti.append(f'{vol}（README {t} 题 / 实测 {stems.get(COPY_OF.get(vol, vol))} 题）')
    add('专记里“N 题答案逐一验算”的题数', [], n_ti, '↔ 源码一级题干数')
    return {r[0] for r in rows}


def check_kuajuan(md):
    """核对范围那三个数（份数／一级题干数／跨卷对数）——摘要与“共享题库”节正文**各写一遍**。

    份数与题数都能现算；对数更是**题数的函数**（C(道数, 2)），所以只要题数一变，两处的
    “339,076 对”必然会跟着变——把它们接进闸，等于让加卷时这两个数自动被比出来。
    """
    sys.path.insert(0, HERE)
    n = len(importlib.import_module('题目溯源').our_stems())
    fen = sorted({int(x) for x in re.findall(r'\*\*(\d+) 份试卷的 \d+ 道\*\*', md)})
    dao = sorted({int(x) for x in re.findall(r'\*\*\d+ 份试卷的 (\d+) 道\*\*', md)})
    dui = sorted({int(x.replace(',', ''))
                  for x in re.findall(r'跨卷(?:两两)?\s*\*\*([\d,]+) 对\*\*', md)})
    if not (fen and dao and dui):
        raise AssertionError('README 里找不到“核对范围”那三个数（份数／一级题干数／跨卷对数）')
    add('核对范围：份数（两处）', fen, [len(srcs()) - COPIES], '摘要与“共享题库”节正文各写一遍')
    add('核对范围：一级题干数（两处）', dao, [n], '源码现算的一级题干数')
    add('核对范围：跨卷对数（两处）', dui, [n * (n - 1) // 2], '＝ C(题干数, 2)，随题数自动变')


def check_yuantu(md, zhuti_vols):
    """'页级核对'那一段的 45 份／388 张、最早 13 份 95 张与'其余'名单。"""
    sec = md[md.index('### 回原图逐题核对'):md.index(ZHUTI_HEAD)]
    sm_n, sm_z = _zhenti_g(r'有原文链接的现为 \*\*(\d+) 份 / (\d+) 张\*\*', sec,
                           '回原图：有链接的份数/张数', n=2)
    e_n, e_z = _zhenti_g(r'\*\*(\d+) 份共 (\d+) 张\*\*', sec, '回原图：最早一批', n=2)
    m = re.search(r'不在那一轮内\s*（(.*?)——这些均为', sec, re.S)
    if not m:
        raise AssertionError('README 里找不到这处断言：回原图“其余…份不在那一轮内（…）”那段名单')
    rest = re.findall(r'(高一[0-9a-c]+)\s+\S+\s+(\d+)\s*张', m.group(1))
    if not rest:
        raise AssertionError('回原图那段名单里一个“高一NN … N 张”都读不出来（解析失效？）')
    n_rest, z_rest = len(rest), sum(int(x[1]) for x in rest)
    # 有原文链接、且不是对号副本的份（高一16／高一18 的原图是拍照卷那两组照片的副本）
    link = [r[0] for r in table_rows(md, QINGDAN_HEAD)
            if 'mp.weixin' in r[5] and r[0] not in COPY_NAMES]
    add('回原图：有原文链接的份数/张数', (sm_n, sm_z),
        (len(link), sum(yuantu_n(v) for v in link)),
        '不含 高一a／b／c 三份拍照卷，也不含两份对号副本')
    add('回原图：两批之和 = 总数', (e_n + n_rest, e_z + z_rest), (sm_n, sm_z),
        f'最早一批 {e_n} 份 {e_z} 张 ＋ 其余 {n_rest} 份 {z_rest} 张')
    add('回原图：“其余”名单都在有链接的份里', [],
        sorted(set(v for v, _ in rest) - set(link)), f'{n_rest} 份')
    # "48 套卷子都过了一遍"：逐题核对表 ∪ 写在专记里的五份，再去掉两份对号副本
    add('回原图：过了一遍的套数', claim(md, r'(\d+) 套卷子都过了一遍', '回原图：套数'),
        len((zhuti_vols | set(ZHUANJI5)) - set(COPY_NAMES)),
        f'逐题核对表 {len(zhuti_vols)} 行 ＋ 专记 {len(ZHUANJI5)} 份 − {COPIES} 份副本')


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
    # 溯源报告的页数在 README 里写了**两遍**，措辞不同：“目录结构”表一处（`` `题目溯源.pdf`，N 页 ``）、
    # “编译方式”节一处（`` `溯源/题目溯源.pdf`（N 页） ``）。早年只核了前者，后者静默过期过一整轮
    # （2026-09-26 才发现），故两处各断一条。
    trace_pages = pdf_pages(os.path.join(PAPERS, '溯源', '题目溯源.pdf'))
    add('溯源报告页数', claim(md, r'`题目溯源\.pdf`，(\d+) 页', '溯源页数'), trace_pages)
    add('溯源报告页数（“编译方式”节）',
        claim(md, r'`溯源/题目溯源\.pdf`（(\d+) 页）', '溯源页数2'), trace_pages)
    add('溯源节抽出行数', claim(md, r'一节抽出 (\d+) 行', '溯源节行数'), trace_section_lines(md))
    bundle = os.path.join(PAPERS, '试卷紧凑', '合并打印版.pdf')
    add('合订本份数', claim(md, r'——(\d+) 份合订', '合订份数'), len(c) - COPIES)
    add('合订本页数', claim(md, r'份合订、(\d+) 页', '合订页数'), pdf_pages(bundle))

    # 逐份页数先存成 {卷号: 页数}：下面“试卷清单”表要逐份比对，合计也由它加出来（每份只读一次盘）
    pt = {vol_of(f): pdf_pages(f) for f in t}
    pc = {vol_of(f): pdf_pages(f) for f in c}
    pa = {vol_of(f): pdf_pages(f) for f in a}
    tp = sum(pt.values())
    cp = sum(pc.values())
    ap = sum(pa.values())
    # “N 份”不写死：加卷后这句里的份数会同时变旧，所以份数与三个页数一起核
    #（写死 24 的话，加第 25 份时这里会报“找不到断言”，把一条本可自动跟上的检查变成手工维护项）。
    n = len(t)
    add('“现 N 份”那句里的份数', claim(md, r'现 (\d+) 份为 \d+ / \d+ / \d+ 页', '现 N 份'), n)
    add('三版总页数（试卷）', claim(md, r'现 \d+ 份为 (\d+) /', '试卷总页'), tp)
    add('三版总页数（紧凑）', claim(md, r'现 \d+ 份为 \d+ / (\d+) /', '紧凑总页'), cp)
    add('三版总页数（答案）', claim(md, r'现 \d+ 份为 \d+ / \d+ / (\d+) 页', '答案总页'), ap)
    add('紧凑版合计页数', claim(md, r'合计 \*\*\d+ → (\d+) 页\*\*', '紧凑合计'), cp)
    # 同一组页数在“说明”一节还复述了一遍（措辞不同，无“现”字），一并核
    add('三版总页数（复述处）', claim(md, r'未改版式，(\d+) 份为 \d+ / \d+ / \d+ 页', '复述份数'), n)
    check_qingdan(md, pt, pc, pa)


def main():
    md = readme_text()
    root = None
    if os.path.exists(ROOT_README):
        root = io.open(ROOT_README, encoding='utf-8').read()
    try:
        check_source(md)
        check_output(md)
        check_zhenti(md)
        check_tongti_counts(md)
        check_hitlist(md, zhenti_slots([r[0] for r in zhenti_rows(md)]))
        check_fujia(md)
        check_liuzhuan(md, len(srcs()))
        check_subtitle_dist(md, root, len(srcs()))
        check_yuantu(md, check_hedui(md))
        check_kuajuan(md)
        check_repro()
    except AssertionError as e:
        print(f'❌ {e}')
        print('   处理：改了 README 措辞就要同步改本脚本里的正则（见文件头“设计 1”）。')
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
        print('   处理：按“实测”列改 README（本脚本是现算的，实测列即当前仓库的真实值）。')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
