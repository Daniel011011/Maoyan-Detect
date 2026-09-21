"""旧入口兼容：现在与独立脚本共用双影院检测，默认每 30 分钟。"""
import sys
from cinema_monitor import main

if __name__ == "__main__":
    sys.exit(main())
