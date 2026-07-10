# -*- coding: utf-8 -*-
"""语法 / 冒烟自检：编译 scripts/ 下全部 .py，发现语法错误即非零退出。

运行：
  python tests/syntax_check.py
（建议用 WorkBuddy 隔离 venv 的 python；纯 py_compile，不触发运行时 import。）
"""
import compileall
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(ROOT, "scripts")


if __name__ == "__main__":
    print("==> 语法自检 scripts/ ...")
    ok = compileall.compile_dir(SCRIPTS, quiet=1, maxlevels=3)
    if ok:
        print("✅ 全部模块语法 OK")
        sys.exit(0)
    else:
        print("❌ 存在语法错误", file=sys.stderr)
        sys.exit(1)
