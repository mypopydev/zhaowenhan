#!/usr/bin/env python3
"""recitation/ 由原文/*.json 生成三版 tex 源码

用法：
    python3 工具/生成tex.py              # 处理 原文/ 下全部 json
    python3 工具/生成tex.py 104 105      # 只处理指定期号

产出（写在 ../源码/）：
    <期号>_zh2en.tex  默写卷（中文 + 提示词，英文留空）
    <期号>_ans.tex    中英对照（背诵 · 答案）
    <期号>_en2zh.tex  回译卷（英文，中文留空）
"""

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, os.pardir)
SRC = os.path.join(ROOT, "源码")
RAW = os.path.join(ROOT, "原文")

PRE = r"""\documentclass[11pt,a4paper]{article}
\usepackage{xeCJK}
\usepackage{fontspec}
\usepackage{xcolor}
\usepackage{geometry}
\usepackage[protrusion=true]{microtype}
\geometry{margin=1.8cm,top=1.9cm}
\linespread{1.25}

\setmainfont{Baskerville}
\setCJKmainfont{Songti SC}

\definecolor{tipblue}{RGB}{0,95,160}
\definecolor{rulegray}{RGB}{190,190,190}

\setlength{\parindent}{0pt}
\setlength{\parskip}{0.35em}
\newcommand{\num}[1]{\makebox[1.9em][r]{#1.}\hspace{0.3em}}
\newcommand{\wline}{\noindent\rule{\linewidth}{0.4pt}}
% 中文题干：宋体粗体；提示词：蓝色小字；英文句子：Baskerville 正体
\newcommand{\prompt}[1]{\emph{\textcolor{tipblue}{\small（#1）}}}

\begin{document}
\pagestyle{plain}
"""

SPECIAL = {"#": "\\#", "%": "\\%", "&": "\\&", "_": "\\_",
           "$": "\\$", "{": "\\{", "}": "\\}", "~": "\\~{}", "^": "\\^{}"}


def esc(s: str) -> str:
    """原文里偶尔混进 LaTeX 特殊字符（如「(reliance)\\」），统一转义"""
    return "".join(SPECIAL.get(c, c) for c in (s or "").rstrip("\\"))


SEP = ("\\vspace{0.4em}\\noindent{\\color{rulegray}\\rule{\\textwidth}{0.6pt}}"
       "\\vspace{0.4em}")


def head(issue: str, sub: str, note: str, src: str, n: int, date: str) -> str:
    return f"""\\begin{{center}}
{{\\LARGE\\bfseries 上海高考高分翻译背诵 \\quad {issue}}}\\\\[0.25em]
{{\\large {src} \\quad\\ {sub}}}\\\\[0.35em]
{{\\footnotesize 来源：微信公众号「发现之旅 速来记单词」· {date} · 赵文瀚}}
\\end{{center}}

\\vspace{{0.4em}}
\\noindent\\begin{{tabular}}{{@{{}}p{{0.33\\textwidth}}@{{}}p{{0.34\\textwidth}}@{{}}p{{0.33\\textwidth}}@{{}}}}
姓名：\\underline{{\\hspace{{2.0cm}}}} & 日期：\\underline{{\\hspace{{2.0cm}}}} & 得分：\\underline{{\\hspace{{1.4cm}}}}\\,/\\enspace {n} \\\\
\\end{{tabular}}

\\vspace{{0.5em}}
\\noindent{{\\small {note}}}

\\vspace{{0.8em}}
"""


def build(data: dict) -> None:
    issue = data["issue"]
    items = data["items"]
    prov = data["proverb"]
    n = len(items) + (1 if prov else 0)
    # 标题里的来源段（如「26 二模」「24 一模」）与发布日期
    tail = data["title"].split(f"-{issue}-")[-1]
    src = f"{tail}　{data['date']}"

    # 1) 默写卷（中→英）
    b = []
    for it in items:
        hint = f"\\prompt{{{esc(it['hint'])}}}" if it.get("hint") else ""
        b.append(f"\\num{{{it['no']}}}\\textbf{{{esc(it['zh'])}}}{hint}")
        b.append("\\vspace{0.3em}")
        b.append("\\wline\\vspace{0.3em}\n\\wline")
    if prov:
        b.append(SEP)
        b.append(f"\\num{{{n}}}\\textbf{{谚语　{prov['zh']}}}")
        b.append("\\vspace{0.3em}")
        b.append("\\wline\\vspace{0.3em}\n\\wline")
    write(issue, "zh2en", head(issue, "默写（中 $\\to$ 英）",
                               "根据中文句子与提示词写出英文翻译，题号沿用原文。", src, n, data["date"]), b)

    # 2) 中英对照（答案）
    b = []
    for it in items:
        hint = f"\\prompt{{{esc(it['hint'])}}}" if it.get("hint") else ""
        b.append(f"\\num{{{it['no']}}}\\textbf{{{esc(it['zh'])}}}{hint}")
        b.append("\\vspace{0.15em}")
        b.append(f"\\noindent\\hangindent=2.2em\\hangafter=1\\hspace{{2.2em}}{esc(it['en'])}")
    if prov:
        b.append(SEP)
        b.append(f"\\num{{{n}}}\\textbf{{谚语}}\\quad {prov['en']}")
        b.append("\\vspace{0.15em}")
        b.append(f"\\noindent\\hangindent=2.2em\\hangafter=1\\hspace{{2.2em}}{prov['zh']}")
    write(issue, "ans", head(issue, "中英对照（背诵 · 答案）",
                             "中 $\\to$ 英默写卷的参考答案；亦可直接用于背诵与回译自查。", src, n, data["date"]), b)

    # 3) 回译卷（英→中）
    b = []
    for it in items:
        b.append(f"\\num{{{it['no']}}}{it['en']}")
        b.append("\\vspace{0.25em}")
        b.append("\\wline")
    if prov:
        b.append(SEP)
        b.append(f"\\num{{{n}}}\\textbf{{谚语}}\\quad {prov['en']}")
        b.append("\\vspace{0.25em}")
        b.append("\\wline")
    write(issue, "en2zh", head(issue, "回译（英 $\\to$ 中）",
                               "根据英文句子写出中文原句，题号沿用原文。", src, n, data["date"]), b)


def write(issue: str, kind: str, head_txt: str, blocks) -> None:
    os.makedirs(SRC, exist_ok=True)
    path = os.path.join(SRC, f"recitation_{issue}_{kind}.tex")
    with open(path, "w", encoding="utf-8") as f:
        f.write(PRE + head_txt + "\n\n".join(blocks) + "\n\n\\end{document}\n")
    print(f"  → 源码/recitation_{issue}_{kind}.tex")


def bundle(datas: list, name: str) -> None:
    """合册：多期合成一册，册内题号连续编号，每期前加小标题"""
    span = f"{datas[0]['issue']}–{datas[-1]['issue']}"
    src = f"{datas[0]['date']} 至 {datas[-1]['date']}"
    n = sum(len(d["items"]) + (1 if d.get("proverb") else 0) for d in datas)

    def issue_head(d: dict) -> str:
        tail = d["title"].split(f"-{d['issue']}-")[-1]
        return ("\\vspace{0.35em}\\noindent{\\large\\bfseries 第 " + str(d["issue"])
                + " 期　" + tail + "　{\\small " + d["date"] + "}}"
                + "\\vspace{0.15em}")

    def blocks(kind: str):
        b, no = [], 0
        for d in datas:
            b.append(issue_head(d))
            for it in d["items"]:
                no += 1
                hint = f"\\prompt{{{esc(it['hint'])}}}" if it.get("hint") else ""
                b.append("\\begin{minipage}{\\linewidth}")
                if kind == "en2zh":
                    b.append(f"\\num{{{no}}}{esc(it['en'])}")
                    b.append("\\vspace{0.25em}")
                    b.append("\\wline")
                else:
                    b.append(f"\\num{{{no}}}\\textbf{{{it['zh']}}}{hint}")
                    if kind == "ans":
                        b.append("\\vspace{0.15em}")
                        b.append(f"\\noindent\\hangindent=2.2em\\hangafter=1\\hspace{{2.2em}}{esc(it['en'])}")
                        for a in it.get("alt", []):
                            b.append(f"\\noindent\\hangindent=2.2em\\hangafter=1\\hspace{{2.2em}}{{\\small\\color{{tipblue}}另译：{esc(a)}}}")
                    else:
                        b.append("\\vspace{0.3em}")
                        b.append("\\wline\\vspace{0.3em}\n\\wline")
                b.append("\\end{minipage}")
            p = d.get("proverb")
            if p:
                no += 1
                if kind == "en2zh":
                    b.append(f"\\num{{{no}}}\\textbf{{谚语}}\\quad {p['en']}")
                    b.append("\\vspace{0.25em}")
                    b.append("\\wline")
                elif kind == "ans":
                    b.append(f"\\num{{{no}}}\\textbf{{谚语}}\\quad {p['en']}")
                    b.append("\\vspace{0.15em}")
                    b.append(f"\\noindent\\hangindent=2.2em\\hangafter=1\\hspace{{2.2em}}{esc(p['zh'])}")
                    if not p["en"]:
                        b.append("\\noindent\\hangindent=2.2em\\hangafter=1\\hspace{2.2em}{\\small\\color{tipblue}（原文未附英文，自行试译）}")
                else:
                    b.append(f"\\num{{{no}}}\\textbf{{谚语　{p['zh']}}}")
                    b.append("\\vspace{0.3em}")
                    b.append("\\wline\\vspace{0.3em}\n\\wline")
        return b

    write(name, "zh2en", head(f"合册 {span}", "默写（中 $\\to$ 英）",
                              "按中文句子与提示词写出英文翻译；题号在册内连续编号，每期以小标题分隔。", src, n, ""),
          blocks("zh2en"))
    write(name, "ans", head(f"合册 {span}", "中英对照（背诵 · 答案）",
                            "默写卷的参考答案；亦可直接用于背诵与回译自查。", src, n, ""),
          blocks("ans"))
    write(name, "en2zh", head(f"合册 {span}", "回译（英 $\\to$ 中）",
                              "根据英文句子写出中文原句；题号在册内连续编号。", src, n, ""),
          blocks("en2zh"))


def main() -> int:
    args = sys.argv[1:]
    size = 0
    if "--bundle" in args:
        i = args.index("--bundle")
        size = int(args[i + 1])
        del args[i:i + 2]
    want = args
    files = sorted(glob.glob(os.path.join(RAW, "*.json")))
    datas = [json.load(open(fp, encoding="utf-8")) for fp in files]
    datas = [d for d in datas if d.get("issue")]
    # 期号撞号：同一期号只保留日期较晚的一篇，其余跳过并提示（原文两种都留着）
    by_issue = {}
    for d in datas:
        k = int(d["issue"])
        if k not in by_issue or (d.get("date") or "") > (by_issue[k].get("date") or ""):
            if k in by_issue:
                print(f"  ⚠ 期号 {k} 撞号，保留 {d.get('date')}，跳过 {by_issue[k].get('date')}")
            by_issue[k] = d
    datas = [by_issue[k] for k in sorted(by_issue)]
    if want:
        datas = [d for d in datas if str(d["issue"]) in want]
    if size:
        for k in range(0, len(datas), size):
            chunk = datas[k:k + size]
            name = f"bundle_{int(chunk[0]['issue']):03d}_{int(chunk[-1]['issue']):03d}"
            print(f"== 合册 {name}（{len(chunk)} 期）")
            bundle(chunk, name)
        return 0
    for d in datas:
        print(f"== {d['issue']}: {d['title']}")
        build(d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
