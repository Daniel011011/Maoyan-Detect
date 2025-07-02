# 🎬 Maoyan-Detect

A script to fetch Maoyan HTML, parse movie schedules, and detect new movies.

---

## 📢 特性

✅ 自动获取猫眼 HTML 页面  
✅ 解析并生成 `.ics` 日历文件  
✅ 通过 Bark 发送新电影通知  
✅ 自动推送日历到 [GitHub Pages](https://daniel011011.github.io/Maoyan-Detect/)，可以直接在网页上查看西安高新区杜比影院的电影安排！

---

## 🔗 访问

👉 [电影排期网页日历](https://daniel011011.github.io/Maoyan-Detect/)

---

## 🛠️ 技术点

- 使用 **requests + lxml** 抓取并解析猫眼 HTML
- 使用 **ics** 库生成标准日历文件
- 使用 **GitHub Actions** 定时更新日历文件
- 使用 **FullCalendar + ical.js** 在网页端展示日历
- 日历内容支持多 ICS 源合并，并在网页中以周视图、24 小时制、中文日期显示

---

## 💡 说明

- 项目脚本会定期抓取西安高新区杜比影城的猫眼页面，更新 `movies.ics` 文件。
- 日历网页通过 GitHub Pages 发布在：
