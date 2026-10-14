#!/usr/bin/env python3
"""recitation/ 抓取与解析（微信公众号《上海高考高分翻译背诵》）

用法：
    python3 工具/抓取解析.py <文章URL> [<文章URL> ...]
    python3 工具/抓取解析.py urls.txt      # 每行一个 URL

产出（写在 ../原文/）：
    <期号>.html   原文 HTML 的精简版（只留标题/发布时间/正文，平台脚本已剔除）
    <期号>.json   解析后的条目数据（重排依据）

解析规则：
  - 正文在 <div id="js_content"> 内，段落交替：中文段（末尾括号为提示词）→ 英文段
  - 末尾若出现「英文在前、中文在后」的成对段，判为谚语
  - 末尾的「英文+短释义」对照串（如 114 期「-sing solo独唱 smooth out消除…」）判为**本期词汇**，
    存进 vocab 字段（不入条目）；「知识星球」推广尾注按尾注滤掉
"""

import datetime
import html
import json
import os
import re
import glob
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, os.pardir, "原文")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def fetch(url: str) -> str:
    r = subprocess.run(
        ["curl", "-sL", "-A", UA, "-e", "https://mp.weixin.qq.com/", url],
        capture_output=True,
    )
    return r.stdout.decode("utf-8", errors="ignore")


def slim(s: str) -> str:
    """只保留标题、发布时间与正文 js_content——原页自带数 MB 平台脚本，入库前剔除"""
    title, ct = meta(s)[0], re.search(r"var ct\s*=\s*\"?(\d{10})", s)
    m = re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)</div>\s*(?=<script|$)', s, re.S)
    body = f'<div id="js_content">{m.group(1)}</div>' if m else '<div id="js_content"></div>'
    return (f"<!-- 精简版原文：仅保留标题 / 发布时间 / 正文 js_content，平台脚本已剔除 -->\n"
            f"var msg_title = '{title}';\n"
            f'var ct = "{ct.group(1) if ct else ""}";\n'
            f"{body}\n"
            f"<script></script>\n")


def meta(s: str):
    def g(p):
        m = re.search(p, s)
        return m.group(1) if m else None

    title = (g(r'var msg_title\s*=\s*[\'"]([^\'"]+)') or "").strip()
    ct = g(r'var ct\s*=\s*"?(\d{10})')
    date = datetime.datetime.fromtimestamp(int(ct)).strftime("%Y-%m-%d") if ct else ""
    # 标题形如：…背诵-105-26二模 / 每日背诵-59 / …-99（末尾）
    m = (re.search(r"-(\d+)-", title) or re.search(r"-(\d+)\s*$", title)
         or re.search(r"第\s*(\d+)\s*[期讲]", title))
    issue = m.group(1) if m else None
    return title, date, issue


def body_paragraphs(s: str):
    m = re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)<script', s, re.S)
    body = m.group(1) if m else ""
    paras = re.findall(r"<(?:p|section)[^>]*>(.*?)</(?:p|section)>", body, re.S)
    out = []
    for p in paras:
        t = html.unescape(re.sub(r"<[^>]+>", "", p)).replace("\xa0", " ").strip()
        if t:
            out.append(t.rstrip("\\").strip())
    return out


# 「知识星球」是 2026-10-14 起（第 112 期）每期都有的**推广尾注**
# （「笔者现已开通知识星球，内容每日更新…」），与既有的点赞/关注一类同性质，一并滤掉
NOTE_PAT = re.compile(r"手搓|点赞|转发|推荐|感谢支持|如裨益|内容均为|扫码|关注|往期|合集|点个在看|星标|知识星球")
CJK = r"\u4e00-\u9fff"


def is_note(t: str) -> bool:
    return bool(NOTE_PAT.search(t)) and not re.search(r"[（(][^）)]{1,12}[）)]\s*$", t)


def has_cjk(t: str) -> bool:
    return bool(re.search(f"[{CJK}]", t))


# parse() 自己产出的字段——超出这个集合的键说明是**人工补的**，--reparse 不覆盖
PARSED_KEYS = {"title", "issue", "date", "url", "items", "proverb", "vocab", "warns"}
ITEM_KEYS = {"no", "zh", "hint", "en", "alt"}


# 「本期词汇」尾块：整段是「英文 + 短汉字释义」的对照串，如第 114 期的
# 「-sing solo独唱 smooth out消除  fast-growing 快速发展的」。它不是翻译条目、也不是谚语，
# 单列进 json 的 vocab 字段（生成器在三版末尾排成一块「本期词汇」）。
VOCAB_PAIR = re.compile(rf"(-?[A-Za-z][A-Za-z\-'’]*(?:\s+[A-Za-z\-'’]+)*)\s*([{CJK}]{{1,6}})")


def parse_vocab(t: str):
    """整段是词汇对照块则返回 [{"en","zh"}]，否则 None。

    三条判据同时成立才认（防误吞正常条目或谚语）：
      ① 段内没有句末标点「。！？」——正常中文条目的句子都以「。」收尾；
      ② 至少 2 组「英文 + 短释义」（释义 ≤6 字）；
      ③ 段内**所有**汉字都被这些释义覆盖（不留孤立汉字）。
    """
    if re.search(r"[。！？]", t):
        return None
    pairs = []
    for m in VOCAB_PAIR.finditer(t):
        en, zh = m.group(1).strip(), m.group(2)
        pairs.append({"en": en, "zh": zh})
    covered = sum(len(p["zh"]) for p in pairs)
    total_cjk = len(re.findall(f"[{CJK}]", t))
    if len(pairs) < 2 or covered < total_cjk:
        return None
    return pairs


def parse(s: str, url: str):
    title, date, issue = meta(s)
    paras = [p for p in body_paragraphs(s) if not is_note(p)]
    items, proverb, warns, vocab = [], None, [], None
    i = 0
    while i < len(paras):
        cur = paras[i]
        # ⓬ 「本期词汇」尾块（第 114 期首见）：整段英文＋短释义对照 → vocab
        if vocab is None:
            vc = parse_vocab(cur)
            if vc:
                vocab = vc
                i += 1
                continue
        numbered = re.match(r"^\s*\d+\s*[.、)．]\s*", cur)
        # ⓪ 「N. 英文. 中文」例句体（早期期号）：拆成一条（英文在前、中文在后）
        if numbered:
            body = cur[numbered.end():]
            mm = re.match(rf"^([A-Za-z][^{CJK}]{{20,}}?)\s*([{CJK}].*)$", body)
            if mm:
                en = mm.group(1).strip()
                zh = mm.group(2).strip()
                mh2 = re.search(r"[（(]([^）)]+)[）)]\s*$", zh)
                hint = mh2.group(1) if mh2 else None
                if mh2:
                    zh = zh[:mh2.start()].strip()
                items.append({"no": len(items) + 1, "zh": zh, "hint": hint, "en": en})
                i += 1
                continue
            paras[i] = body          # 只去掉段首编号，按常规中→英处理
            cur = body
        # ① 同一段内「英文. + 中文」→ 谚语
        inline = re.match(rf"^([A-Za-z][^{CJK}]*?[.!?])\s*([{CJK}].*)$", cur)
        if inline:
            proverb = {"en": inline.group(1).strip(), "zh": inline.group(2).strip()}
            i += 1
            continue
        if has_cjk(cur):
            mz = re.match(rf"^(.*?[。！？，、])\s*([A-Za-z][^{CJK}]{{20,}}[.!?])\s*$", cur)
            if mz:
                zh = mz.group(1).strip()
                en = mz.group(2).strip()
                mh3 = re.search(r"[（(]([^）)]+)[）)]\s*$", zh)
                hint = mh3.group(1) if mh3 else None
                if mh3:
                    zh = zh[:mh3.start()].strip()
                items.append({"no": len(items) + 1, "zh": zh, "hint": hint, "en": en})
                i += 1
                continue
            mh = re.search(r"[（(]([^）)]+)[）)]\s*$", cur)
            zh = cur[:mh.start()].strip() if mh else cur
            hint = mh.group(1) if mh else None
            ens, j = [], i + 1
            while j < len(paras) and not has_cjk(paras[j]):
                ens.append(re.sub(r"^\s*\d+\s*[.、)．]\s*", "", paras[j])); j += 1
            # 多段英文：若紧随其后的中文段**无提示词**，则「末段英文 + 该中文」是谚语
            nxt = paras[j] if j < len(paras) else None
            if len(ens) >= 2 and nxt and has_cjk(nxt) and not re.search(r"[（(][^）)]+[）)]\s*$", nxt):
                proverb = {"en": ens[-1], "zh": nxt}
                ens, j = ens[:-1], j + 1
            if ens:
                items.append({"no": len(items) + 1, "zh": zh, "hint": hint,
                              "en": ens[0], "alt": ens[1:]})
                i = j
                continue
            # 无对应英文：短句判为谚语（原文可能只给中文），长句报警
            if len(zh) <= 15:
                proverb = {"en": "", "zh": zh}
            else:
                warns.append(f"第 {len(items)+1} 条缺英文：{zh[:30]}")
                items.append({"no": len(items) + 1, "zh": zh, "hint": hint, "en": ""})
            i += 1
            continue
        # ② 英文段 + 下一段中文 → 谚语
        if i + 1 < len(paras) and has_cjk(paras[i + 1]):
            proverb = {"en": cur, "zh": paras[i + 1]}
            i += 2
            continue
        warns.append(f"孤立英文段：{cur[:30]}")
        i += 1
    return {"title": title, "issue": issue, "date": date, "url": url,
            "items": items, "proverb": proverb, "vocab": vocab or [], "warns": warns}


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    if "--reparse" in args:
        args.remove("--reparse")
        for fp in sorted(glob.glob(os.path.join(OUT, "*.html"))):
            s = open(fp, encoding="utf-8").read()
            data = parse(s, "")
            # 文件名优先：文件名是人工核定过的（如 79.html 的原文标题本身误写 -78-）
            mb = re.match(r"^(\d+)", os.path.basename(fp))
            if mb:
                data["issue"] = mb.group(1)
            name = data["issue"] or os.path.basename(fp).split(".")[0]
            # 保留既有 JSON 里的来源链接；若同号同日的 JSON 已存在则跳过，避免产生副本
            jp0 = os.path.join(OUT, f"{name}.json")
            if os.path.exists(jp0):
                try:
                    old0 = json.load(open(jp0, encoding="utf-8"))
                    if old0.get("url"):
                        data["url"] = old0["url"]
                    # **人工补过字段的 json 一律不重写**：parse() 不产出这些字段，
                    # 重写会把人工成果静默冲掉（2026-10-14 踩到——107.json 的
                    # correction／editor_note 是本模块唯一一处「原文参考译文有误」订正，
                    # 生成器生成 tex 时要读它；64／75／78／79 另有顶层 note）
                    hand = (set(old0) - PARSED_KEYS) | (
                        {k for it in old0.get("items", []) for k in it} - ITEM_KEYS)
                    if hand:
                        print(f"  · {name} 含人工字段 {sorted(hand)}，跳过（不覆盖）")
                        continue
                    # 老 JSON 没有 vocab 字段时按「与本次一致」处理——避免回归重解析时
                    # 仅仅为了补一个空字段而重写全部 72 份 json（vocab 是可选字段）
                    if (old0.get("date") == data.get("date")
                            and old0.get("items") == data.get("items")
                            and old0.get("vocab", data["vocab"]) == data["vocab"]):
                        print(f"  · {name} 与既有 JSON 一致，跳过")
                        continue
                except Exception:
                    pass
            with open(os.path.join(OUT, f"{name}.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            p = data["proverb"]
            print(f"✓ {name}: 条目 {len(data['items'])}，"
                  f"谚语 {('有 ' + p['en'][:28]) if p and p.get('en') else ('仅有中文' if p else '无')}")
            for w in data.get("warns", []):
                print(f"    ⚠ {w}")
        return 0

    if len(args) == 1 and os.path.isfile(args[0]):
        urls = [u.strip() for u in open(args[0]) if u.strip()]
    else:
        urls = args

    os.makedirs(OUT, exist_ok=True)
    for k, url in enumerate(urls):
        if k:
            time.sleep(2)                     # 限速，避免被风控
        s = fetch(url)
        if 'id="js_content"' not in s:
            print(f"✗ 抓取失败（无正文）：{url}")
            continue
        data = parse(s, url)
        name = data["issue"] or f"unnamed_{int(time.time())}"
        jp = os.path.join(OUT, f"{name}.json")
        # 期号撞号：已有同号但不同链接时，文件名带日期区分，避免覆盖
        dup = False
        if os.path.exists(jp):
            try:
                old = json.load(open(jp, encoding="utf-8"))
                if old.get("url") and old["url"] != url:
                    dup = True
                    name = f"{name}_{data['date']}"
                    jp = os.path.join(OUT, f"{name}.json")
            except Exception:
                pass
        open(os.path.join(OUT, f"{name}.html"), "w", encoding="utf-8").write(slim(s))
        with open(jp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        if dup:
            print(f"\u26a0 期号 {data['issue']} 撞号（已存在另一篇），本次存为 {name}")
        p = data["proverb"]
        print(f"✓ {name}: {data['title']}（{data['date']}） "
              f"条目 {len(data['items'])}，谚语 {'有' if p else '无'}")
        for it in data["items"]:
            print(f"    {it['no']} [{it['hint']}] {it['zh'][:26]}…")
        if p:
            print(f"    谚语 {p['en'][:40]} / {p['zh']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
