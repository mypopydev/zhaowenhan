# 试卷与答案 · 高一上数学

2026–2027 学年上海市部分市重点中学高一上**周练 / 周末作业**的 LaTeX 重排版。

原始材料来自微信公众号图文——试卷以 PNG 图片形式发布（无文字层），本目录内容已逐题 OCR
重排为可编辑的 XeLaTeX 源码，并**按「试卷 / 答案」分离输出**：
试卷版只有题目，答案版才含答案与解析。

## 目录结构

| 目录 | 内容 |
|------|------|
| `试卷/` | 试卷版 PDF，**仅题目、填空横线与解答题作答题区，不含任何答案**（8 份） |
| `答案/` | 答案版 PDF，题目 + 行内【答案】+ 逐题【解析】（8 份） |
| `源码/` | LaTeX 源码（8 份 `.tex` + 共享样式 `common.sty` + `Makefile`） |
| `原图/` | 微信公众号原卷图片，按页序命名（`01.png`、`02.png`…），用于溯源（58 张） |

## 试卷清单

全部 8 套的知识范围均为**集合与常用逻辑用语**（高一上第一章）。
系列号取自原文标题（收集系列目前缺 高一01）。

| 系列 | 学校 | 作业 | 页数 试卷/答案 | 原图 | 原文 |
|------|------|------|:---:|:---:|------|
| 高一02 | 大同中学 | 集合综合练习 | 3 / 5 | 8 | [链接](https://mp.weixin.qq.com/s/NvdeYz6-8KgQfImrs40L_Q) |
| 高一03 | 格致中学 | 周末作业1 | 3 / 4 | 6 | [链接](https://mp.weixin.qq.com/s/fLqIJLEGpTq0-I5CoLrd_g) |
| 高一04 | 位育中学 | 周末作业1 | 2 / 2 | 3 | [链接](https://mp.weixin.qq.com/s/sTXEEcN_lpv5jmpGgmfMVQ) |
| 高一05 | 七宝中学 | 周末作业9.5 | 4 / 5 | 9 | [链接](https://mp.weixin.qq.com/s/UY9w_gk3iw9gyu0GRXbE3A) |
| 高一06 | 延安中学 | 周末作业1 | 2 / 3 | 4 | [链接](https://mp.weixin.qq.com/s/cnFq_79rKIUShDp0SzWEkw) |
| 高一07 | 交附闵行 | 周练1 | 4 / 6 | 11 | [链接](https://mp.weixin.qq.com/s/jfnfEjbjjJy8Uw48nMQB1A) |
| 高一08 | 七宝中学 | 周末作业1 | 4 / 5 | 9 | [链接](https://mp.weixin.qq.com/s/eojQb4OGTGHJyrnP3_3mww) |
| 高一09 | 进才中学 | 周末作业1 | 4 / 5 | 8 | [链接](https://mp.weixin.qq.com/s/65D0HFe1t_SzD3S1PGfyLg) |

合计 16 份 PDF、58 张原图。

## 答案与试卷如何分离

`源码/common.sty` 里用一个条件开关控制答案内容的显隐：

```latex
\newif\ifanswer
\ifdefined\isanswer\answertrue\fi
\newcommand{\ans}[1]{\ifanswer\textbf{【答案】}#1\fi}
```

- **试卷版**：不传入 `\isanswer`，`\ans{}` 及其后的【解析】块整段不输出。
- **答案版**：编译时传入 `\def\isanswer{1}`，答案与解析正常渲染。

题目本身在两种版本中完全一致，因此答案版也同时是一份"带解析的讲解稿"。

## 编译方式

在 `源码/` 目录（或 `papers/` 目录）下执行：

```bash
make            # 编译全部：试卷版 -> ../试卷/，答案版 -> ../答案/
make test       # 只编试卷版
make ans        # 只编答案版
make one F=高一02_大同中学_集合综合练习    # 只编某一套
make check      # 校验试卷版确实不含答案（逐份文本比对）
make list       # 查看页数统计
make clean      # 清理 LaTeX 临时文件
```

需 `xelatex`（TeX Live / MacTeX 均可）、`pdfinfo` 与 `pdftotext`（poppler）。
`make check` 会抽取两版 PDF 的文本，确认试卷版中【答案】【解析】标记数为 0、答案版大于 0。

## 说明

- 原卷为微信公众号图片，答案以原卷给出的版本为准，未擅自改动。
- 试卷中出现的插图直接取自原卷截图（如格致中学第 4 题的 Venn 图，`源码/figures/`），
  **不用 TikZ 重绘**，以保证与原卷完全一致。
- **解答题作答题区**：OCR 重排会丢掉原卷给解答题留的书写空间，故由 `\ansspace[n]` 按题量
  重新留白（2 小问约 5–6 行、3 小问约 7–8 行、含证明/压轴 8–10 行、5 小问 10–12 行，行高 1.2cm）。
  留白只在**试卷版**输出，答案版版式与页数完全不受影响。
