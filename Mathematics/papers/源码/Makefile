# 高一数学试卷 —— 编译 Makefile
#
# 目录约定：
#   高一NN_学校_作业.tex    每套一份（题目 + 行内 \ans 答案 + 【解析】块）
#   common.sty              共享样式（试卷版/答案版/紧凑版三档开关）
#   ../试卷/                试卷版输出（仅题目，无答案）
#   ../答案/                答案版输出（题目 + 答案 + 解析）
#   ../试卷紧凑/            紧凑试卷版输出（与试卷版同内容，只去掉解答题作答区）
#
# 答案分离机制：common.sty 中 \newif\ifanswer，
#   试卷版 = 不定义 \isanswer；答案版 = 传入 \def\isanswer{1}。
#
# 常用命令：
#   make                    编译全部（试卷版 + 答案版；紧凑版请用 make compact）
#   make test               只编试卷版
#   make ans                只编答案版
#   make one F=高一02_大同中学_集合综合练习     只编某一套
#   make compact            编译全部（紧凑试卷版：去掉解答题作答区，压轴题换页保护保留）
#   make one-c F=高一02_大同中学_集合综合练习   只编某一套的紧凑版
#   make check              校验：试卷版/紧凑版不含答案，且紧凑版正文与试卷版一致
#   make docs               校验：README 里的「当前态计数」与源码/成品是否一致
#   make list               查看页数统计
#   make trace              生成「题目溯源」报告（溯源.tex → ../溯源/题目溯源.pdf）
#   make bundle             把 ../试卷紧凑/ 的成品合成一份合订打印本（40 份 / 91 页）
#   make clean              清理 LaTeX 临时文件
#   make distclean          清理临时文件与中间 PDF
#   make help               显示本帮助
#
# 溯源报告（与 42 份试卷分开的一条链）：内容来自 ../README.md 的「题目溯源」一节，
# 由 ../工具/README转tex.py 生成 溯源.tex（**不要手改 溯源.tex**——改内容改 README、
# 改排版改那个脚本）。溯源.tex 不匹配 高一*.tex 通配符，故 test/ans/compact/one 都不碰它。
# 编译后跑 ../工具/溯源比对.py 做两道校验，见该脚本头部。
#
# 编译时附带「缺字检查」：xelatex 对字体里没有的字形只报 Missing character 然后
# 静默丢弃该字符（PDF 里直接消失、不报错），故每条编完立即扫日志，命中就中止构建。
# 要新增符号（★ ℃ 生僻字等）时，先在 common.sty 里把它划入 CJK 字符类。

SHELL    := /bin/bash
XELATEX  := xelatex
OPTS     := -interaction=nonstopmode -halt-on-error -file-line-error
PDFINFO  := pdfinfo
PDTOTEXT := pdftotext

TOOLS     := ../工具
DEST_TEST := ../试卷
DEST_COMPACT := ../试卷紧凑
DEST_ANS  := ../答案
DEST_TRACE := ../溯源
TEX       := $(sort $(wildcard 高一*.tex))

# 缺字检查（test / ans / one 共用）：扫 $$LF.log，命中 Missing character 即中止。
# 调用前须把 LF 设成当前这套的名字（不含 .tex），如 LF=$$b。
# 写成单行是为了让 shell 所见与 make 展开一致（多行续行在变量里会被折叠）。
FONTCHK = miss=$$(grep -a 'Missing character' "$$LF.log" 2>/dev/null | sed 's/.*There is no //; s/ in font.*//' | sort -u | tr '\n' ' '); if [ -n "$$miss" ]; then printf '❌ %s 有字符没字形（PDF 里已静默消失）：%s\n' "$$LF" "$$miss"; printf '   处理：把该字符划入 CJK 字符类（见 common.sty 的 xeCJKDeclareCharClass）\n'; exit 1; fi

.PHONY: all test ans compact one one-c check docs trace bundle list clean distclean help

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

compact:
	@mkdir -p "$(DEST_COMPACT)"
	@n=0; for f in $(TEX); do \
		b=$${f%.tex}; LF=$$b; n=$$((n+1)); \
		printf '  紧凑版  %s\n' "$$b"; \
		$(XELATEX) $(OPTS) "\def\iscompact{1}\input{$$f}" >/dev/null || { echo "❌ $$b 编译失败"; exit 1; }; \
		$(FONTCHK); \
		cp "$$b.pdf" "$(DEST_COMPACT)/$${b}_试卷.pdf" || exit 1; \
		rm -f "$$b.pdf"; \
	done; \
	echo "✅ 紧凑版 $$n 份 -> $(DEST_COMPACT)/"

one-c:
	@if [ -z "$(F)" ]; then echo "用法: make one-c F=高一02_大同中学_集合综合练习"; exit 1; fi
	@test -f "$(F).tex" || { echo "无此文件: $(F).tex"; exit 1; }
	@mkdir -p "$(DEST_COMPACT)"
	@LF="$(F)"; $(XELATEX) $(OPTS) "\def\iscompact{1}\input{$(F).tex}" >/dev/null && $(FONTCHK) && cp "$(F).pdf" "$(DEST_COMPACT)/$(F)_试卷.pdf" || exit 1
	@rm -f "$(F).pdf"
	@echo "✅ $(F) 紧凑版已更新"

# 校验：试卷版/紧凑版必须 0 个答案标记，答案版必须 >0；且紧凑版正文与试卷版一致（忽略换行与页码）
check:
	@fail=0; \
	for f in "$(DEST_TEST)"/*_试卷.pdf; do \
		b=$$(basename "$$f" _试卷.pdf); \
		t=$$($(PDTOTEXT) "$$f" - 2>/dev/null | grep -c -e '【答案】' -e '【解析】' -e '参考答案'); \
		a=$$($(PDTOTEXT) "$(DEST_ANS)/$${b}_答案.pdf" - 2>/dev/null | grep -c -e '【答案】' -e '【解析】' -e '参考答案'); \
		c=$$($(PDTOTEXT) "$(DEST_COMPACT)/$${b}_试卷.pdf" - 2>/dev/null | grep -c -e '【答案】' -e '【解析】' -e '参考答案'); \
		s=$$(python3 "$(TOOLS)/正文指纹.py" "$$f" 2>/dev/null); \
		sc=$$(python3 "$(TOOLS)/正文指纹.py" "$(DEST_COMPACT)/$${b}_试卷.pdf" 2>/dev/null); \
		if [ "$$t" -ne 0 ] || [ "$$c" -ne 0 ] || [ "$$a" -eq 0 ] || [ "$$s" != "$$sc" ]; then \
			printf '  ⚠ %s —— 试卷泄漏=%s 紧凑泄漏=%s 答案标记=%s 正文一致=%s\n' "$$b" "$$t" "$$c" "$$a" "$$([ "$$s" = "$$sc" ] && echo 是 || echo 否)"; fail=1; \
		else \
			printf '  ✔ %s —— 试卷 0 / 紧凑 0 / 答案 %s\n' "$$b" "$$a"; \
		fi; \
	done; \
	if [ $$fail -eq 0 ]; then echo "✅ 全部试卷版与紧凑版均无答案泄漏，且紧凑版正文与试卷版逐字一致"; else echo "❌ 有问题，请检查"; exit 1; fi

# ===== 文档计数核对（独立一条链，不进 check）=====
# 核的是 README 与**源码**是否同步，与 check 的轴不同：check 读成品 PDF、管输出对不对
#（答案不泄漏、紧凑版与试卷版逐字一致），本目标解析 源码/高一*.tex 与成品份数/页数、
# 逐条比 README 里二十来处「当前态计数」。判据、为什么单列、以及「断言找不到即失败」的
# 设计都在 工具/计数核对.py 的文件头，改 README 措辞时务必同步改那边的正则。
docs:
	@python3 $(TOOLS)/计数核对.py

# ===== 溯源报告（独立一条链，不进 all：all 会把 42 份成品 PDF 全重写、污染 diff）=====
# 依赖 ../README.md：README 改了，make trace 会自动重新生成 溯源.tex 再编译。
溯源.tex: ../README.md ../工具/README转tex.py
	@python3 ../工具/README转tex.py

trace: 溯源.pdf
	@mkdir -p "$(DEST_TRACE)"
	@cp 溯源.pdf "$(DEST_TRACE)/题目溯源.pdf"
	@# 比对放在 cp 之后：它读的是成品 ../溯源/题目溯源.pdf（见该脚本头部）
	@python3 $(TOOLS)/溯源比对.py
	@echo "✅ 溯源报告 -> $(DEST_TRACE)/题目溯源.pdf"

溯源.pdf: 溯源.tex common.sty
	@# 两遍：第二遍才有目录与交叉引用。每遍都跑缺字检查（★▲⊕ 这些最容易静默丢）。
	@LF=溯源; $(XELATEX) $(OPTS) 溯源.tex >/dev/null && $(FONTCHK) || exit 1
	@LF=溯源; $(XELATEX) $(OPTS) 溯源.tex >/dev/null && $(FONTCHK) || exit 1
	@# 注意 $$( ) ：写 $( ) 会被 make 当成变量展开（踩过，打印出来是空的）
	@printf '  缺字 %s 处 / Overfull %s 处 / 页数 %s\n' \
	  "$$(grep -ac 'Missing character' 溯源.log)" \
	  "$$(grep -ac 'Overfull .hbox' 溯源.log)" \
	  "$$($(PDFINFO) 溯源.pdf | awk '/^Pages/{print $$2}')"

# ===== 合订打印本（独立一条链，不进 all：理由同 trace）=====
# 把 ../试卷紧凑/ 下的成品按文件名序合成一份 91 页的 PDF 便于打印。
# 目标写成 phony：合并只需不到一秒，每次重跑比维护依赖更稳妥（不会有陈旧产物）。
bundle:
	@test -n "$(sort $(wildcard $(DEST_COMPACT)/*_试卷.pdf))" \
	  || { echo "❌ $(DEST_COMPACT)/ 里还没有成品，先跑 make compact"; exit 1; }
	@python3 $(TOOLS)/合并试卷.py

list:
	@for f in "$(DEST_TEST)"/*_试卷.pdf; do \
		b=$$(basename "$$f" _试卷.pdf); \
		t=$$($(PDFINFO) "$$f" 2>/dev/null | awk '/^Pages/{print $$2}'); \
		c=$$($(PDFINFO) "$(DEST_COMPACT)/$${b}_试卷.pdf" 2>/dev/null | awk '/^Pages/{print $$2}'); \
		a=$$($(PDFINFO) "$(DEST_ANS)/$${b}_答案.pdf" 2>/dev/null | awk '/^Pages/{print $$2}'); \
		printf '  %s —— 试卷 %s 页 / 紧凑 %s 页 / 答案 %s 页\n' "$$b" "$$t" "$$c" "$$a"; \
	done

clean:
	@rm -f *.aux *.log *.out *.toc *.fls *.fdb_latexmk *.synctex.gz *.xdv
	@echo ">> 已清理 LaTeX 临时文件"

distclean: clean
	@rm -f *.pdf
	@echo ">> 已清理中间 PDF（$(DEST_TEST)/、$(DEST_COMPACT)/ 与 $(DEST_ANS)/ 中的成品未动）"

help:
	@sed -n '2,29p' $(firstword $(MAKEFILE_LIST)) | sed 's/^# \{0,1\}//'
