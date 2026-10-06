#!/usr/bin/env python3
"""recitation/ 内容自检

对 原文/*.json 做结构与内容检查，并核对生成的 tex 是否含对应条目。

检查项：
  A 条目缺字段（中文/英文为空）
  B 中文段残留英文（说明段内切分失败）
  C 英文段混入中文
  D 中文段残留段首编号（1. / 2、 等）
  E 提示词未在译文中出现（可能是错配或提示词抽取有误）
  F 条目疑似过短（中文 <8 字 或 英文 <25 字符）
  G 原文正文中还有未计入的段落（漏条目）
  H 生成的 tex 中找不到该条目文字（渲染/转义异常）

用法：
    python3 工具/内容校验.py            # 全部期号
    python3 工具/内容校验.py 68 96      # 指定期号
"""

import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, os.pardir)
RAW = os.path.join(ROOT, "原文")
SRC = os.path.join(ROOT, "源码")
CJK = r"\u4e00-\u9fff"


def hint_in_en(hint: str, en: str) -> bool:
    """提示词是否以某种形式出现在译文里（取词干前 5 个字符匹配）"""
    h = re.sub(r"[^a-z]", "", hint.lower())
    if not h:
        return True
    stem = h[:5]
    e = re.sub(r"[^a-z]", "", en.lower())
    return stem in e or h in e


def main() -> int:
    want = sys.argv[1:]
    files = sorted(glob.glob(os.path.join(RAW, "*.json")))
    problems = 0
    for fp in files:
        d = json.load(open(fp, encoding="utf-8"))
        iss = d.get("issue")
        if not iss or not str(iss).isdigit():
            continue
        if want and str(iss) not in want:
            continue
        msgs = []
        items = d.get("items", [])
        for it in items:
            zh, en = it.get("zh", ""), it.get("en", "")
            no = it.get("no")
            if not zh or not en:
                msgs.append(f"A 缺字段 #{no}: zh={zh[:20]!r} en={en[:30]!r}")
            if re.search(rf"[A-Za-z]{{25,}}", zh):
                msgs.append(f"B 中文段残留英文 #{no}: {zh[:45]}")
            if re.search(rf"[{CJK}]", en):
                msgs.append(f"C 英文段混中文 #{no}: {en[:45]}")
            if re.match(r"^\s*\d+\s*[.、)．]", zh):
                msgs.append(f"D 段首编号残留 #{no}: {zh[:30]}")
            if len(zh) < 8 or len(en) < 25:
                msgs.append(f"F 条目过短 #{no}: zh={len(zh)}字 en={len(en)}字符 | {zh[:20]} / {en[:30]}")
            hint = it.get("hint")
            if hint and not hint_in_en(hint, en):
                msgs.append(f"E 提示词未在译文出现 #{no}: 提示={hint} | {en[:50]}")
        # G：原文段落是否被全部计入
        hp = os.path.join(RAW, f"{iss}.html")
        if os.path.exists(hp):
            s = open(hp, encoding="utf-8").read()
            m = re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)<script', s, re.S)
            if m:
                paras = [p for p in re.findall(r"<(?:p|section)[^>]*>(.*?)</(?:p|section)>", m.group(1), re.S)
                         if re.sub(r"<[^>]+>", "", p).strip()]
                # 粗略：条数*2（中+英）+ 谚语*2 应不小于段落数-2（允许前言/尾注）
                expect = len(items) * 2 + (2 if d.get("proverb") else 0)
                if len(paras) > expect + 3:
                    msgs.append(f"G 疑似漏条目：正文 {len(paras)} 段，仅计入 {expect}")
        # H：tex 是否含该期条目
        tp = os.path.join(SRC, f"recitation_{iss}_ans.tex")
        if os.path.exists(tp):
            tx = open(tp, encoding="utf-8").read()
            for it in items:
                key = it["en"][:25].replace("{", "").replace("}", "")
                if key and key not in tx:
                    msgs.append(f"H tex 中缺译文 #{it.get('no')}: {key}")
        if msgs:
            problems += len(msgs)
            print(f"== 第 {iss} 期（{d.get('date')}）")
            for m in msgs:
                print("   " + m)
    print(f"\n共 {problems} 条告警")
    return 0


if __name__ == "__main__":
    sys.exit(main())
