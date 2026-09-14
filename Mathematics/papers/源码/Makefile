# 高一数学试卷 —— 编译 Makefile
#
# 目录约定：
#   高一NN_学校_作业.tex    每套一份（题目 + 行内 \ans 答案 + 【解析】块）
#   common.sty              共享样式（试卷版/答案版开关）
#   ../试卷/                试卷版输出（仅题目，无答案）
#   ../答案/                答案版输出（题目 + 答案 + 解析）
#
# 答案分离机制：common.sty 中 \newif\ifanswer，
#   试卷版 = 不定义 \isanswer；答案版 = 传入 \def\isanswer{1}。
#
# 常用命令：
#   make                    编译全部（试卷版 + 答案版）
#   make test               只编试卷版
#   make ans                只编答案版
#   make one F=高一02_大同中学_集合综合练习     只编某一套
#   make check              校验试卷版是否真的不含答案
#   make list               查看页数统计
#   make clean              清理 LaTeX 临时文件
#   make distclean          清理临时文件与中间 PDF
#   make help               显示本帮助
#
# 编译时附带「缺字检查」：xelatex 对字体里没有的字形只报 Missing character 然后
# 静默丢弃该字符（PDF 里直接消失、不报错），故每条编完立即扫日志，命中就中止构建。
# 要新增符号（★ ℃ 生僻字等）时，先在 common.sty 里把它划入 CJK 字符类。

SHELL    := /bin/bash
XELATEX  := xelatex
OPTS     := -interaction=nonstopmode -halt-on-error -file-line-error
PDFINFO  := pdfinfo
PDTOTEXT := pdftotext

DEST_TEST := ../试卷
DEST_ANS  := ../答案
TEX       := $(sort $(wildcard 高一*.tex))

# 缺字检查（test / ans / one 共用）：扫 $$LF.log，命中 Missing character 即中止。
# 调用前须把 LF 设成当前这套的名字（不含 .tex），如 LF=$$b。
# 写成单行是为了让 shell 所见与 make 展开一致（多行续行在变量里会被折叠）。
FONTCHK = miss=$$(grep -a 'Missing character' "$$LF.log" 2>/dev/null | sed 's/.*There is no //; s/ in font.*//' | sort -u | tr '\n' ' '); if [ -n "$$miss" ]; then printf '❌ %s 有字符没字形（PDF 里已静默消失）：%s\n' "$$LF" "$$miss"; printf '   处理：把该字符划入 CJK 字符类（见 common.sty 的 xeCJKDeclareCharClass）\n'; exit 1; fi

.PHONY: all test ans one check list clean distclean help

all: test ans

test:
	@mkdir -p "$(DEST_TEST)"
	@n=0; for f in $(TEX); do \
		b=$${f%.tex}; LF=$$b; n=$$((n+1)); \
		printf '  试卷版  %s\n' "$$b"; \
		$(XELATEX) $(OPTS) "$$f" >/dev/null || { echo "❌ $$b 编译失败"; exit 1; }; \
		$(FONTCHK); \
		cp "$$b.pdf" "$(DEST_TEST)/$${b}_试卷.pdf" || exit 1; \
		rm -f "$$b.pdf"; \
	done; \
	echo "✅ 试卷版 $$n 份 -> $(DEST_TEST)/"

ans:
	@mkdir -p "$(DEST_ANS)"
	@n=0; for f in $(TEX); do \
		b=$${f%.tex}; LF=$$b; n=$$((n+1)); \
		printf '  答案版  %s\n' "$$b"; \
		$(XELATEX) $(OPTS) "\def\isanswer{1}\input{$$f}" >/dev/null || { echo "❌ $$b 编译失败"; exit 1; }; \
		$(FONTCHK); \
		cp "$$b.pdf" "$(DEST_ANS)/$${b}_答案.pdf" || exit 1; \
		rm -f "$$b.pdf"; \
	done; \
	echo "✅ 答案版 $$n 份 -> $(DEST_ANS)/"

one:
	@if [ -z "$(F)" ]; then echo "用法: make one F=高一02_大同中学_集合综合练习"; exit 1; fi
	@test -f "$(F).tex" || { echo "无此文件: $(F).tex"; exit 1; }
	@LF="$(F)"; $(XELATEX) $(OPTS) "$(F).tex" >/dev/null && $(FONTCHK) && cp "$(F).pdf" "$(DEST_TEST)/$(F)_试卷.pdf" || exit 1
	@LF="$(F)"; $(XELATEX) $(OPTS) "\def\isanswer{1}\input{$(F).tex}" >/dev/null && $(FONTCHK) && cp "$(F).pdf" "$(DEST_ANS)/$(F)_答案.pdf" || exit 1
	@rm -f "$(F).pdf"
	@echo "✅ $(F) 两版已更新"

# 校验：试卷版必须 0 个答案标记，答案版必须 >0
check:
	@fail=0; \
	for f in "$(DEST_TEST)"/*_试卷.pdf; do \
		b=$$(basename "$$f" _试卷.pdf); \
		t=$$($(PDTOTEXT) "$$f" - 2>/dev/null | grep -c -e '【答案】' -e '【解析】' -e '参考答案'); \
		a=$$($(PDTOTEXT) "$(DEST_ANS)/$${b}_答案.pdf" - 2>/dev/null | grep -c -e '【答案】' -e '【解析】' -e '参考答案'); \
		if [ "$$t" -ne 0 ] || [ "$$a" -eq 0 ]; then \
			printf '  ⚠ %s —— 试卷泄漏=%s  答案标记=%s\n' "$$b" "$$t" "$$a"; fail=1; \
		else \
			printf '  ✔ %s —— 试卷 0 / 答案 %s\n' "$$b" "$$a"; \
		fi; \
	done; \
	if [ $$fail -eq 0 ]; then echo "✅ 全部试卷版均无答案泄漏"; else echo "❌ 存在泄漏，请检查源码 \\ifanswer 包裹"; exit 1; fi

list:
	@for f in "$(DEST_TEST)"/*_试卷.pdf; do \
		b=$$(basename "$$f" _试卷.pdf); \
		t=$$($(PDFINFO) "$$f" 2>/dev/null | awk '/^Pages/{print $$2}'); \
		a=$$($(PDFINFO) "$(DEST_ANS)/$${b}_答案.pdf" 2>/dev/null | awk '/^Pages/{print $$2}'); \
		printf '  %s —— 试卷 %s 页 / 答案 %s 页\n' "$$b" "$$t" "$$a"; \
	done

clean:
	@rm -f *.aux *.log *.out *.toc *.fls *.fdb_latexmk *.synctex.gz *.xdv
	@echo ">> 已清理 LaTeX 临时文件"

distclean: clean
	@rm -f *.pdf
	@echo ">> 已清理中间 PDF（$(DEST_TEST)/ 与 $(DEST_ANS)/ 中的成品未动）"

help:
	@sed -n '2,25p' $(firstword $(MAKEFILE_LIST)) | sed 's/^# \{0,1\}//'
