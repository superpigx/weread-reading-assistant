# -*- coding: utf-8 -*-
"""首次使用：把已登录的 Chrome Default profile 复制为独立 WereadCDP 目录。"""
import os
from common import log
from core.browser import seed_profile, DEFAULT_PROFILE

def run(args):
    src = args.src or os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
        "Google", "Chrome", "User Data", "Default")
    dst = args.dst or os.environ.get("WEREAD_PROFILE") or DEFAULT_PROFILE
    log("复制登录态 profile: %s -> %s" % (src, dst))
    log("⚠️ 请先关闭你自己的 Chrome（否则 profile 被锁会导致复制不完整），复制完成后即可重开。")
    seed_profile(src, dst)
    log("✅ 已完成。之后脚本会自启该 profile，无需你手动登录或关浏览器。")
    if "Edge" in dst or os.path.exists(dst.replace("WereadCDP", "WereadCDP_edge")):
        pass
