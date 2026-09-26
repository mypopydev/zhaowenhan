# 试卷与答案 —— 高一上数学
# 本文件只做转发；真正的规则都在 源码/Makefile。转发列表必须与 README「编译方式」一节
# 文档化的入口一一对应——2026-09-27 发现 docs／one-c／compact 三个漏在列表外，
# 从 papers/ 跑 `make docs` 会直接报「No rule to make target」。
.PHONY: all test ans compact one one-c check docs trace bundle list clean distclean help

all test ans compact one one-c check docs trace bundle list clean distclean help:
	@$(MAKE) -C 源码 $@
