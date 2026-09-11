# 英语单词默写表 —— 编译 Makefile
#
# 目录约定：
#   vocab_*.tex            中→英题目（含早期 vocab_01 专项）
#   en2cn/vocab_*.tex      英→中题目
#   ans/zh2en/vocab_*.tex  中→英参考答案
#   ans/en2cn/vocab_*.tex  英→中参考答案
#
# 常用命令：
#   make                 编译题目（197 份）
#   make ans             编译答案（196 份）
#   make zh2en / en2cn   只编某方向题目
#   make ans-zh2en / ans-en2cn  只编某方向答案
#   make letter L=A      只编 A 字母（两个方向）
#   make dist            编译并汇总到 dist/{zh2en,en2cn}/
#   make merge           合成两本题目合册
#   make merge-ans       合成两本答案合册
#   make check           校验每份均为 1 页
#   make clean           清理 LaTeX 临时文件
#   make distclean       清理临时文件与生成的 PDF

SHELL       := /bin/bash
LATEXMK     := latexmk
LATEXMKOPTS := -cd -xelatex -interaction=nonstopmode -halt-on-error -file-line-error
PDFUNITE    := pdfunite
PDFINFO     := pdfinfo
DIST        := dist

ZH_SRC   := $(sort $(wildcard vocab_*.tex))
E2C_SRC  := $(sort $(wildcard en2cn/*.tex))
ANSZH_SRC := $(sort $(wildcard ans/zh2en/*.tex))
ANSE2C_SRC := $(sort $(wildcard ans/en2cn/*.tex))
ZH_PDF   := $(ZH_SRC:.tex=.pdf)
E2C_PDF  := $(E2C_SRC:.tex=.pdf)
ANSZH_PDF := $(ANSZH_SRC:.tex=.pdf)
ANSE2C_PDF := $(ANSE2C_SRC:.tex=.pdf)
ALL_SRC  := $(ZH_SRC) $(E2C_SRC) $(ANSZH_SRC) $(ANSE2C_SRC)
ALL_PDF  := $(ZH_PDF) $(E2C_PDF) $(ANSZH_PDF) $(ANSE2C_PDF)

.PHONY: all zh2en en2cn ans ans-zh2en ans-en2cn letter dist merge merge-ans check clean distclean list help

all: $(ZH_PDF) $(E2C_PDF)

# ---- 编译规则 ----
%.pdf: %.tex
	@$(LATEXMK) $(LATEXMKOPTS) -silent $<

zh2en: $(ZH_PDF)
en2cn: $(E2C_PDF)
ans: $(ANSZH_PDF) $(ANSE2C_PDF)
ans-zh2en: $(ANSZH_PDF)
ans-en2cn: $(ANSE2C_PDF)

letter:
	@if [ -z "$(L)" ]; then echo "用法: make letter L=A"; exit 1; fi
	@echo ">> 编译字母 $(L)"
	@for f in $(wildcard vocab_$(L)_*.tex) $(wildcard en2cn/vocab_$(L)_*.tex); do \
		echo "   $$f"; \
		$(LATEXMK) $(LATEXMKOPTS) -silent "$$f" || exit 1; \
	done

# ---- 汇总 ----
dist: all ans
	@mkdir -p $(DIST)/zh2en $(DIST)/en2cn $(DIST)/ans-zh2en $(DIST)/ans-en2cn
	@cp $(ZH_PDF) $(DIST)/zh2en/
	@cp $(E2C_PDF) $(DIST)/en2cn/
	@cp $(ANSZH_PDF) $(DIST)/ans-zh2en/
	@cp $(ANSE2C_PDF) $(DIST)/ans-en2cn/
	@echo ">> 已汇总: 题目 $(words $(ZH_PDF))+$(words $(E2C_PDF)) 份, 答案 $(words $(ANSZH_PDF))+$(words $(ANSE2C_PDF)) 份 -> $(DIST)/"

# 合成整册（便于打印）
merge: all
	@mkdir -p $(DIST)
	@$(PDFUNITE) $(ZH_PDF)  "$(DIST)/默写表_中译英_全册.pdf"
	@$(PDFUNITE) $(E2C_PDF) "$(DIST)/默写表_英译中_全册.pdf"
	@for f in "$(DIST)/默写表_中译英_全册.pdf" "$(DIST)/默写表_英译中_全册.pdf"; do \
		echo ">> $$f  $$($(PDFINFO) "$$f" 2>/dev/null | awk '/^Pages/{print $$2}') 页"; \
	done

# 合成答案合册
merge-ans: ans
	@mkdir -p $(DIST)
	@$(PDFUNITE) $(ANSZH_PDF) "$(DIST)/参考答案_中译英_全册.pdf"
	@$(PDFUNITE) $(ANSE2C_PDF) "$(DIST)/参考答案_英译中_全册.pdf"
	@for f in "$(DIST)/参考答案_中译英_全册.pdf" "$(DIST)/参考答案_英译中_全册.pdf"; do \
		echo ">> $$f  $$($(PDFINFO) "$$f" 2>/dev/null | awk '/^Pages/{print $$2}') 页"; \
	done

# ---- 校验 ----
check: all
	@fail=0; n=0; \
	for f in $(ALL_PDF); do \
		n=$$((n+1)); \
		p=$$($(PDFINFO) "$$f" 2>/dev/null | awk '/^Pages/{print $$2}'); \
		if [ "$$p" != "1" ]; then echo "  ⚠ $$f: $$p 页"; fail=1; fi; \
	done; \
	if [ $$fail -eq 0 ]; then echo "✅ 全部 $$n 份均为 1 页"; else echo "❌ 存在非单页文件"; exit 1; fi

# ---- 清理 ----
clean:
	@$(LATEXMK) -c $(ALL_SRC) >/dev/null 2>&1 || true
	@rm -f *.aux *.log *.out *.toc *.fls *.fdb_latexmk *.synctex.gz *.xdv *.bbl *.blg
	@rm -f en2cn/*.aux en2cn/*.log en2cn/*.out en2cn/*.toc en2cn/*.fls en2cn/*.fdb_latexmk en2cn/*.synctex.gz en2cn/*.xdv
	@rm -f ans/zh2en/*.aux ans/zh2en/*.log ans/zh2en/*.out ans/zh2en/*.toc ans/zh2en/*.fls ans/zh2en/*.fdb_latexmk ans/zh2en/*.synctex.gz ans/zh2en/*.xdv
	@rm -f ans/en2cn/*.aux ans/en2cn/*.log ans/en2cn/*.out ans/en2cn/*.toc ans/en2cn/*.fls ans/en2cn/*.fdb_latexmk ans/en2cn/*.synctex.gz ans/en2cn/*.xdv
	@echo ">> 已清理 LaTeX 临时文件"

distclean: clean
	@rm -f $(ZH_PDF) $(E2C_PDF) $(ANSZH_PDF) $(ANSE2C_PDF)
	@rm -rf $(DIST)
	@echo ">> 已清理生成的 PDF 与 $(DIST)/"

# ---- 辅助 ----
list:
	@echo "题目 中→英: $(words $(ZH_PDF))   英→中: $(words $(E2C_PDF))"
	@echo "答案 中→英: $(words $(ANSZH_PDF))   英→中: $(words $(ANSE2C_PDF))"
	@echo "合计: $(words $(ALL_PDF)) 份"

help:
	@sed -n '2,17p' $(firstword $(MAKEFILE_LIST)) | sed 's/^# \{0,1\}//'
