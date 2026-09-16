# 英语单词默写表 —— 编译 Makefile
#
# 目录约定（按字母组织，L = A…Z）：
#   L/zh2en_NN.tex        中→英题目
#   L/en2cn_NN.tex        英→中题目
#   L/ans_zh2en_NN.tex    中→英参考答案
#   L/ans_en2cn_NN.tex    英→中参考答案
#   extra/zh2en_01.tex    早期 A-advanced 专项题目
#   extra/ans_zh2en_01.tex   早期 A-advanced 专项参考答案
#
# 常用命令：
#   make                 编译题目（197 份）
#   make ans             编译答案（197 份）
#   make zh2en / en2cn              只编某方向题目
#   make ans-zh2en / ans-en2cn      只编某方向答案
#   make letter L=S      只编 S 字母（题目+答案）
#   make dist            汇总到 dist/（保留字母子目录）
#   make merge           合成两本题目合册
#   make merge-ans       合成两本答案合册
#   make check           校验每份均为 1 页
#   make clean           清理 LaTeX 临时文件
#   make distclean       清理临时文件与生成的 PDF
#   make list / help     查看统计 / 用法

SHELL       := /bin/bash
LATEXMK     := latexmk
LATEXMKOPTS := -cd -xelatex -interaction=nonstopmode -halt-on-error -file-line-error
PDFUNITE    := pdfunite
PDFINFO     := pdfinfo
DIST        := dist
DIRS        := A B C D E F G H I J K L M N O P Q R S T U V W X Y Z extra

ZH_SRC     := $(sort $(wildcard [A-Z]/zh2en_*.tex) $(wildcard extra/zh2en_*.tex))
E2C_SRC    := $(sort $(wildcard [A-Z]/en2cn_*.tex))
ANSZH_SRC  := $(sort $(wildcard [A-Z]/ans_zh2en_*.tex) $(wildcard extra/ans_zh2en_*.tex))
ANSE2C_SRC := $(sort $(wildcard [A-Z]/ans_en2cn_*.tex))
ZH_PDF     := $(ZH_SRC:.tex=.pdf)
E2C_PDF    := $(E2C_SRC:.tex=.pdf)
ANSZH_PDF  := $(ANSZH_SRC:.tex=.pdf)
ANSE2C_PDF := $(ANSE2C_SRC:.tex=.pdf)
ALL_PDF    := $(ZH_PDF) $(E2C_PDF) $(ANSZH_PDF) $(ANSE2C_PDF)

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
	@test -d "$(L)" || { echo "无目录: $(L)"; exit 1; }
	@echo ">> 编译字母 $(L)"
	@for f in $(sort $(wildcard $(L)/*.tex)); do \
		echo "   $$f"; \
		$(LATEXMK) $(LATEXMKOPTS) -silent "$$f" || exit 1; \
	done

# ---- 汇总（保留字母子目录）----
dist: all ans
	@for L in $(DIRS); do \
		mkdir -p $(DIST)/zh2en/$$L $(DIST)/en2cn/$$L $(DIST)/ans-zh2en/$$L $(DIST)/ans-en2cn/$$L; \
		cp $$L/zh2en_*.pdf     $(DIST)/zh2en/$$L/     2>/dev/null || true; \
		cp $$L/en2cn_*.pdf     $(DIST)/en2cn/$$L/     2>/dev/null || true; \
		cp $$L/ans_zh2en_*.pdf $(DIST)/ans-zh2en/$$L/ 2>/dev/null || true; \
		cp $$L/ans_en2cn_*.pdf $(DIST)/ans-en2cn/$$L/ 2>/dev/null || true; \
	done
	@echo ">> 已汇总: 题目 $(words $(ZH_PDF))+$(words $(E2C_PDF)) 份, 答案 $(words $(ANSZH_PDF))+$(words $(ANSE2C_PDF)) 份 -> $(DIST)/"

merge: all
	@mkdir -p $(DIST)
	@$(PDFUNITE) $(ZH_PDF)  "$(DIST)/默写表_中译英_全册.pdf"
	@$(PDFUNITE) $(E2C_PDF) "$(DIST)/默写表_英译中_全册.pdf"
	@for f in "$(DIST)/默写表_中译英_全册.pdf" "$(DIST)/默写表_英译中_全册.pdf"; do \
		echo ">> $$f  $$($(PDFINFO) "$$f" 2>/dev/null | awk '/^Pages/{print $$2}') 页"; \
	done

merge-ans: ans
	@mkdir -p $(DIST)
	@$(PDFUNITE) $(ANSZH_PDF) "$(DIST)/参考答案_中译英_全册.pdf"
	@$(PDFUNITE) $(ANSE2C_PDF) "$(DIST)/参考答案_英译中_全册.pdf"
	@for f in "$(DIST)/参考答案_中译英_全册.pdf" "$(DIST)/参考答案_英译中_全册.pdf"; do \
		echo ">> $$f  $$($(PDFINFO) "$$f" 2>/dev/null | awk '/^Pages/{print $$2}') 页"; \
	done

# ---- 校验 ----
check: all ans
	@fail=0; n=0; \
	for f in $(ALL_PDF); do \
		n=$$((n+1)); \
		p=$$($(PDFINFO) "$$f" 2>/dev/null | awk '/^Pages/{print $$2}'); \
		if [ "$$p" != "1" ]; then echo "  ⚠ $$f: $$p 页"; fail=1; fi; \
	done; \
	if [ $$fail -eq 0 ]; then echo "✅ 全部 $$n 份均为 1 页"; else echo "❌ 存在非单页文件"; exit 1; fi

# ---- 清理 ----
clean:
	@for L in $(DIRS); do \
		rm -f $$L/*.aux $$L/*.log $$L/*.out $$L/*.toc $$L/*.fls $$L/*.fdb_latexmk $$L/*.synctex.gz $$L/*.xdv; \
	done
	@echo ">> 已清理 LaTeX 临时文件"

distclean: clean
	@for L in $(DIRS); do rm -f $$L/*.pdf; done
	@rm -rf $(DIST)
	@echo ">> 已清理生成的 PDF 与 $(DIST)/"

# ---- 辅助 ----
list:
	@echo "题目 中→英: $(words $(ZH_PDF))   英→中: $(words $(E2C_PDF))"
	@echo "答案 中→英: $(words $(ANSZH_PDF))   英→中: $(words $(ANSE2C_PDF))"
	@echo "合计: $(words $(ALL_PDF)) 份"

help:
	@sed -n '2,21p' $(firstword $(MAKEFILE_LIST)) | sed 's/^# \{0,1\}//'
