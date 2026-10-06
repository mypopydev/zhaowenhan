# 英语翻译背诵 · 编译 Makefile
#
# 目录约定（recitation/）：
#   原文/<名称>.html     公众号原文 HTML（溯源）
#   原文/<名称>.json     解析后的条目数据（重排依据）
#   源码/<名称>_zh2en.tex  默写卷（中→英，英文留空）      —— 输出到 默写/
#   源码/<名称>_ans.tex    中英对照（背诵 · 答案）        —— 输出到 答案/
#   源码/<名称>_en2zh.tex  回译卷（英→中，中文留空）      —— 输出到 回译/
#
# 常用命令：
#   make                编译全部 tex → pdf（pdf 落在对应输出目录）
#   make check          校验：每份 1 页、日志 0 处 Overfull／Underfull／Missing character
#   make clean          清理 LaTeX 中间文件与生成的 PDF
#   make list           查看清单
#
# 可复现构建：与 mistakes/Makefile 同一套做法——① 以源文件 mtime 作为
# SOURCE_DATE_EPOCH 传给 TeX Live（固定 PDF 的 /ID），② 用 -usepretex 注入
# docinfo special，覆盖 XeTeX 默认写入的编译时刻并把 /CreationDate 定为源文件
# 日期。源码不变时重编得到逐字节相同的 PDF。

SHELL       := /bin/bash
LATEXMK     := latexmk
LATEXMKOPTS := -xelatex -interaction=nonstopmode -halt-on-error -file-line-error -silent
PDFINFO     := pdfinfo

TEX := $(sort $(wildcard 源码/*.tex))
PDF := $(patsubst 源码/%_zh2en.tex,默写/%_zh2en.pdf,$(filter %_zh2en.tex,$(TEX))) \
       $(patsubst 源码/%_ans.tex,答案/%_ans.pdf,$(filter %_ans.tex,$(TEX))) \
       $(patsubst 源码/%_en2zh.tex,回译/%_en2zh.pdf,$(filter %_en2zh.tex,$(TEX)))

.PHONY: all check clean list

all: $(PDF)

# ---- 编译规则（可复现）----
默写/%_zh2en.pdf: 源码/%_zh2en.tex
	@mkdir -p 默写
	@$(call build,$<,$@)

答案/%_ans.pdf: 源码/%_ans.tex
	@mkdir -p 答案
	@$(call build,$<,$@)

回译/%_en2zh.pdf: 源码/%_en2zh.tex
	@mkdir -p 回译
	@$(call build,$<,$@)

define build
ep=$$(stat -f %m "$1" 2>/dev/null || stat -c %Y "$1"); \
d=$$(date -u -r "$$ep" +%Y%m%d%H%M%SZ 2>/dev/null || date -u -d "@$$ep" +%Y%m%d%H%M%SZ); \
printf '>> %s\n' "$1"; \
SOURCE_DATE_EPOCH=$$ep $(LATEXMK) $(LATEXMKOPTS) \
	-outdir="$$(dirname "$2")" \
	-usepretex="\\special{pdf:docinfo<</Creator(English/recitation)/Producer(xdvipdfmx)/CreationDate(D:$$d)>>}" "$1"
endef

# ---- 校验：每份 1 页、日志 0 警告 ----
check: all
	@fail=0; n=0; \
	for f in $(PDF); do \
		n=$$((n+1)); \
		log="$$(dirname $$f)/$$(basename $$f .pdf).log"; \
		p=$$($(PDFINFO) "$$f" 2>/dev/null | awk '/^Pages/{print $$2}'); \
		if [ ! -f "$$log" ]; then bad=日志缺失; \
		else bad=$$(grep -cE 'Overfull|Underfull|Missing character' "$$log"); fi; \
		if [[ "$$f" == *bundle* ]]; then \
			want="1–12"; ok=$$([ "$$p" -ge 1 ] && [ "$$p" -le 12 ] && echo 1 || echo 0); \
		else \
			want="1"; ok=$$([ "$$p" = "1" ] && echo 1 || echo 0); \
		fi; \
		if [ "$$ok" != "1" ] || [ "$$bad" != "0" ]; then \
			echo "  ⚠ $$f: $$p 页（应 $$want 页）、日志问题 $$bad 处"; fail=1; \
		else \
			printf '  ✓ %-46s %s 页  0 警告\n' "$$f" "$$p"; \
		fi; \
	done; \
	if [ $$fail -eq 0 ]; then echo "✅ 全部 $$n 份通过（页数与日志均符合预期）"; else echo "❌ 存在不符合预期的文件"; exit 1; fi

# ---- 清理 ----
clean:
	@rm -f 默写/*.pdf 答案/*.pdf 回译/*.pdf
	@rm -f 默写/*.aux 答案/*.aux 回译/*.aux
	@rm -f 默写/*.log 答案/*.log 回译/*.log
	@rm -f 默写/*.fls 答案/*.fls 回译/*.fls
	@rm -f 默写/*.fdb_latexmk 答案/*.fdb_latexmk 回译/*.fdb_latexmk
	@rm -f 默写/*.xdv 答案/*.xdv 回译/*.xdv
	@echo ">> 已清理生成的 PDF 与中间文件"

list:
	@echo "源码 $(words $(TEX)) 份 → PDF $(words $(PDF)) 份"
	@printf '%s\n' $(PDF) | sed 's/^/  /'
