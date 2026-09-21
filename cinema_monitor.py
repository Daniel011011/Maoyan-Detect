"""独立双影院监控，Python 3.10+，仅使用标准库。运行 --help 查看参数。"""
import argparse
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import re
import sys
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, unquote
from urllib.request import Request, urlopen

TZ = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parent
CINEMAS = [
    {"id": "24311", "name": "西安万达影城（高新万达广场店）", "format": "杜比影院"},
    {"id": "39869", "name": "寰映影城（西安荟聚激光IMAX店）", "format": "激光 IMAX"},
]
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Version/16.0 Mobile/15E148 Safari/604.1"


def now():
    return datetime.now(TZ)


def normalize(value):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value)).upper()


def matches_hall(cinema, hall):
    value = normalize(hall)
    if cinema["id"] == "24311":
        return "杜比影院" in value or "DOLBYCINEMA" in value
    return "IMAX" in value and ("激光" in value or "LASER" in value)


def request_json(url, payload=None):
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(url, data=body, headers={"User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json"})
    with urlopen(req, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch(cinema):
    return request_json("https://m.maoyan.com/ajax/cinemaDetail?cinemaId=" + cinema["id"])


def parse(data, cinema, clock=None):
    clock = clock or now()
    if not isinstance(data, dict) or not isinstance(data.get("showData"), dict):
        raise ValueError("响应缺少 showData，可能需要验证或接口已变更")
    show = data["showData"]
    if str(show.get("cinemaId", data.get("cinemaId"))) != cinema["id"]:
        raise ValueError("接口返回影院编号不一致")
    if not isinstance(show.get("movies"), list):
        raise ValueError("响应缺少 movies 列表，不能作为无排片处理")
    result = {}
    for movie in show["movies"]:
        if not isinstance(movie.get("shows"), list):
            raise ValueError("影片缺少 shows 列表")
        for group in movie["shows"]:
            if not isinstance(group.get("plist"), list):
                raise ValueError("日期缺少 plist 列表")
            for slot in group["plist"]:
                hall = slot.get("th", "")
                if not matches_hall(cinema, hall):
                    continue
                date = slot.get("dt") or group.get("showDate")
                start = datetime.strptime(f"{date} {slot['tm']}", "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
                if start <= clock:
                    continue
                name = movie["nm"]
                identity = [cinema["id"], str(movie.get("id") or name), start.isoformat(), normalize(hall)]
                key = hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()[:24]
                duration = movie.get("dur")
                duration = int(duration) if str(duration).isdigit() and int(duration) > 0 else None
                result[key] = {"key": key, "cinema_id": cinema["id"], "movie": name, "hall": hall,
                               "date": start.strftime("%Y-%m-%d"), "time": start.strftime("%H:%M"),
                               "start": start.isoformat(), "duration": duration,
                               "bookable": str(slot.get("enterShowSeat")) == "1"}
    return sorted(result.values(), key=lambda s: (s["start"], s["movie"]))


def special(slot):
    name = normalize(slot["movie"])
    return ("复仇者联盟4" in name or "复联4" in name or "AVENGERS:ENDGAME" in name) and datetime.fromisoformat(slot["start"]).weekday() == 5


def atomic_json(path, value):
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def atomic_text(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(value, encoding="utf-8", newline="")
    tmp.replace(path)


def read_state(path):
    if not path.exists():
        return {"version": 1, "cinemas": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("cinemas"), dict):
        raise ValueError("状态文件格式错误，请保留备份后处理；不会自动重置通知记录")
    return data


def bark_settings(value):
    value = value.strip()
    if not value:
        raise ValueError("请设置 BARK_URL 或本地 bark_url.txt")
    if "://" not in value:
        return "https://api.day.app/push", value
    parsed = urlparse(value)
    parts = parsed.path.strip("/").split("/")
    if parsed.scheme != "https" or not parsed.netloc or not parts[0]:
        raise ValueError("Bark 地址必须为 https://服务器/设备Key/可选内容")
    return f"{parsed.scheme}://{parsed.netloc}/push", unquote(parts[0])


def notify(bark, cinema, slots, new_date):
    endpoint, key = bark_settings(bark)
    title = "周六《复联4》有排片了" if any(special(s) for s in slots) else ("影院新一天排片" if new_date else "影院新增场次")
    date = datetime.fromisoformat(slots[0]["start"])
    weekday = "周" + "一二三四五六日"[date.weekday()]
    lines = [cinema["name"], f"{date:%Y年%m月%d日}（{weekday}） · {cinema['format']}"]
    for s in slots:
        sale = "可进入选座" if s["bookable"] else "已排片，开售状态待确认"
        lines.append(f"{s['time']} 《{s['movie']}》｜{s['hall']}｜{sale}")
    lines.append("以上为新增场次，余票以购票页为准。")
    answer = request_json(endpoint, {"device_key": key, "title": title, "body": "\n".join(lines),
                                    "group": "西安影院排片", "url": "https://www.maoyan.com/cinema/" + cinema["id"]})
    if not isinstance(answer, dict) or answer.get("code") != 200:
        raise RuntimeError("Bark 未确认推送成功")


def export(state, out):
    clock = now()
    cinemas = []
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Maoyan Detect//Cinema//ZH", "CALSCALE:GREGORIAN"]
    def escape(value):
        return value.replace("\\", "\\\\").replace("\n", "\\n").replace(";", "\\;").replace(",", "\\,")
    for cinema in CINEMAS:
        entry = state["cinemas"].get(cinema["id"], {})
        slots = [s for s in entry.get("slots", []) if datetime.fromisoformat(s["start"]) > clock]
        cinemas.append({**cinema, "url": "https://www.maoyan.com/cinema/" + cinema["id"],
                        "updated_at": entry.get("updated_at"), "error": entry.get("error"), "slots": slots})
        for s in slots:
            begin = datetime.fromisoformat(s["start"]).astimezone(timezone.utc)
            lines += ["BEGIN:VEVENT", "UID:" + s["key"] + "@maoyan-detect", "DTSTAMP:" + datetime.fromisoformat(entry["updated_at"]).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
                      "DTSTART:" + begin.strftime("%Y%m%dT%H%M%SZ"),
                      "SUMMARY:" + escape(f"{s['movie']}（{s['hall']}）"), "LOCATION:" + escape(cinema["name"]),
                      "URL:https://www.maoyan.com/cinema/" + cinema["id"]]
            if s["duration"]:
                lines.append("DTEND:" + (begin + timedelta(minutes=s["duration"])).strftime("%Y%m%dT%H%M%SZ"))
            lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    # RFC 5545: fold lines on UTF-8 byte boundaries (75 octets, including continuation).
    folded = []
    for line in lines:
        part = ""
        for ch in line:
            if len((part + ch).encode("utf-8")) > 75:
                folded.append(part)
                part = " "
            part += ch
        folded.append(part)
    atomic_text(out / "movies.ics", "\r\n".join(folded) + "\r\n")
    atomic_json(out / "schedules.json", {"generated_at": clock.isoformat(), "cinemas": cinemas})


def check_once(state_path, out, bark, no_notify=False, notify_initial=False, fetcher=fetch, sender=notify):
    state = read_state(state_path)
    failures = 0
    for cinema in CINEMAS:
        cid = cinema["id"]
        entry = state["cinemas"].setdefault(cid, {})
        try:
            slots = parse(fetcher(cinema), cinema)
        except Exception as exc:
            failures += 1
            entry["error"] = f"排片更新失败（{type(exc).__name__}），保留上次成功数据"
            logging.error("%s: %s", cinema["name"], entry["error"])
            atomic_json(state_path, state)
            continue
        first = not entry.get("updated_at")
        previous = {s["key"] for s in entry.get("slots", [])}
        previous_dates = {s["date"] for s in entry.get("slots", [])}
        # Keep acknowledgements for future dates, even if a show temporarily disappears.
        today = now().date().isoformat()
        seen = {k: date for k, date in entry.get("seen", {}).items() if date >= today}
        pending = dict(entry.get("pending", {}))
        current = {s["key"]: s for s in slots}
        pending = {k: {**value, "slot": current[k]} for k, value in pending.items() if k in current and k not in seen}
        for s in slots:
            if s["key"] in seen:
                continue
            if no_notify or (first and not notify_initial and not special(s)):
                seen[s["key"]] = s["date"]
            elif s["key"] not in previous or s["key"] in pending:
                pending.setdefault(s["key"], {"slot": s, "new_date": s["date"] not in previous_dates})
        if no_notify:
            pending = {}
        entry.update(slots=slots, updated_at=now().isoformat(), error=None, seen=seen, pending=pending)
        atomic_json(state_path, state)  # Persist pending before sending so a failed send can retry.
        logging.info("%s：%d 场，待通知 %d 场%s", cinema["name"], len(slots), len(pending), "（首次建立基线）" if first else "")
        for date in sorted({p["slot"]["date"] for p in pending.values()}):
            day = sorted([p for p in pending.values() if p["slot"]["date"] == date], key=lambda p: p["slot"]["start"])
            # Split long notifications without dropping any showtimes.
            for offset in range(0, len(day), 8):
                chunk = day[offset:offset + 8]
                try:
                    sender(bark, cinema, [p["slot"] for p in chunk], any(p["new_date"] for p in chunk))
                except Exception as exc:
                    logging.error("%s：Bark 推送失败（%s），下次重试", cinema["name"], type(exc).__name__)
                    failures += 1
                    break
                for p in chunk:
                    s = p["slot"]
                    seen[s["key"]] = s["date"]
                    pending.pop(s["key"], None)
                atomic_json(state_path, state)
    export(state, out)
    return failures == 0


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="监控高新万达杜比影院与西安荟聚寰映激光 IMAX，新增场次通过 Bark 通知")
    p.add_argument("--interval", type=float, default=30, metavar="分钟", help="检测间隔，默认 30 分钟")
    p.add_argument("--once", action="store_true", help="只检测一次，适合任务计划或 GitHub Actions")
    p.add_argument("--no-notify", action="store_true", help="只更新排片并建立通知基线，不发送 Bark")
    p.add_argument("--notify-initial", action="store_true", help="首次启动也通知所有现有场次；默认仅周六复联4首次提醒")
    p.add_argument("--state", type=Path, default=ROOT / ".cinema-state.json")
    p.add_argument("--output-dir", type=Path, default=ROOT)
    args = p.parse_args(argv)
    if not math.isfinite(args.interval) or args.interval <= 0:
        p.error("--interval 必须是大于 0 的有限分钟数")
    bark = os.environ.get("BARK_URL", "")
    if not bark and (ROOT / "bark_url.txt").exists():
        bark = (ROOT / "bark_url.txt").read_text(encoding="utf-8-sig").strip()
    if not args.no_notify:
        try:
            bark_settings(bark)
        except ValueError as exc:
            p.error(str(exc))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        while True:
            started = time.monotonic()
            try:
                ok = check_once(args.state, args.output_dir, bark, args.no_notify, args.notify_initial)
            except Exception as exc:
                logging.error("本轮失败（%s），不会重置已有状态", type(exc).__name__)
                ok = False
            if args.once:
                return 0 if ok else 1
            delay = max(1, args.interval * 60 - (time.monotonic() - started))
            logging.info("下次检测约在 %.1f 分钟后；按 Ctrl+C 停止", delay / 60)
            time.sleep(delay)
    except KeyboardInterrupt:
        logging.info("监控已停止")
        return 0


if __name__ == "__main__":
    sys.exit(main())
