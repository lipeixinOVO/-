# -*- coding: utf-8 -*-
"""headless Chrome 的公共启动封装，shot.py / peek.py 共用。

**user-data-dir 必须是每次唯一的临时目录**，不能是项目里的固定目录。
固定目录踩过两个坑（2026-10-26 现场）：

1. 上一次 Chrome 没退干净时目录被锁，新进程建不了 profile 直接失败；
2. headless 失败后会退回**带 UI 的模式**，在用户桌面上弹出一个
   「无法创建数据目录 / Google Chrome 无法对其数据目录 _shot_profile 执行读写操作」
   的对话框 —— 用户正在用电脑，突然弹这个，完全不知道哪来的。

临时目录用完即删，既不锁、也不会被 push_github.py 当源码传上去。
"""
import os
import shutil
import subprocess
import tempfile

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# 不弹任何首次运行/更新/同步相关的 UI，避免 headless 退回窗口模式
FLAGS = [
    "--headless=new",
    "--disable-gpu",
    "--hide-scrollbars",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "--disable-sync",
    "--disable-extensions",
    "--disable-component-update",
    "--disable-features=Translate,MediaRouter",
    "--metrics-recording-only",
]


def run(args, timeout=90):
    """跑一次 Chrome，返回 CompletedProcess。args 里不要自己带 --user-data-dir。"""
    d = tempfile.mkdtemp(prefix="dcashot-")
    try:
        cmd = [CHROME] + FLAGS + ["--user-data-dir=" + d] + list(args)
        return subprocess.run(cmd, check=False, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print("⚠ Chrome 超时，跳过")
        return None
    finally:
        # Windows 上句柄释放有延迟，删不掉就算了（是临时目录，系统会回收）
        shutil.rmtree(d, ignore_errors=True)


def chrome_path():
    return CHROME if os.path.exists(CHROME) else None
