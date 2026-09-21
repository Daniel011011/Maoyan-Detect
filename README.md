# 西安双影院排片监控

同时获取两家影院的指定影厅，网页并排显示，手机上下显示：

| 影院 | 猫眼编号 | 严格影厅筛选 |
| --- | --- | --- |
| 西安万达影城（高新万达广场店） | [24311](https://www.maoyan.com/cinema/24311) | 杜比影院 / Dolby Cinema，不包含仅杜比全景声的厅 |
| 寰映影城（西安荟聚激光IMAX店） | [39869](https://www.maoyan.com/cinema/39869) | 名称同时包含 IMAX 和激光 / Laser，不包含普通激光厅或 PRIME 杜比全景声厅 |

本地脚本对所有日期、所有电影的新增排片提醒；周六《复仇者联盟4》特别标记。网页提供「只看周六」「只看《复联4》」筛选，两个影院始终同时展示。

## 电脑运行：只需 Python 3.10 或更高版本

`cinema_monitor.py` 是独立脚本，仅用 Python 标准库，不需要 pip 安装依赖，也不依赖本项目其他文件。可以单独复制到任意文件夹。

1. 在脚本旁边创建 `bark_url.txt`，粘贴你的完整 Bark 地址，例如 `https://api.day.app/你的设备Key/任意文字`。脚本会自动提取 Key，通知内容由脚本生成。也可设置环境变量 `BARK_URL`（优先于文件）。此文件已加入 Git 忽略，不会随正常提交公开。
2. 双击 `start_monitor.cmd`，或者在脚本所在文件夹执行：

```powershell
python cinema_monitor.py
```

启动时立即检测，以后默认每 30 分钟检测一次。保持程序运行且电脑联网、不休眠，Ctrl+C 停止。要改成每 10 分钟：

```powershell
python cinema_monitor.py --interval 10
```

其他用法：

```powershell
python cinema_monitor.py --once                 # 只检测一次
python cinema_monitor.py --once --no-notify     # 更新排片、建立基线，不发通知
python cinema_monitor.py --notify-initial       # 首次也通知所有现有场次
python run3.py                                 # 网页更新入口，始终不发通知
python data.py                                 # 原项目循环入口，同样默认每30分钟
```

默认首次成功抓取建立基线，避免把所有旧场次推送一遍；如果首次就有周六《复联4》，仍会提醒。后续新增日期、新增影片或同一天新增开场时间都会提醒。删除场次、价格变动不提醒；相同场次短暂消失后恢复不重复提醒。失败的 Bark 推送保存在待发送队列，下次重试。通知按影院、日期分组，注明星期、电影、时间、影厅和能否进入选座，长列表分批发送。

本地 `.cinema-state.json` 保存基线及通知记录，重启程序不会丢失。不要删除它或同时启动多个进程写同一个状态文件。只有 Bark 确认成功才记录已发送；网络超时恰好发生在服务端收下通知之后时，重试仍可能造成重复。

`--no-notify` 会把当前场次记入基线，之后启用推送仅提醒新增场次。若要重新首次通知，请先备份状态文件，再使用不同的 `--state` 路径运行。

## 网页和日历

脚本生成 `schedules.json` 和 `movies.ics`，其中只包含上述两个影厅类型，使用北京时间。ICS 包含两家影院的位置和稳定事件 ID，结束时间使用接口片长，未知时不虚构片长。

本地预览（另开一个终端）：

```powershell
python preview.py
```

打开 http://127.0.0.1:8000/ 。预览服务只允许访问四个公开网页文件，不提供 Bark 配置、源码或状态文件。直接双击 HTML 会受浏览器本地文件请求限制，请使用这个本地服务。网页每 5 分钟刷新已生成的数据；刷新按钮不会直接调用猫眼接口，后台 Python 才负责检测。

某影院抓取失败时保留上次成功结果，网页标明失败及最近成功更新时间；超过 90 分钟未更新显示提示。首次从未成功获取与确认没有排片分别显示。接口返回验证页或缺少关键字段不会被误认为空排片。

## GitHub Actions 每 30 分钟自动检测及更新网页

1. 提交本次改动至仓库默认分支。工作流的 push 分支配置默认 `main`，如果默认分支不同，需要相应修改。
2. Settings → Pages → Build and deployment → Source 选择 **GitHub Actions**。
3. 在 Actions 手动运行 **Update cinema schedules**，验证更新和部署。

云端只更新两家影院指定影厅的网页排片，**始终不发送 Bark 通知，也不读取 GitHub 的 Bark Secret**。不需要配置 `BARK_URL` Secret。`run3.py` 强制使用 `--no-notify`，即使环境中设置了 Bark 地址，也不会发送通知。

工作流 `*/30 * * * *` 每 30 分钟计划执行，GitHub 调度可能延迟。云端使用 `.web-state.json` 保存抓取缓存，接口临时失败时保留上次成功排片。本地通知继续由 `cinema_monitor.py` / `start_monitor.cmd` 负责，使用独立的 `.cinema-state.json`，不受网页更新影响。

Pages 部署仅上传 `index.html`、`app.js`、`schedules.json`、`movies.ics` 四个文件，不发布设备 Key 或本地通知状态文件。

接口来自原项目使用的猫眼移动端公开接口，可能限流或变更。当前排片不保证有余票；最终以购票页面为准。`check.py` 是旧 CSV 对比工具，已不被任何新入口调用。

## 验证

```powershell
python -m unittest discover -s tests -v
node --check app.js
```

测试使用合成排片及模拟推送，不向 Bark 发送测试通知。
