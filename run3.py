"""云端网页入口：只更新双影院排片，始终不发送 Bark 通知。"""
import sys
from cinema_monitor import ROOT, main

if __name__ == "__main__":
    sys.exit(main(["--once", "--no-notify", "--state", str(ROOT / ".web-state.json"), *sys.argv[1:]]))
