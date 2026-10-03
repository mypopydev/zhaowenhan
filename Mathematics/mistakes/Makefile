# 数学错题集 —— 编译 Makefile
#
# 目录约定（Mathematics/mistakes/）：
#   赵文瀚-数学错题集N-YYYYMMDD.tex      错题集（题目 + 来源 + 手写填空栏）
#   赵文瀚-数学错题集N-YYYYMMDD_原卷.pdf  源 PDF 归档（微信导出的原样副本，**不参与编译**）
#   ../papers/源码/common.sty             共享样式（以相对路径复用，勿在本目录另写 style）
#   ../papers/源码/figures/*.png          复用插图（如 venn_AB_complement.png）
#
# 常用命令：
#   make            编译 tex → pdf
#   make check      校验：缺字 0 / 题数 16 / 无答案泄漏 / 页数（回填后）
#   make clean      清理 LaTeX 中间文件
#   make distclean  清理中间文件与生成的 PDF
#   make list       查看产物与页数
#   make help       显示本帮助
#
# 可复现构建：① 以源文件 mtime 作 SOURCE_DATE_EPOCH（固定 PDF 的 /ID）；
# ② -usepretex 注入 docinfo special，覆盖 XeTeX 默认写入的编译时刻（/Creator 精确到分、
# 不归 SOURCE_DATE_EPOCH 管）并把 /CreationDate 定为源文件日期。源码不变时重编得到
# 逐字节相同的 PDF，因此“重编一遍”不会在 git 里产生无意义的二进制 diff。
#
# 注意：`-cd` 让 latexmk 把 CWD 切到本目录，.tex 里的相对路径 `../papers/源码/…`
# 才是相对本目录解析（从别处直接跑 xelatex 会解析错）。

SHELL       := /bin/bash
LATEXMK     := latexmk
LATEXMKOPTS := -cd -xelatex -interaction=nonstopmode -halt-on-error -file-line-error -silent
PDFINFO     := pdfinfo
PDTOTEXT    := pdftotext

TEX := $(sort $(wildcard *.tex))
PDF := $(TEX:.tex=.pdf)
LOG := $(PDF:.pdf=.log)

# 每题末尾一个“我的错答”填空栏 → 栏数即题数
WANT_ITEMS := 16
# 期望页数：首次 `make` 后按实际页数回填
WANT_PAGES := 4
# ⚠ 这两个期望值（以及 check 的判据）现在按**单份错题集**写死：本目录若添第二份、而它的题数或
#   页数与这份不同，check 会误报。届时改成“按份”的表（以文件名为键）。两个值任一个为 0 时
#   该项检查跳过（页数早已如此，题数同理）。

.PHONY: all check clean distclean list help

all: $(PDF)

# ---- 编译规则（可复现）----
%.pdf: %.tex ../papers/源码/common.sty
	@ep=$$(stat -f %m "$<" 2>/dev/null || stat -c %Y "$<"); \
	d=$$(date -u -r "$$ep" +%Y%m%d%H%M%SZ 2>/dev/null || date -u -d "@$$ep" +%Y%m%d%H%M%SZ); \
	printf '>> %s\n' "$<"; \
	SOURCE_DATE_EPOCH=$$ep $(LATEXMK) $(LATEXMKOPTS) \
		-usepretex="\\special{pdf:docinfo<</Creator(Mathematics/mistakes)/Producer(xdvipdfmx)/CreationDate(D:$$d)>>}" "$<"

# 日志缺失时按需重建该份（-B 只作用于这一份；可复现构建保证 PDF 字节不变）
$(LOG): %.log: %.tex
	@$(MAKE) --no-print-directory -B $(@:.log=.pdf) >/dev/null 2>&1

# ---- 校验 ----
#   缺字（Missing character）致命——xelatex 对无字形字符是静默丢弃；
#   题数 / 答案泄漏 / 页数同样致命；Overfull、Underfull 只报数（字段栏与长题干易过宽）。
check: all $(LOG)
	@fail=0; \
	for f in $(PDF); do \
		log="$${f%.pdf}.log"; \
		p=$$($(PDFINFO) "$$f" 2>/dev/null | awk '/^Pages/{print $$2}'); \
		miss=$$(grep -a -c 'Missing character' "$$log" 2>/dev/null); \
		nq=$$($(PDTOTEXT) "$$f" - 2>/dev/null | grep -c '我的错答'); \
		na=$$($(PDTOTEXT) "$$f" - 2>/dev/null | grep -c -e '【答案】' -e '【解析】' -e '参考答案'); \
		of=$$(grep -a -c 'Overfull' "$$log" 2>/dev/null); \
		uf=$$(grep -a -c 'Underfull' "$$log" 2>/dev/null); \
		[ "$$miss" = "0" ] || { printf '  ❌ %s 缺字 %s 处（PDF 里已静默消失）\n' "$$f" "$$miss"; fail=1; }; \
		[ "$$na" = "0" ] || { printf '  ❌ %s 疑似答案泄漏 %s 处\n' "$$f" "$$na"; fail=1; }; \
		if [ "$(WANT_ITEMS)" != "0" ] && [ "$$nq" != "$(WANT_ITEMS)" ]; then \
			printf '  ❌ %s 题数 %s，应为 %s\n' "$$f" "$$nq" "$(WANT_ITEMS)"; fail=1; fi; \
		if [ "$(WANT_PAGES)" != "0" ] && [ "$$p" != "$(WANT_PAGES)" ]; then \
			printf '  ❌ %s 页数 %s，应为 %s\n' "$$f" "$$p" "$(WANT_PAGES)"; fail=1; fi; \
		printf '  %s：%s 页 / 题数 %s / 缺字 %s / 答案泄漏 %s / Overfull %s / Underfull %s\n' \
			"$$f" "$$p" "$$nq" "$$miss" "$$na" "$$of" "$$uf"; \
	done; \
	if [ $$fail -eq 0 ]; then printf '✅ 全部通过（缺字 0 / 无答案泄漏 / 题数 %s）\n' "$(WANT_ITEMS)"; \
	else echo "❌ 有不符合预期项"; exit 1; fi

# ---- 清理 ----
clean:
	@rm -f *.aux *.log *.out *.toc *.lof *.lot *.fls *.fdb_latexmk *.synctex.gz *.xdv
	@echo ">> 已清理 LaTeX 临时文件"

distclean: clean
	@rm -f $(PDF)
	@echo ">> 已清理生成的 PDF"

# ---- 辅助 ----
list:
	@for f in $(PDF); do \
		printf '  %s —— %s 页\n' "$$f" "$$($(PDFINFO) "$$f" 2>/dev/null | awk '/^Pages/{print $$2}')"; \
	done
	@printf '%s\n' $(TEX) | sed 's/^/  源：/'
	@printf '  另含原卷归档 %s 个（不参与编译）\n' "$$(ls -1 *_原卷*.pdf 2>/dev/null | wc -l | tr -d ' ')"

help:
	@awk 'NR>1 && /^#/ {sub(/^# ?/,""); print; next} NR>1 {exit}' $(firstword $(MAKEFILE_LIST))
