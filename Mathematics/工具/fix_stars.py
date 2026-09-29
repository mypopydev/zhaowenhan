#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_stars —— 把 EPUB 里作为「数学记号」的 ASCII 星号 * 批量换成 ∗（U+2217）

    python3 fix_stars.py 输入.epub 输出.epub

场景：电子书里的公式常把「对偶／共轭星」排成 ASCII `*`（如 `d*F = 4π*J`、`q⁻¹ = q*/qq*`）。
`*` 在 Markdown 里是强调标记，**同一段落里成对的裸 `*` 会在转换/渲染时被当成斜体吃掉**——
实测（2026-09-29，Robyn Arianrhod《Vector》EPUB）：

    原版：`d*F = 4π*J, dF = 0.`  →  渲染成 `dF = 4πJ, dF = 0.`（两颗对偶星全丢）
          `q⁻¹ = q*/qq*, where q* is…`  →  `q^/qq^`（两颗共轭星被吃，还拖出假斜体）
          `a = UpU*`、`M87*` 因**落单**（同段里不成对）而幸存
    换 ∗ 后：上述全部无损落盘，且与强调标记在视觉上彻底分离

为什么可以「全换」而不会伤到强调格式：XHTML 里强调是 `<i>`/`<b>` **标签**，没有基于 `*`
的语法，所以源文件里出现的每一个 `*` 都是**字面星**。同一次实测：《Vector》全书 XHTML 里
`*` 共 7 个（麦克斯韦对偶 2、四元数共轭 4、黑洞名 `M87*` 1），本脚本替换 7 个、强调标记
一个没碰。

四条注意：
  ① **上标信息不保**：书里那几颗共轭星原是**上标**（`<sup>*</sup>`），换掉后纯文本导出仍会
     把上标压平（`q^∗`）。要真上标得靠 `<sup>`／`^{}`（注意：Markdown 里的 `x^{*}` 同样会
     丢星，实测渲染成 `x^{}`——要用 `x^{∗}`）。
  ② **黑洞名也会被换**：`M87*` → `M87∗`；拿它去 arXiv/ADS 检索时记得换回 ASCII `*`。
  ③ **PDF 不适用**：星在 PDF 内容流里、是排版字形，重打一遍文本没用；要从 EPUB 取文本。
  ④ 若某本书的 HTML **真把 `*` 当标记**用（自制电子书里偶见），别用本脚本。

自检（写完立刻重开输出文件验，任一不符即非零退出）：条目数不变、`mimetype` 仍在首位、
ASCII `*` 归零、`∗` 的个数 == 替换掉的个数。
"""
import io
import os
import sys
import zipfile

ASTERISK = '*'
STAR_OP = '\u2217'          # ∗ ASTERISK OPERATOR（Hodge star／共轭的常见排印）
TEXT_EXT = ('.xhtml', '.html', '.htm', '.xml', '.opf', '.ncx')


def fix(src, dst):
    zin = zipfile.ZipFile(src)
    names = zin.namelist()
    if names[0] != 'mimetype':
        sys.exit('❌ 输入不是规范 EPUB（首条目不是 mimetype）：%s' % src)
    n_star = n_file = 0
    with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.lower().endswith(TEXT_EXT):
                t = data.decode('utf-8')
                c = t.count(ASTERISK)
                if c:
                    t = t.replace(ASTERISK, STAR_OP)
                    n_star += c
                    n_file += 1
                data = t.encode('utf-8')
            # mimetype 必须第一个、且不压缩（EPUB 规范）
            zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
            zi.compress_type = (zipfile.ZIP_STORED if item.filename == 'mimetype'
                                else item.compress_type)
            zi.external_attr = item.external_attr
            zout.writestr(zi, data)
    # ---- 自检：重开输出文件核对 ----
    z = zipfile.ZipFile(dst)
    a = s = 0
    for n in z.namelist():
        if n.lower().endswith(('.xhtml', '.html')):
            t = z.read(n).decode('utf-8', 'replace')
            a += t.count(ASTERISK)
            s += t.count(STAR_OP)
    bad = []
    if len(z.namelist()) != len(names):
        bad.append('条目数 %d != %d' % (len(z.namelist()), len(names)))
    if z.namelist()[0] != 'mimetype':
        bad.append('mimetype 不在首位')
    if z.testzip() is not None:
        bad.append('有坏条目：%s' % z.testzip())
    if a != 0:
        bad.append('输出里还剩 %d 个 ASCII 星' % a)
    if s != n_star:
        bad.append('∗ 的个数 %d != 替换数 %d' % (s, n_star))
    print('   替换 %d 颗 ASCII 星 → ∗（U+2217），涉及 %d 个文件' % (n_star, n_file))
    print('   输出 %s（%.1f MB）；自检：ASCII 星 %d、∗ %d' %
          (dst, os.path.getsize(dst) / 1024 / 1024, a, s))
    if bad:
        sys.exit('❌ 自检未过：' + '；'.join(bad))
    print('✅ 自检通过（条目数／mimetype 位置／坏条目／两处计数）')


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    if not os.path.exists(sys.argv[1]):
        sys.exit('❌ 找不到输入：%s' % sys.argv[1])
    if os.path.exists(sys.argv[2]):
        sys.exit('❌ 输出已存在，先删掉或换个名字：%s' % sys.argv[2])
    fix(sys.argv[1], sys.argv[2])


if __name__ == '__main__':
    main()
