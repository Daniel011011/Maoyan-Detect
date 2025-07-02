# ==== 配置区域 ====
cinema_ids = ["24311"]  # 影院代号列表
keywords = ["杜比影院厅（儿童需购票）"]  # 筛选影厅关键词
ics_filename = "movies.ics"  # 导出的 ICS 文件名
# ==================

import requests
from lxml import etree
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from ics import Calendar, Event
import os

# ==== 模拟浏览器请求，避免被拦截 ====
def get_html(cinema_id):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Referer': f'https://www.maoyan.com/cinema/{cinema_id}',
        'Cookie': '__mta=210542506.1733641122799.1733642219853.1733647588736.25; uuid_n_v=v1; uuid=DC9A4F20B53111EFB8546310D54B6F22534E20DE39E9421BBFC34EFAE872705F; _csrf=13d3621adccdd088d441415f77b219246d0f0b275ae4180c318b03bf5c90cbcd; Hm_lvt_e0bacf12e04a7bd88ddbd9c74ef2b533=1733641122; HMACCOUNT=BC022F5825BD5502; _lx_utm=utm_source%3Dbing%26utm_medium%3Dorganic; _lxsdk_cuid=193a510320c8a-0bcd8e0240c7a8-4c657b58-1fa400-193a510320dc8; _ga=GA1.1.1724561831.1733641123; WEBDFPID=0v459uvuy74y50w0zu20183v6vx959xu806z48859w0979583uvu4x02-2049001189653-1733641187358AWOOGGWfd79fef3d01d5e9aadc18ccd4d0c95073924; token=AgE0IGV7ptrf2-r8vp7zOu7z2Elyz1cjHEjQAZPpHqFMrcCyznwzm9EZyu5NoeQENgsVaYjUD_R7CAAAAAAJJQAAWgKYq2Apjr-GbDx17w-PBIhzQbNPWh7dcMnx6x6MIWykleslpLk0fovkkG_6SC9f; uid=1049684815; uid.sig=MBK5DVJXe4-YCmKBQ9vkxxzmalQ; _lxsdk=DC9A4F20B53111EFB8546310D54B6F22534E20DE39E9421BBFC34EFAE872705F; ci=42; recentCis=42; __mta=210542506.1733641122799.1733641341509.1733641356975.22; Hm_lpvt_e0bacf12e04a7bd88ddbd9c74ef2b533=1733647589; _ga_WN80P4PSY7=GS1.1.1733647588.2.0.1733647588.0.0.0; _lxsdk_s=193a572dd54-3e5-7e1-740%7C%7C2',
    }

    url = f"https://www.maoyan.com/cinema/{cinema_id}"

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            html_file = f"maoyan_{cinema_id}.html"
            with open(html_file, "w", encoding="utf-8") as file:
                file.write(response.text)
            print(f"✅ 影院 {cinema_id} 页面已保存为 {html_file}")
            return html_file
        else:
            print(f"❌ 请求失败: {cinema_id}，状态码: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 请求异常: {cinema_id}，错误信息: {e}")
        return None

# ==== 解析本地 HTML，提取匹配的排片信息 ====
def parse_html(html_file, cinema_id, keyword_list):
    with open(html_file, "r", encoding="utf-8") as file:
        html = file.read()

    tree = etree.HTML(html)
    index = 3
    matched = []

    while True:
        movie_name_xpath = f'//*[@id="app"]/div[{index}]/div[1]/div[1]/h2'
        movie_name_res = tree.xpath(movie_name_xpath)
        if not movie_name_res:
            break
        movie_name = movie_name_res[0].text.strip()
        index2 = 2

        while True:
            date_xpath = f'//*[@id="app"]/div[{index}]/div[2]/span[{index2}]'
            date_res = tree.xpath(date_xpath)
            if not date_res:
                break
            movie_date = date_res[0].text[3:].strip()  # 去掉 "周X "

            index3 = 1
            newindex2 = index2 + 1
            while True:
                time_xpath = f'//*[@id="app"]/div[{index}]/div[{newindex2}]/table/tbody/tr[{index3}]/td[1]/span[1]'
                time_res = tree.xpath(time_xpath)
                if not time_res:
                    break
                show_time = time_res[0].text.strip()

                room_xpath = f'//*[@id="app"]/div[{index}]/div[{newindex2}]/table/tbody/tr[{index3}]/td[3]/span'
                room_res = tree.xpath(room_xpath)
                room = room_res[0].text.strip() if room_res else ""

                if any(k in room for k in keyword_list):
                    matched.append([cinema_id, movie_name, movie_date, show_time, room])

                index3 += 1
            index2 += 1
        index += 1
    return matched

# ==== 生成 ICS 文件 ====
def generate_ics(movie_list, filename="movies.ics"):
    calendar = Calendar()
    tz = ZoneInfo("Asia/Shanghai")  # 设置为北京时间

    for row in movie_list:
        cinema_id, name, date_str, time_str, room = row
        try:
            # 解析日期时间
            date_str = date_str.replace("月", "-").replace("日", "")
            dt = datetime.strptime(f"2025-{date_str} {time_str}", "%Y-%m-%d %H:%M")
            dt = dt.replace(tzinfo=tz)

            # 创建日历事件
            event = Event()
            event.name = f"{name}（{room}）"
            event.begin = dt
            event.duration = timedelta(hours=2)
            event.location = "西安万达影城（高新万达广场杜比影院店）"  # 添加城市位置
            event.description = f"影院ID: {cinema_id} - {room}"

            calendar.events.add(event)
        except Exception as e:
            print(f"⚠️ 跳过错误行: {row}，原因: {e}")

    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(calendar)
    print(f"📅 ICS 文件已保存为：{filename}")

# ==== 主程序入口 ====
def main():
    all_data = []
    for cid in cinema_ids:
        html_file = get_html(cid)
        if html_file:
            matches = parse_html(html_file, cid, keywords)
            all_data.extend(matches)

    if all_data:
        generate_ics(all_data, ics_filename)
    else:
        print("⚠️ 未找到符合条件的放映信息")

if __name__ == "__main__":
    main()
