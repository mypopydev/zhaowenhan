#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并试卷.py —— 把 试卷紧凑/ 下的成品卷合成一份便于打印的 PDF

用法
----
    python3 工具/合并试卷.py        # → 试卷紧凑/合并打印版.pdf
    make bundle                     # 上面这一步（+ 依赖检查）

约定
----
  · **目录**：只收 `试卷紧凑/*_试卷.pdf`。合并件自己叫「合并打印版.pdf」，**不匹配这个
    通配符**，所以不会把自己卷进下一轮（这是当初挑这个名字的用意）。
  · **顺序**：按文件名排序 = `高一02`…`高一21`、`高一a`、`高一b`、`高一c`
    （数字＝公众号连载号、字母＝拍照卷，与 README 的编号规则一致；`0`<`2`<`a` 的字典序
    正好给出这个顺序，不必另写排序键）。
  · **排除对号副本**：`高一16` 与 `高一b`、`高一18` 与 `高一c` 去掉标题的「（补）」二字后
    **逐字相同**（见 README「编号规则」），打印版只收一份——留着会白印两套。故 21 份 / 46 页。
  · **页码**：各卷的页码是编在卷面里的，合并后每份仍从 1 开始。要连续页码得重新排版整册，
    不在本脚本范围。
  · **书签**：每份卷子加一个 PDF 书签（电脑上看时可直接跳转），书签名用「高一NN · 学校 作业名」。
    打印用不到书签，但加它只多几行，比 `pdfunite` 多出来的就这一点。
"""
import glob
import io
import os
import re
import subprocess
import sys

from pypdf import PdfReader, PdfWriter

HERE = os.path.dirname(os.path.abspath(__file__))
PAPERS = os.path.normpath(os.path.join(HERE, '..'))
SRC_DIR = os.path.join(PAPERS, '试卷紧凑')
OUT = os.path.join(SRC_DIR, '合并打印版.pdf')
PAT = '*_试卷.pdf'

# 对号副本：与 高一b／高一c 逐字相同，打印版只收一份
SKIP = ('高一16', '高一18')


def title_of(path):
    """`高一02_大同中学_集合综合练习_试卷.pdf` → 「高一02 · 大同中学 集合综合练习」"""
    base = os.path.basename(path)
    base = re.sub(r'_试卷\.pdf$', '', base)
    parts = base.split('_')
    return parts[0] + ' · ' + ' '.join(parts[1:])


def page_texts(path):
    """抽一份 PDF 的逐页文本（按分页符切；末尾空元素去掉）"""
    out = subprocess.run(['pdftotext', path, '-'], capture_output=True, text=True).stdout
    pages = [p.strip() for p in out.split('\f')]
    while pages and not pages[-1]:
        pages.pop()
    return pages


def verify(merged, keep):
    """逐页比对：合并件的每一页必须与**来源 PDF 的对应页**逐字相同

    比「整篇字符数相等」更严——整篇相等理论上可能掩盖「两页对调」（同页文本完全相同时）。
    两侧都用 `pdftotext`（同一支抽取器）才好逐字比，所以这里不拿 pypdf 的抽取结果去比。
    """
    mp = page_texts(merged)
    i, nchar = 0, 0
    for f in keep:
        sp = page_texts(f)
        for k, src in enumerate(sp):
            if i + k >= len(mp):
                return False, '合并件页数不足：%s 第 %d 页找不到对应页' % (title_of(f), k + 1)
            if mp[i + k] != src:
                return False, ('%s 第 %d 页与合并件第 %d 页不一致' %
                               (title_of(f), k + 1, i + k + 1))
            nchar += len(src)
        i += len(sp)
    if i != len(mp):
        return False, '合并件多出 %d 页' % (len(mp) - i)
    return True, '%d 页逐字相同、合计 %d 字符' % (len(mp), nchar)


def main():
    files = sorted(glob.glob(os.path.join(SRC_DIR, PAT)))
    if not files:
        sys.exit('❌ %s 里没有 %s，先跑 make compact' % (SRC_DIR, PAT))
    keep = [f for f in files if not os.path.basename(f).startswith(SKIP)]
    drop = [f for f in files if os.path.basename(f).startswith(SKIP)]

    w = PdfWriter()
    rows = []
    for f in keep:
        r = PdfReader(f)
        start = len(w.pages)
        for p in r.pages:
            w.add_page(p)
        w.add_outline_item(title_of(f), start)
        rows.append((title_of(f), len(r.pages), start + 1))
    total = len(w.pages)
    w.add_metadata({
        '/Title': '上海高一上数学 集合与常用逻辑用语 · 紧凑试卷 %d 份合订（%d 页）'
                  % (len(keep), total),
        '/Subject': '试卷紧凑版合订打印本（无答案、无解答题作答区；页码各卷独立）',
        '/Creator': 'papers/工具/合并试卷.py',
    })
    with io.open(OUT, 'wb') as fh:
        w.write(fh)

    # 自校验：页数、书签数、以及**逐页逐字**与来源一致
    chk = PdfReader(OUT)
    marks = chk.outline
    n_marks = len(marks) if marks else 0
    print('✅ %s' % os.path.relpath(OUT, PAPERS))
    print('   %d 份 / %d 页；书签 %d 个' % (len(keep), len(chk.pages), n_marks))
    if len(chk.pages) != total or n_marks != len(keep):
        sys.exit('❌ 自校验失败：页数或书签数与预期不符')
    ok, msg = verify(OUT, keep)
    if not ok:
        sys.exit('❌ 逐页比对失败：%s' % msg)
    print('   逐页比对：%s' % msg)
    for t, n, p in rows:
        print('     %-30s %d 页  起第 %d 页' % (t, n, p))
    if drop:
        print('   已排除对号副本：%s（与 高一b／高一c 逐字相同）'
              % '、'.join(title_of(f) for f in drop))


if __name__ == '__main__':
    main()
