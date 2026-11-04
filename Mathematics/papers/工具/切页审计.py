#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""切页审计 —— 找出“题被切在难看位置”的页

用法
----
    python3 切页审计.py "试卷/*_试卷.pdf"
    python3 切页审计.py "试卷紧凑/*_试卷.pdf"
    python3 切页审计.py "答案/*_答案.pdf"

逐页取文本（`pdftotext -f N -l N`），按三类判“难看切页”，最后给一张每份一卷的表与合计：

  A  **选择题干与选项分页**：页末是选择题干（以“（ ）.”收尾）、次页首行是选项 `A.`
     —— 读者得翻页才能看选项，最影响使用。
  B  **节标题落页末**：页末最后一行是节标题（`一、`…`六、`）—— 标题与它的第一道题分家。
  C  **页末收尾碎片**：页末只剩“）.”这类收尾残片（“（\quad）”与句点被拆行留下）。

判据为什么要这么写
------------------
只按“页末最后一行长什么样”判，不猜排版意图——这三类都是**页末形态**问题，直接看形态最稳。
不要用“某题的文字是否跨页”这类判据：长题跨页是正常且无法避免的（属 D 类，本脚本不报）。

三类都已在 2026-09-15 修掉，**本脚本由此转为回归守卫——正常情况下三版都应报“合计异常：无”
并返回 0**（实测：24 份的三版全部为 0）：
  · B 类 3 处（高一12、高一c 等）→ `common.sty` 的 `\needvspace`，让 `\bigsec` 排版前先量页高；
  · A 类 1 处（高一07 第 16 题）→ `\keepwithprev`（`\nopagebreak[4]`）插在选项段之前；
  · C 类 4＋2 处 → 把“（\quad）.”整体包成 `\mbox`（全库 72 处）——原先断行会正好落在
    `\quad` 这枚胶水上，页末就留下“）.”；包成盒子后不再拆开。

**2026-11-04 给 C 类加一道 `-layout` 复核**：`pdftotext` 默认模式按抽取块顺序出行，
`\mbox{（\quad）}` 右侧的全角“）”可能被单独建块、排到该页文本流的最末尾，于是
`lines[-1]` 是“）”而物理页末其实是完整的题干＋选项（高一110 答案版 p3 即此例）。
这类是抽取顺序噪声，不是真的“页末收尾碎片”。故默认模式报 C 类时再用
`pdftotext -layout` 取同一页的末行复核：**真碎片在 `-layout` 下也独占一行**（物理断行
真实存在），只有两次都命中才报。方向是只减少假阳性，不放宽任何真问题。

与 `工具/正文指纹.py` 的分工：那个管“内容有没有变”（紧凑版 vs 试卷版逐字一致），
这个管“分页好不好看”。两个都不进 `make check`（本脚本读的是成品 PDF，跑一次要几十秒）。
"""
import glob
import os
import re
import subprocess
import sys

B = re.compile(r'^[一二三四五六]\s*、')                 # 节标题
A_STEM = re.compile(r'（\s*）\s*\.?\s*$')               # 选择题干收尾“（ ）.”
A_OPT = re.compile(r'^\s*[ABCD][.．]\s')               # 选项行
C_FRAG = re.compile(r'^[）)]\s*[.．]?$')                # 收尾碎片“）.”


def pages(pdf):
    """每页的正文行（去掉页码行与空行）"""
    info = subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout
    n = int(info.split('Pages:')[1].split('\n')[0])
    out = []
    for i in range(1, n + 1):
        t = subprocess.run(['pdftotext', '-f', str(i), '-l', str(i), pdf, '-'],
                           capture_output=True, text=True).stdout
        out.append([l.strip() for l in t.split('\n')
                    if l.strip() and not re.fullmatch(r'\s*\d*\s*', l)])
    return out


def layout_last(pdf, pno):
    """`-layout` 模式下该页的最后一个正文行（按物理位置，而非抽取块顺序）。"""
    t = subprocess.run(['pdftotext', '-f', str(pno), '-l', str(pno), '-layout', pdf, '-'],
                       capture_output=True, text=True).stdout
    lines = [l.strip() for l in t.split('\n')
             if l.strip() and not re.fullmatch(r'\s*\d*\s*', l)]
    return lines[-1] if lines else ''


def audit(pdf):
    pg = pages(pdf)
    bad = []
    for i, lines in enumerate(pg[:-1]):
        nxt = pg[i + 1]
        if not lines or not nxt:
            continue
        if B.match(lines[-1]):
            bad.append((i + 1, 'B 节标题落页末'))
        if A_STEM.search(lines[-1]) and A_OPT.match(nxt[0]):
            bad.append((i + 1, 'A 选择题干与选项分页'))
        # 默认模式的“）”可能只是 pdftotext 抽取顺序噪声；物理页末（-layout）也是碎片才报
        if C_FRAG.match(lines[-1]) and C_FRAG.match(layout_last(pdf, i + 1)):
            bad.append((i + 1, 'C 页末收尾碎片'))
    return len(pg), bad


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    files = sorted(glob.glob(sys.argv[1]))
    if not files:
        print('没有匹配的文件：%s' % sys.argv[1])
        sys.exit(1)
    tot = {}
    for f in files:
        n, bad = audit(f)
        name = os.path.basename(f).replace('_试卷.pdf', '').replace('_答案.pdf', '')
        marks = '；'.join('p%d %s' % b for b in bad)
        print('  %-44s %d 页  %s' % (name[:42], n, ('⚠ ' + marks) if bad else '✔'))
        for _, k in bad:
            tot[k] = tot.get(k, 0) + 1
    print('\n  %d 份，合计异常：%s' % (len(files),
                                   '、'.join('%s×%d' % (k, v) for k, v in sorted(tot.items())) or '无'))
    sys.exit(1 if tot else 0)


if __name__ == '__main__':
    main()
