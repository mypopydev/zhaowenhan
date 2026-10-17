#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""正文指纹 —— 判断两个 PDF 的正文是否“一字不差”（给 make check 用）

    python3 正文指纹.py 试卷/高一10_…_试卷.pdf

输出一行 md5：把 PDF 正文取出、**去掉页码行与所有空白**之后，按字符排序再取哈希。
排序是为了**忽略换行位置**——同一段文字在两版里可以断在不同处（作答区有无会改变分页），
逐行 diff 会假报差异，字符多重集才是“内容是否一致”的正确判据。

为什么不用 shell 流水线：`pdftotext | grep -o . | sort | md5` 在 macOS 上会按**字节**切
多字节汉字，实测对同一段文字给出不同哈希（高一c 就误报过一次）；Python 按字符处理才稳。

页码必须去掉：紧凑版页数比试卷版少，页脚印的“2”“3”自然不同，留着就会被当成内容差异。
**取文必须加 `-layout`**（2026-09-26 改的）：不加时是“原始”阅读顺序，pdftotext 会把页脚的
页码**并进相邻那行正文**——高一32 末页的页码“4”被粘成 `…最小值.4`、紧凑版粘成 `.3`，
于是“整行只有数字才算页码”的过滤器就漏掉了它，同一份源码编出的两版竟报“正文不一致”。
`-layout` 保留版面，页码独占一行、过滤得掉；38 份实测——默认模式 1 份假报，`-layout` 0 份。
"""
import re
import subprocess
import sys
import hashlib
from collections import Counter


def fingerprint(pdf):
    txt = subprocess.run(['pdftotext', '-layout', pdf, '-'],
                         capture_output=True, text=True).stdout
    # 去页码行——**只删“第 k 页末尾且恰为 k”的纯数字行**。原先全文一刀切（任何纯数字行都删），
    # 会把上标分数（如 $a^{\frac12}$）被 pdftotext 拆出来的**单独一行数字**也当页码删掉：
    # 高一62 第 17 题题干 $a^{\frac12}+a^{-\frac12}=\sqrt6$ 的分母「2」在紧凑版里恰好独占
    # 一行被删、试卷版里粘在别行幸存，于是同一份源码的两版被误判“正文不一致”。
    # pdftotext 用 \x0c 分页；页脚就是 \thepage，故“末行＝页号”才算页码，其余纯数字行
    # （分数拆出来的分子分母）一律保留——两版同删/同留，多重集才平衡。
    blocks = []
    for idx, page in enumerate(txt.split('\x0c'), start=1):
        lines = [l for l in page.split('\n') if l.strip()]
        if lines and re.fullmatch(rf'\s*{idx}\s*', lines[-1]):
            lines.pop()
        blocks.append('\n'.join(lines))
    txt = '\n'.join(blocks)
    chars = sorted(Counter(re.sub(r'\s+', '', txt)).elements())
    return hashlib.md5(''.join(chars).encode('utf-8')).hexdigest()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    print(fingerprint(sys.argv[1]))
