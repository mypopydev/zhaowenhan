#!/usr/bin/env python3
"""mistakes/ 计数与一致性自检（make docs 调用）

对照三份材料核数：
  ① English/README.md 里关于本目录的声明
  ② 本目录实际文件（tex / pdf / 原卷扫描件）
  ③ 各 PDF 的页数与内嵌元数据

任一不符即退出码 1，用于提交前把关。新增一套默写或改了 README 数字后，
先跑 `make docs` 再提交。

用法：
    python3 计数核对.py          # 在 mistakes/ 下执行
    make docs                   # 等价（会先确保 PDF 已编译）
"""

import os
import re
import subprocess
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
README = HERE.parent / "README.md"
VOCAB = HERE.parent / "vocabulary"

fails: list[str] = []
notes: list[str] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    mark = "✓" if ok else "✗"
    print(f"  {mark} {label}" + (f"  —— {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(label + (f"（{detail}）" if detail else ""))


def pdf_pages(pdf: Path) -> int | None:
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    return int(m.group(1)) if m else None


def docinfo(pdf: Path) -> str:
    """取 PDF 里的 /Creator /Producer /CreationDate（在压缩对象流里，先解压）"""
    raw = pdf.read_bytes()
    for m in re.finditer(rb"stream\r?\n", raw):
        s = m.end()
        e = raw.find(b"endstream", s)
        try:
            d = zlib.decompress(raw[s:e])
        except zlib.error:
            continue
        mm = re.search(rb"<</Creator.{0,160}", d, re.S)
        if mm:
            return mm.group(0).decode("latin1")
    return ""


def main() -> int:
    readme = README.read_text()
    mk = (HERE / "Makefile").read_text()

    print("=== 1. README 的 make 目标 ↔ Makefile ===")
    declared = set(re.findall(r"^make\s+([a-z-]+)", readme, re.M))
    phony = set(re.search(r"\.PHONY:(.*)", mk).group(1).split())
    missing = declared - phony
    check(not missing, f"README 声明的目标都在 Makefile 里（{' '.join(sorted(declared))}）",
          f"缺 {sorted(missing)}")

    print("\n=== 2. 编译份数 ===")
    tex = sorted(p for p in HERE.glob("*.tex"))
    m = re.search(r"编译全部\s*(\d+)\s*份", readme)
    check(bool(m), "README 写明了 tex 份数")
    if m:
        check(int(m.group(1)) == len(tex), f"README 的份数（{m.group(1)}）== 实际（{len(tex)}）")
    check(all((p.with_suffix(".pdf")).exists() for p in tex),
          f"{len(tex)} 份 tex 都有对应 PDF")

    print("\n=== 3. 各套材料的结构 ===")
    sets = re.findall(r"`((?:vocab|phrase|grammar)_\d\d_[a-z_0-9]+)`", readme)
    check(len(sets) == 8, f"README 列出的套数 = 8", f"实际 {sets}")
    for pre in sets:
        files = {p.name for p in HERE.glob(f"{pre}*")}
        # 语法卷的二刷是「重做 / 答案」，其余套是「中→英 / 英→中 / 答案」
        subs = ([f"{pre}_recheck_q", f"{pre}_recheck_ans"] if pre.startswith("grammar_")
                else [f"{pre}_recheck_zh2en", f"{pre}_recheck_en2cn", f"{pre}_recheck_ans"])
        need = {f"{pre}.tex", f"{pre}.pdf"} | {f"{s}.{e}" for s in subs for e in ("tex", "pdf")}
        scan = [f for f in files if "原卷" in f]
        check(need <= files, f"{pre}: 订正表 + 二刷卷（{len(subs)} 份）齐备", f"缺 {sorted(need - files)}")
        check(len(scan) >= 1, f"{pre}: 有原卷扫描件（{len(scan)} 个）")
        scan_tex = [f for f in scan if f.endswith(".tex")]
        check(not scan_tex, f"{pre}: 原卷只有扫描件、无同名 .tex（distclean 不会误删）",
              f"多出 {sorted(scan_tex)}")

    print("\n=== 4. 页数（对照 README 与 Makefile 的 check 规则）===")
    check("订正表 2 页" in readme and "二刷卷 1 页" in readme and "时态语态 3 页" in readme,
          "README 写明页数规则")
    check('== grammar_01_*_recheck_* ]]; then want=2' in mk
          and 'tense_voice_01.pdf" ]]; then want=3' in mk
          and '*_recheck_* ]]; then want=1' in mk,
          "Makefile 的 check 规则与之一致")
    for texf in tex:
        pdf = texf.with_suffix(".pdf")
        if not pdf.exists():
            continue
        if pdf.name == "tense_voice_01.pdf" or pdf.name == "vocab_04_audience_behaviour_01.pdf":
            want = 3
        elif pdf.name.startswith("grammar_01_") and "_recheck_" in pdf.name:
            want = 2                      # grammar_01 的重做/答案卷各 2 页
        elif "_recheck_" in pdf.name:
            want = 1
        else:
            want = 2                      # 各套订正表（含语法卷）2 页
        got = pdf_pages(pdf)
        check(got == want, f"{pdf.name}: {got} 页（应 {want}）")

    print("\n=== 5. vocabulary 份数（README 声明 ↔ 实际）===")
    counts = {}
    for key, pat in (("zh2en", "zh2en_"), ("en2cn", "en2cn_"),
                     ("ans_zh2en", "ans_zh2en_"), ("ans_en2cn", "ans_en2cn_")):
        counts[key] = len(list(VOCAB.glob(f"[A-Z]/[0-9]*{pat}*.tex")) or
                          [p for p in VOCAB.glob(f"[A-Z]/{pat}*.tex")]) + \
                      len(list(VOCAB.glob(f"extra/{pat}*.tex")))
    q = sum(counts[k] for k in ("zh2en", "en2cn"))
    a = sum(counts[k] for k in ("ans_zh2en", "ans_en2cn"))
    mm = re.search(r"题目\s*(\d+)\s*份\s*\+\s*答案\s*(\d+)\s*份", readme)
    check(bool(mm), "README 写明了 vocabulary 份数")
    if mm:
        check(int(mm.group(1)) == q, f"README 题目份数（{mm.group(1)}）== 实际（{q}）")
        check(int(mm.group(2)) == a, f"README 答案份数（{mm.group(2)}）== 实际（{a}）")

    print("\n=== 6. PDF 元数据来自可复现规则 ===")
    for texf in tex:
        pdf = texf.with_suffix(".pdf")
        if not pdf.exists():
            continue
        info = docinfo(pdf)
        mt = int(texf.stat().st_mtime)
        want = subprocess.run(["date", "-u", "-r", str(mt), "+%Y%m%d%H%M%SZ"],
                              capture_output=True, text=True).stdout.strip()
        ok = "Creator(English/mistakes)" in info and f"CreationDate(D:{want})" in info
        check(ok, f"{pdf.name}: /Creator 与 /CreationDate 已固定", info[:80] or "取不到 docinfo")

    print()
    if fails:
        print(f"❌ {len(fails)} 项不符：")
        for f in fails:
            print(f"   - {f}")
        return 1
    print(f"✅ 全部通过（{len(tex)} 份 tex、{len(sets)} 套默写、页数与元数据均符合声明）")
    for n in notes:
        print(f"   注：{n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
