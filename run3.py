import requests
from lxml import etree
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from ics import Calendar, Event
import os
import collections
if not hasattr(collections, 'Mapping'):
    import collections.abc
    collections.Mapping = collections.abc.Mapping
# ==========================================================

import requests
from lxml import etree
# ==== 配置区域 ====
cinema_ids = ["1037"]  # 影院代号列表
keywords = ["IMAX"]    # 筛选影厅关键词
ics_filename = "movies.ics"  # 导出的 ICS 文件名
# ==================

def get_html(cinema_id):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Referer': f'https://www.maoyan.com/cinema/{cinema_id}',
        'Cookie': '__mta=210542506.1733641122799.1733642219853.1733647588736.25; uuid_n_v=v1; uuid=DC9A4F20B53111EFB8546310D54B6F22534E20DE39E9421BBFC34EFAE872705F;',
    }
    url = f"https://www.maoyan.com/cinema/{cinema_id}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            html_file = f"maoyan_{cinema_id}.html"
            with open(html_file, "w", encoding="utf-8") as file:
                file.write(response.text)
            print(f"✅ 影院 {cinema_id} 页面已保存")
            return html_file
        else:
            print(f"❌ 请求失败: {cinema_id}，状态码: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None

def parse_html(html_file, cinema_id, keyword_list):
    with open(html_file, "r", encoding="utf-8") as file:
        html = file.read()
    tree = etree.HTML(html)
    index = 3
    matched = []
    while True:
        movie_name_xpath = f'//*[@id="app"]/div[{index}]/div[1]/div[1]/h2'
        movie_name_res = tree.xpath(movie_name_xpath)
        if not movie_name_res: break
        movie_name = movie_name_res[0].text.strip()
        index2 = 2
        while True:
            date_xpath = f'//*[@id="app"]/div[{index}]/div[2]/span[{index2}]'
            date_res = tree.xpath(date_xpath)
            if not date_res: break
            movie_date = date_res[0].text[3:].strip()
            index3 = 1
            newindex2 = index2 + 1
            while True:
                time_xpath = f'//*[@id="app"]/div[{index}]/div[{newindex2}]/table/tbody/tr[{index3}]/td[1]/span[1]'
                time_res = tree.xpath(time_xpath)
                if not time_res: break
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

def generate_ics(movie_list, filename="movies.ics"):
    calendar = Calendar()
    tz = ZoneInfo("Asia/Shanghai")
    current_year = datetime.now(tz).year

    for row in movie_list:
        cinema_id, name, date_str, time_str, room = row
        try:
            # 处理日期格式：12月10日 -> 12-10
            clean_date = date_str.replace("月", "-").replace("日", "")
            # 组合成完整时间
            dt_str = f"{current_year}-{clean_date} {time_str}"
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
            dt = dt.replace(tzinfo=tz)

            event = Event()
            event.name = f"{name}（{room}）"
            event.begin = dt
            event.duration = timedelta(hours=2.5) # 电影通常按2.5小时预留
            event.location = "西安万达影城（高新万达广场店）"
            event.description = f"影院ID: {cinema_id} | 影厅: {room}"
            calendar.events.add(event)
        except Exception as e:
            print(f"⚠️ 跳过错误行: {row}，原因: {e}")

    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(calendar)
    print(f"📅 ICS 文件已保存为：{filename}")

def main():
    all_data = []
    for cid in cinema_ids:
        html_file = get_html(cid)
        if html_file:
            matches = parse_html(html_file, cid, keywords)
            all_data.extend(matches)
            if os.path.exists(html_file): os.remove(html_file) # 清理临时文件

    if all_data:
        generate_ics(all_data, ics_filename)
    else:
        print("⚠️ 未找到符合条件的放映信息")

if __name__ == "__main__":
    main()

