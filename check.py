from lxml import etree
import csv
import requests
from datetime import datetime
import pandas as pd
import requests
import time
# 读取 CSV 文件

def push(text):
    # 设置推送的内容
    push_url = f'https://api.day.app/Ua37yhGwsH7cUVbzhcTpn3/{text}'


    # 发送 POST 请求
    response = requests.post(push_url)

    # 打印响应内容
    if response.status_code == 200:
        print("推送成功！")
    else:
        print(f"推送失败，状态码: {response.status_code}")
import os

def csv_remove_duplicates():
    # 获取当前目录下的所有 CSV 文件
    #打开文件使用encoding='gbk'
    csv_files = [f for f in os.listdir() if f.endswith('.csv')]
    # 遍历最新的两个文件，查找不一样的行然后打印出来
    if len(csv_files) >= 2:
        # 读取最新的两个文件
        df1 = pd.read_csv(csv_files[-1], header=None, names=["ID", "Plan", "Date", "Time", "Room"], encoding='gbk')
        df2 = pd.read_csv(csv_files[-2], header=None, names=["ID", "Plan", "Date", "Time", "Room"], encoding='gbk')
        # 找出不一样的行
        diff = pd.concat([df1, df2]).drop_duplicates(keep=False)
        # 输出不一样的行
        if not diff.empty:
            return diff
        else:
            print("两个文件内容一样。")
    else:
        print("没有足够的文件进行比较。")

#我想要把每次结果合并到一个文件里，然后再进行比对，这样就不会出现重复的情况了


# # 获取当前目录下的所有 CSV 文件
# csv_files = [f for f in os.listdir() if f.endswith('.csv')]

# # 找出字典序最大的文件名
# if csv_files:
#     max_file = max(csv_files)
#     print(f"字典序最大（即文件名最大）的文件是: {max_file}")
# else:
#     print("没有找到 CSV 文件。")
# filename = max_file

# df = pd.read_csv(filename, header=None,encoding='gbk', names=["ID", "Plan", "Date", "Time", "Room"])

# # 要搜索的关键字
# search_plan = "杜比影院厅（儿童需购票）"
# search_day = "周一"

# # 查找包含“孤星计划”和“周一”的行
# result = df[(df["Room"].str.contains(search_plan)) & (df["Date"].str.contains(search_day))]


# # 输出查询结果
# if not result.empty:
#     print(result)
#     push("杜比影院上新")
# else:
#     print(f"没有找到包含 '{search_plan}' 和 '{search_day}' 的记录")



# # 要搜索的关键字
# search_plan = "柯南"
# search_day = ""

# # 查找包含“孤星计划”和“周一”的行
# result = df[(df["Plan"].str.contains(search_plan)) & (df["Date"].str.contains(search_day))]


# # 输出查询结果
# if not result.empty:
#     print(result)
#     push("柯南上新")
# else:
#     print(f"没有找到包含 '{search_plan}' 和 '{search_day}' 的记录")

if __name__ == "__main__":
    diff = csv_remove_duplicates()
    if diff is not None:
        push("有新的影片上新")
        print(diff)