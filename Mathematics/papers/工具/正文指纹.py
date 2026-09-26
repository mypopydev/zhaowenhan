#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""正文指纹 —— 判断两个 PDF 的正文是否「一字不差」（给 make check 用）

    python3 正文指纹.py 试卷/高一10_…_试卷.pdf

输出一行 md5：把 PDF 正文取出、**去掉页码行与所有空白**之后，按字符排序再取哈希。
排序是为了**忽略换行位置**——同一段文字在两版里可以断在不同处（作答区有无会改变分页），
逐行 diff 会假报差异，字符多重集才是「内容是否一致」的正确判据。

为什么不用 shell 流水线：`pdftotext | grep -o . | sort | md5` 在 macOS 上会按**字节**切
多字节汉字，实测对同一段文字给出不同哈希（高一c 就误报过一次）；Python 按字符处理才稳。

页码必须去掉：紧凑版页数比试卷版少，页脚印的「2」「3」自然不同，留着就会被当成内容差异。
**取文必须加 `-layout`**（2026-09-26 改的）：不加时是「原始」阅读顺序，pdftotext 会把页脚的
页码**并进相邻那行正文**——高一32 末页的页码「4」被粘成 `…最小值.4`、紧凑版粘成 `.3`，
于是「整行只有数字才算页码」的过滤器就漏掉了它，同一份源码编出的两版竟报「正文不一致」。
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
    txt = '\n'.join(l for l in txt.split('\n') if not re.fullmatch(r'\s*\d*\s*', l))  # 去页码行
    chars = sorted(Counter(re.sub(r'\s+', '', txt)).elements())
    return hashlib.md5(''.join(chars).encode('utf-8')).hexdigest()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    print(fingerprint(sys.argv[1]))
