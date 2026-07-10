# 微信读书扩展阅读助手 — 便捷命令
# 使用 WorkBuddy 隔离 venv 的 python 运行（Windows: Scripts/python.exe）

VENV_PY ?= C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe
SK := scripts/weread.py

.PHONY: help install lint test clean

help:
	@echo "Targets: install lint test clean"
	@echo "  install  安装运行依赖 (playwright)"
	@echo "  lint     语法自检 (py_compile)"
	@echo "  test     运行语法/冒烟自检 (tests/syntax_check.py)"
	@echo "  clean    删除 __pycache__"

install:
	"$(VENV_PY)" -m pip install -r requirements.txt

lint:
	"$(VENV_PY)" -m py_compile $(shell find scripts -name '*.py')

test:
	"$(VENV_PY)" tests/syntax_check.py

clean:
	-find . -type d -name __pycache__ -exec rm -rf {} +
