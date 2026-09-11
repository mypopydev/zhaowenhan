# 英语单词默写表 —— 编译 Makefile
#
# 目录约定：
#   vocab_*.tex          中→英（含早期 vocab_01 专项）
#   en2cn/vocab_*.tex    英→中
#
# 常用命令：
#   make                 编译全部（197 份）
#   make zh2en           只编中→英（99 份）
#   make en2cn           只编英→中（98 份）
#   make letter L=A      只编 A 字母（两个方向）
#   make dist            编译并汇总到 dist/{zh2en,en2cn}/
#   make merge           编译并合成两本整册 PDF
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
ZH_PDF   := $(ZH_SRC:.tex=.pdf)
E2C_PDF  := $(E2C_SRC:.tex=.pdf)
ALL_SRC  := $(ZH_SRC) $(E2C_SRC)
ALL_PDF  := $(ZH_PDF) $(E2C_PDF)

.PHONY: all zh2en en2cn letter dist merge check clean distclean list help

all: $(ALL_PDF)

# ---- 编译规则 ----
%.pdf: %.tex
	@$(LATEXMK) $(LATEXMKOPTS) -silent $<

zh2en: $(ZH_PDF)
en2cn: $(E2C_PDF)

letter:
	@if [ -z "$(L)" ]; then echo "用法: make letter L=A"; exit 1; fi
	@echo ">> 编译字母 $(L)"
	@for f in $(wildcard vocab_$(L)_*.tex) $(wildcard en2cn/vocab_$(L)_*.tex); do \
		echo "   $$f"; \
		$(LATEXMK) $(LATEXMKOPTS) -silent "$$f" || exit 1; \
	done

# ---- 汇总 ----
dist: all
	@mkdir -p $(DIST)/zh2en $(DIST)/en2cn
	@cp $(ZH_PDF) $(DIST)/zh2en/
	@cp $(E2C_PDF) $(DIST)/en2cn/
	@echo ">> 已汇总: $(words $(ZH_PDF)) 份 -> $(DIST)/zh2en/ ; $(words $(E2C_PDF)) 份 -> $(DIST)/en2cn/"

# 合成整册（便于打印）
merge: all
	@mkdir -p $(DIST)
	@$(PDFUNITE) $(ZH_PDF)  "$(DIST)/默写表_中译英_全册.pdf"
	@$(PDFUNITE) $(E2C_PDF) "$(DIST)/默写表_英译中_全册.pdf"
	@for f in "$(DIST)/默写表_中译英_全册.pdf" "$(DIST)/默写表_英译中_全册.pdf"; do \
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
	@echo ">> 已清理 LaTeX 临时文件"

distclean: clean
	@rm -f $(ALL_PDF)
	@rm -rf $(DIST)
	@echo ">> 已清理生成的 PDF 与 $(DIST)/"

# ---- 辅助 ----
list:
	@echo "中→英: $(words $(ZH_PDF)) 份"; echo "英→中: $(words $(E2C_PDF)) 份"; echo "合计: $(words $(ALL_PDF)) 份"

help:
	@sed -n '2,17p' $(firstword $(MAKEFILE_LIST)) | sed 's/^# \{0,1\}//'
