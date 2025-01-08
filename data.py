from lxml import etree
import csv
import requests
from datetime import datetime
import requests
import time
from check import csv_remove_duplicates

def gethtml(cinema):
    # 设置请求头
    cinema
    headers = {
        'Referer': 'https://www.maoyan.com/cinema/24311',
        'Cookie': '__mta=210542506.1733641122799.1733642219853.1733647588736.25; uuid_n_v=v1; uuid=DC9A4F20B53111EFB8546310D54B6F22534E20DE39E9421BBFC34EFAE872705F; _csrf=13d3621adccdd088d441415f77b219246d0f0b275ae4180c318b03bf5c90cbcd; Hm_lvt_e0bacf12e04a7bd88ddbd9c74ef2b533=1733641122; HMACCOUNT=BC022F5825BD5502; _lx_utm=utm_source%3Dbing%26utm_medium%3Dorganic; _lxsdk_cuid=193a510320c8a-0bcd8e0240c7a8-4c657b58-1fa400-193a510320dc8; _ga=GA1.1.1724561831.1733641123; WEBDFPID=0v459uvuy74y50w0zu20183v6vx959xu806z48859w0979583uvu4x02-2049001189653-1733641187358AWOOGGWfd79fef3d01d5e9aadc18ccd4d0c95073924; token=AgE0IGV7ptrf2-r8vp7zOu7z2Elyz1cjHEjQAZPpHqFMrcCyznwzm9EZyu5NoeQENgsVaYjUD_R7CAAAAAAJJQAAWgKYq2Apjr-GbDx17w-PBIhzQbNPWh7dcMnx6x6MIWykleslpLk0fovkkG_6SC9f; uid=1049684815; uid.sig=MBK5DVJXe4-YCmKBQ9vkxxzmalQ; _lxsdk=DC9A4F20B53111EFB8546310D54B6F22534E20DE39E9421BBFC34EFAE872705F; ci=42; recentCis=42; __mta=210542506.1733641122799.1733641341509.1733641356975.22; Hm_lpvt_e0bacf12e04a7bd88ddbd9c74ef2b533=1733647589; _ga_WN80P4PSY7=GS1.1.1733647588.2.0.1733647588.0.0.0; _lxsdk_s=193a572dd54-3e5-7e1-740%7C%7C2',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0'
    }

    # 目标 URL
    url = f"https://www.maoyan.com/cinema/{cinema}"

    # 发起请求
    response = requests.get(url, headers=headers)

    # 检查请求是否成功
    if response.status_code == 200:
        # 将内容保存为 HTML 文件
        file_name = "maoyan_cinema.html"
        with open(file_name, "w", encoding="utf-8") as file:
            file.write(response.text)
        print(f"网页{cinema}内容已保存为 {file_name}")
    else:
        print(f"请求失败，状态码: {response.status_code}")

def save_to_csv(movie_name, movie_date, show_time,room, cinema_name,filename):
    """
    将电影信息保存到 CSV 文件中。
    
    :param cinema_name: 电影院名称
    :param movie_name: 电影名称
    :param movie_date: 日期
    :param show_time: 开映时间
    :param filename: 保存的 CSV 文件名，默认为 "cinema_schedule.csv"
    """
    # 打开 CSV 文件以追加模式（如果文件不存在会自动创建）
    with open(filename, mode="a", newline="", encoding="gbk") as file:
        writer = csv.writer(file)
        
        # 如果文件为空，则写入表头
        file.seek(0, 2)  # 定位到文件末尾
        if file.tell() == 0:
            writer.writerow(["电影院名称", "电影名称", "日期", "开映时间"])  # 写入表头
        
        # 写入新的电影数据
        writer.writerow([cinema_name, movie_name, movie_date, show_time,room])

def data(ciname_name):
    with open("maoyan_cinema.html", "r", encoding="utf-8") as file:
        html = file.read()
    # 获取当前日期和时间
    global filename
    # 解析 HTML
    tree = etree.HTML(html)# 解析 HTML
    index = 3
    #电影名称 第一个div
    while True:
        xpath = f'//*[@id="app"]/div[{index}]/div[1]/div[1]/h2'
        result = tree.xpath(xpath)
        if result:
            movie_name = result[0].text
            #打印电影名称
            index2 = 2
            #电影日期
            while True:
                xpath2 = f'//*[@id="app"]/div[{index}]/div[2]/span[{index2}]'
                result2 = tree.xpath(xpath2)
                if result2:
                    movie_date = result2[0].text#打印电影日期
                    #剪切movie_date的前三位内容只保留后面的
                    movie_date = movie_date[3:]
                    index3 = 1#第几场
                    while True:
                        newindex2 = index2 + 1
                        xpath3 = f'//*[@id="app"]/div[{index}]/div[{newindex2}]/table/tbody/tr[{index3}]/td[1]/span[1]'
                        result3 = tree.xpath(xpath3)
                        if result3:
                            show_time = result3[0].text #电影日期
                            xpath4 = f'//*[@id="app"]/div[{index}]/div[{newindex2}]/table/tbody/tr[{index3}]/td[3]/span'
                            result4 = tree.xpath(xpath4)
                            room = result4[0].text#影厅
                            save_to_csv(movie_name,movie_date,show_time,room,ciname_name,filename)
                            index3 += 1
                        else:
                            break
                    index2 += 1
                else:
                    break
            index += 1
            
        else:
            break  # 如果没有找到内容，则退出循环
    print(f"数据{ciname_name}文件")

def push(text):
    # 设置推送的内容
    push_url = f'https://api.day.app/*********/{text}'


    # 发送 POST 请求
    response = requests.post(push_url)

    # 打印响应内容
    if response.status_code == 200:
        print("推送成功！")
    else:
        print(f"推送失败，状态码: {response.status_code}")


if __name__ == "__main__":
    while True:
        current_datetime = datetime.now()

        # 格式化为 MMDDhhmm 格式
        formatted_datetime = current_datetime.strftime("%m%d%H%M")

        filename = f'{formatted_datetime}.csv'

        cinema = ['25552','24311']
        for i in cinema:
            gethtml(i)
            data(i)
        print(f"数据已更新{filename}")

        diff = csv_remove_duplicates()
        if diff is not None:
            push("有新的影片上新")
            print(diff)

        time.sleep(3600)

