# 英语 (English)

## 本目录用途
收录日常练习/考试中的错题与对应薄弱知识点，用于复盘与针对性复习。

## 内容结构
- `mistakes/`   错题条目。现有词汇默写三套（订正表 + 二刷卷 + 原卷扫描件，按 `vocab_01_a_advanced_01`／`vocab_02_advantage_am_01`／`vocab_03_anyhow_assure_01` 编号）与短语默写一套（同构，按 `phrase_01_p11_20_01` 编号，小蓝短语 P11-20，25 条）；这两类每套含订正表 2 页、二刷卷 中→英／英→中／答案 各 1 页。另有两套语法专项：`grammar_01_tense_voice_01`（国庆动词时态语态 35 题选择；订正表 2 页 + 重做卷（`_recheck_q`）／答案与解析（`_recheck_ans`）各 2 页）与 `grammar_02_tense_voice_fill_01`（智学网错题本「时态语态练习1」18 空填空；订正表 2 页 + 重做卷／答案与解析各 1 页）。另含早期时态语态错题重做。编译见 `mistakes/Makefile`（下节）
- `weakpoints/` 薄弱知识点汇总（从错题提炼）
- `review/`     复习计划与复盘记录
- `vocabulary/` 英语单词默写表（LaTeX 重排，按 A–Z 字母分档 + `extra/` 早期 A-advanced 专项，中译英 / 英译中题目 198 份 + 答案 198 份，题目与答案分离，见 `vocabulary/Makefile`）
- `refs/`       参考资料（课程标准等大型 PDF，不入库）

## 单条错题建议字段
- 日期、来源（作业/月考/模拟/高考真题）
- 题目（可附文本或截图）
- 我的错答 / 正确答案
- 错误原因（词汇/语法/理解偏差/写作表达）
- 关联知识点标签
- 掌握程度（0–5）

## 知识模块（便于打标签）
词汇、语法、阅读理解、完形填空、语法填空、应用文、读后续写、听力

## 编译方式（`mistakes/`）

```bash
cd mistakes
make            # 编译全部 23 份 tex → pdf
make check      # 校验：页数符合预期（订正表 2 页 / 二刷卷 1 页（grammar_01 的重做与答案卷 2 页）/ 时态语态 3 页）、日志 0 处 Overfull／Missing character
make docs       # 自检：README 声明 ↔ 实际文件/页数/PDF 元数据（计数核对.py）
make clean      # 清理 LaTeX 临时文件
make distclean  # 清理临时文件与生成的 PDF（原卷扫描件不动，它没有对应 .tex）
make list       # 查看清单（订正表 / 二刷卷份数、原卷件数）
make help       # 显示上面这份说明
```

**可复现构建**：源码不变时重编得到**逐字节相同**的 PDF，所以在 git 里「重编一遍」不会
产生无意义的二进制 diff。编译时由 Makefile 做两件事：

1. 以源文件 mtime 作为 `SOURCE_DATE_EPOCH` 传给 TeX Live——固定 PDF 的 `/ID`；
2. 用 `latexmk -usepretex` 注入 docinfo special，覆盖 `/Creator`、`/Producer`、`/CreationDate`
   ——XeTeX 默认会把**编译时刻（精确到分）**写进 `/Creator`，这一项不归 `SOURCE_DATE_EPOCH` 管，
   不覆盖就做不到可复现。

实测：连续两轮 `make distclean && make`，23 份 PDF 的 md5 逐一相同，且 `git status` 保持干净。

`vocabulary/` 的编译方式见 `vocabulary/Makefile`（`make` 题目 / `make ans` 答案 / `make dist` 汇总 / `make merge` 合册 / `make check` 校验）。
