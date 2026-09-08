import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from ics import Calendar, Event

# ==== 配置区域 ====
cinema_ids = ["24311"]  # 影院代号列表
keywords = ["杜比影院"]    # 筛选影厅关键词
ics_filename = "movies.ics"  # 导出的 ICS 文件名
# ==================

def get_cinema_data(cinema_id):
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
    }
    url = f"https://m.maoyan.com/ajax/cinemaDetail?cinemaId={cinema_id}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"[OK] 影院 {cinema_id} 数据已获取")
            return response.json()
        else:
            print(f"[FAIL] 请求失败: {cinema_id}，状态码: {response.status_code}")
            return None
    except Exception as e:
        print(f"[ERROR] 请求异常: {e}")
        return None

def parse_api_data(data, cinema_id, keyword_list):
    matched = []
    if not data or "showData" not in data:
        return matched

    for movie in data["showData"].get("movies", []):
        movie_name = movie.get("nm", "")
        for date_group in movie.get("shows", []):
            show_date = date_group.get("showDate", "")
            for slot in date_group.get("plist", []):
                hall = slot.get("th", "")
                if any(k in hall for k in keyword_list):
                    show_time = slot.get("tm", "")
                    matched.append([cinema_id, movie_name, show_date, show_time, hall])
    return matched

def generate_ics(movie_list, filename="movies.ics"):
    calendar = Calendar()
    tz = ZoneInfo("Asia/Shanghai")

    for row in movie_list:
        cinema_id, name, date_str, time_str, room = row
        try:
            dt_str = f"{date_str} {time_str}"
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
            dt = dt.replace(tzinfo=tz)

            event = Event()
            event.name = f"{name}（{room}）"
            event.begin = dt
            event.duration = timedelta(hours=2.5)
            event.location = "西安万达影城（高新万达广场店）"
            event.description = f"影院ID: {cinema_id} | 影厅: {room}"
            calendar.events.add(event)
        except Exception as e:
            print(f"[WARN] 跳过错误行: {row}，原因: {e}")

    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(calendar)
    print(f"[ICS] ICS 文件已保存为：{filename}")

def main():
    all_data = []
    for cid in cinema_ids:
        data = get_cinema_data(cid)
        if data:
            matches = parse_api_data(data, cid, keywords)
            all_data.extend(matches)

    if all_data:
        generate_ics(all_data, ics_filename)
    else:
        print("[WARN] 未找到符合条件的放映信息")

if __name__ == "__main__":
    main()



