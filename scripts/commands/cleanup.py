# -*- coding: utf-8 -*-
"""清理后台进程：只杀自己人（本端口孤立 headless 浏览器 + agent-browser daemon）。"""
import os
from common import log
from core.browser import plan_cleanup, kill_strays_on_port, kill_agent_browser

def run(args):
    port = args.port or int(os.environ.get("CDP_PORT", "9223"))
    if args.dry_run:
        plan = plan_cleanup(port)
        log("【dry-run】将要清理：")
        for p in plan:
            log("  - " + p)
        return
    kill_strays_on_port(port)
    kill_agent_browser()
    log("✅ 后台进程已清理（端口 %d 上的孤立 headless 浏览器 + agent-browser daemon）" % port)
