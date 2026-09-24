# 英语错题 / 默写 —— 编译 Makefile
#
# 目录约定（mistakes/）：
#   vocab_NN_<范围>_01.tex              错词订正表            —— 2 页
#   vocab_NN_<范围>_01_recheck_*.tex     二刷卷 中→英 / 英→中 / 答案 —— 各 1 页
#   vocab_NN_<范围>_01_原卷*.jpg         原卷扫描件（归档，不参与编译）
#   tense_voice_01.tex                  时态语态错题重做      —— 3 页
#
# 常用命令：
#   make                编译全部 tex → pdf
#   make check          校验：无 Overfull／Underfull／Missing character，且页数符合预期
#   make docs           自检：README 关于本目录的声明 ↔ 实际文件/页数/元数据（计数核对.py）
#   make clean          清理 LaTeX 中间文件
#   make distclean      清理中间文件与生成的 PDF
#   make list / help    查看清单 / 用法
#
# 可复现构建：编译时由 Makefile 做两件事 —— ① 以源文件 mtime 作为 SOURCE_DATE_EPOCH
# 传给 TeX Live（固定 PDF 的 /ID），② 用 -usepretex 注入 docinfo special，覆盖 XeTeX
# 默认写入的「编译时刻」（/Creator 精确到分、不归 SOURCE_DATE_EPOCH 管）并把
# /CreationDate 定为源文件日期。源码不变时重编得到逐字节相同的 PDF，
# 因此「重编一遍」不会在 git 里产生无意义的二进制 diff。

SHELL       := /bin/bash
LATEXMK     := latexmk
LATEXMKOPTS := -cd -xelatex -interaction=nonstopmode -halt-on-error -file-line-error -silent
PDFINFO     := pdfinfo

TEX := $(sort $(wildcard *.tex))
PDF := $(TEX:.tex=.pdf)
# 二刷卷（1 页）与其余（订正表 2 页 / tense_voice_01 3 页）
RECHECK := $(filter %_recheck_zh2en.pdf %_recheck_en2cn.pdf %_recheck_ans.pdf,$(PDF))
MAIN    := $(filter-out $(RECHECK),$(PDF))

.PHONY: all check docs clean distclean list help

all: $(PDF)

# ---- 编译规则（可复现）----
#  1) SOURCE_DATE_EPOCH = 源文件 mtime → 固定 PDF 的 /ID
#  2) -usepretex 注入 docinfo special → 覆盖 XeTeX 默认写入的编译时刻
#     （/Creator 是精确到分的墙钟时间，不归 SOURCE_DATE_EPOCH 管），
#     并把 /CreationDate 固定为源文件日期
%.pdf: %.tex
	@ep=$$(stat -f %m "$<" 2>/dev/null || stat -c %Y "$<"); \
	d=$$(date -u -r "$$ep" +%Y%m%d%H%M%SZ 2>/dev/null || date -u -d "@$$ep" +%Y%m%d%H%M%SZ); \
	printf '>> %s\n' "$<"; \
	SOURCE_DATE_EPOCH=$$ep $(LATEXMK) $(LATEXMKOPTS) \
		-usepretex="\\special{pdf:docinfo<</Creator(English/mistakes)/Producer(xdvipdfmx)/CreationDate(D:$$d)>>}" "$<"

# ---- 校验 ----
check: all
	@fail=0; n=0; \
	for f in $(PDF); do \
		n=$$((n+1)); \
		log="$${f%.pdf}.log"; \
		p=$$($(PDFINFO) "$$f" 2>/dev/null | awk '/^Pages/{print $$2}'); \
		if [[ "$$f" == *_recheck_* ]]; then want=1; \
		elif [[ "$$f" == "tense_voice_01.pdf" ]]; then want=3; \
		else want=2; fi; \
		bad=$$(grep -cE 'Overfull|Underfull|Missing character' "$$log" 2>/dev/null); \
		if [ "$$p" != "$$want" ] || [ "$$bad" != "0" ]; then \
			echo "  ⚠ $$f: $$p 页（应 $$want 页）、日志问题 $$bad 处"; fail=1; \
		else \
			printf '  ✓ %-46s %s 页  0 警告\n' "$$f" "$$p"; \
		fi; \
	done; \
	if [ $$fail -eq 0 ]; then echo "✅ 全部 $$n 份通过（页数与日志均符合预期）"; else echo "❌ 存在不符合预期的文件"; exit 1; fi

# ---- 文档自查（README 声明 ↔ 实际）----
docs: all
	@python3 计数核对.py

# ---- 清理 ----
clean:
	@rm -f *.aux *.log *.out *.toc *.lof *.lot *.fls *.fdb_latexmk *.synctex.gz *.xdv
	@echo ">> 已清理 LaTeX 临时文件"

distclean: clean
	@rm -f $(PDF)
	@echo ">> 已清理生成的 PDF"

# ---- 辅助 ----
list:
	@echo "订正表 $(words $(MAIN)) 份 / 二刷卷 $(words $(RECHECK)) 份，合计 $(words $(PDF)) 份"
	@echo "另含原卷扫描件 $$(ls -1 *原卷*.jpg *原卷*.pdf 2>/dev/null | wc -l | tr -d ' ') 个（不参与编译）"
	@printf '%s\n' $(PDF) | sed 's/^/  /'

help:
	@sed -n '2,26p' $(firstword $(MAKEFILE_LIST)) | sed 's/^# \{0,1\}//'
