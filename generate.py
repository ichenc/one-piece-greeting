#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ONE PIECE · 每日通缉令
每天从角色资料库中选出一位角色，重绘一张「WANTED」通缉令并更新 README.md。

纯 Python 标准库实现，不依赖任何第三方服务或图片外链。
用法:
    python generate.py                       # 生成今日 README（默认 UTC 日期）
    python generate.py --date 2026-12-25     # 预览指定日期的角色
    python generate.py --character zoro      # 指定角色
    python generate.py --shuffle             # 手动随机换一张
    python generate.py --skip-preview        # 不生成本地预览页
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA_FILE = BASE / "characters.json"
TEMPLATE_FILE = BASE / "README_template.md"
HISTORY_FILE = BASE / "history.json"
WANTED_FILE = BASE / "assets" / "wanted.svg"
CHAR_IMAGES = BASE / "assets" / "characters"
README_FILE = BASE / "README.md"
PREVIEW_FILE = BASE / "preview.html"

CST = timezone(timedelta(hours=8))  # 以北京时间作为「今天」，与国内阅读习惯一致
WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
STAT_LABELS = ["⚔️ 攻击", "🛡️ 防御", "💨 速度", "🧠 智谋", "✨ 霸气"]
GREETINGS = [
    "今天也把帆扬起来吧，船长！",
    "伟大航路的天气，今天也适合冒险。",
    "别把罗盘弄丢了，我们出发啦。",
    "新的悬赏令贴出来了，快去看看。",
    "无论风往哪吹，都要向前航行。",
    "今天的伙伴，会是谁呢？",
    "肉！还有一场冒险在等着我们。",
]


# --------------------------------------------------------------------------- 工具

def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fp:
        fp.write(text)


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def load_data():
    payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return payload["characters"], payload["meta"]


def load_history() -> list:
    if not HISTORY_FILE.exists():
        return []
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def digest(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:12], 16)


def date_label(d: date) -> str:
    return f"{d.year} 年 {d.month} 月 {d.day} 日"


def bounty_number(c: dict) -> str:
    return f"฿ {c['bounty']:,}" if c["bounty"] else "— 未公布 —"


def stat_rows(c: dict) -> str:
    rows = []
    for label, value in zip(STAT_LABELS, c["stats"]):
        filled = round(value / 10)
        bar = "▓" * filled + "░" * (10 - filled)
        rows.append(f"| {label} | {value} | `{bar}` |")
    return "\n".join(rows)


def bounty_desc(c: dict) -> str:
    return f"{c['bounty_zh']}贝利" if c["bounty"] else "未公布"


def history_rows(hist: list, chars: dict, limit: int = 7) -> str:
    rows = []
    for item in reversed(hist[-limit:]):
        c = chars.get(item["id"])
        name = c["zh"] if c else item.get("zh", "?")
        amount = bounty_desc(c) if c else "—"
        rows.append(f"| {item['date']} | {name} | {amount} |")
    return "\n".join(rows) if rows else "| — | 还没有记录 | — |"


# --------------------------------------------------------------------------- 角色选择

def pick_character(d: date, chars: list, hist: list, force: str | None = None,
                   shuffle: bool = False) -> dict:
    """按日期确定性地选角色；排除最近 15 天登场过的，保证短期内不重复。"""
    by_id = {c["id"]: c for c in chars}
    if force:
        if force not in by_id:
            raise SystemExit(f"找不到角色 id: {force}")
        return by_id[force]

    # 幂等：同一天已有记录就复用，保证重复运行不会换角色、不会多提交一次
    if not shuffle:
        for h in hist:
            if h.get("date") == d.isoformat() and h["id"] in by_id:
                return by_id[h["id"]]

    recent = {h["id"] for h in hist[-15:]}
    pool = [c for c in chars if c["id"] not in recent] or chars[:]

    if shuffle:
        seed = digest(datetime.now(timezone.utc).isoformat() + str(random.random()))
    else:
        seed = digest(f"one-piece-wanted:{d.isoformat()}")
    return pool[seed % len(pool)]


# --------------------------------------------------------------------------- 图标

def icon_svg(name: str) -> str:
    """返回 100x100 坐标系内的白色线性图标（外层 g 统一提供描边样式）。"""
    W = ''
    icons = {
        "strawhat": f'<path d="M27 58 Q29 26 50 24 Q71 26 73 58 Z" fill="#ffffff" fill-opacity="0.16" {W}/>'
                    f'<ellipse cx="50" cy="59" rx="40" ry="10" fill="#ffffff" fill-opacity="0.28" {W}/>'
                    f'<path d="M29 50 Q50 57 71 50" {W}/>',
        "sword": f'<path d="M14 86 L72 20 M30 90 L86 28 M12 62 L58 12" {W}/>'
                 f'<path d="M12 86 L24 74 M28 90 L40 78 M10 62 L22 52" {W}/>'
                 f'<circle cx="72" cy="18" r="4" fill="#ffffff"/>',
        "compass": f'<circle cx="50" cy="50" r="36" {W}/>'
                   f'<path d="M50 10 L58 42 L90 50 L58 58 L50 90 L42 58 L10 50 L42 42 Z" fill="#ffffff" fill-opacity="0.32" {W}/>'
                   f'<circle cx="50" cy="50" r="5" fill="#ffffff"/>',
        "star": f'<path d="M50 8 L62 38 L94 40 L69 61 L78 92 L50 74 L22 92 L31 61 L6 40 L38 38 Z" fill="#ffffff" fill-opacity="0.28" {W}/>',
        "flame": f'<path d="M50 8 C62 28 78 34 74 58 C71 80 61 90 50 92 C34 90 24 78 24 60 C24 46 32 40 36 30 C40 42 44 42 46 36 C50 26 44 18 50 8 Z" fill="#ffffff" fill-opacity="0.28" {W}/>'
                 f'<path d="M50 52 C57 62 60 68 56 76 C53 82 46 82 43 76 C40 70 44 62 50 52 Z" fill="#ffffff" fill-opacity="0.55"/>',
        "antler": f'<path d="M30 40 L18 18 M18 18 L8 12 M18 18 L24 6 M70 40 L82 18 M82 18 L92 12 M82 18 L76 6" {W}/>'
                  f'<path d="M26 44 Q50 32 74 44 Q80 66 68 80 Q50 92 32 80 Q20 66 26 44 Z" fill="#ffffff" fill-opacity="0.22" {W}/>'
                  f'<circle cx="40" cy="60" r="3.5" fill="#ffffff"/><circle cx="60" cy="60" r="3.5" fill="#ffffff"/>',
        "book": f'<path d="M50 30 Q34 20 12 24 L12 78 Q34 74 50 84 Q66 74 88 78 L88 24 Q66 20 50 30 Z" fill="#ffffff" fill-opacity="0.22" {W}/>'
                f'<path d="M50 30 L50 84" {W}/>'
                f'<path d="M20 38 Q32 36 42 42 M58 42 Q68 36 80 38" {W}/>',
        "anchor": f'<circle cx="50" cy="16" r="9" {W}/>'
                  f'<path d="M50 25 L50 84 M32 42 L68 42 M14 62 Q14 84 50 84 Q86 84 86 62" {W}/>'
                  f'<path d="M14 62 L4 56 M14 62 L4 72 M86 62 L96 56 M86 62 L96 72" {W}/>',
        "note": f'<path d="M40 20 L76 14 L76 62" {W}/>'
                f'<path d="M40 30 L76 24" {W}/>'
                f'<ellipse cx="30" cy="70" rx="12" ry="9" transform="rotate(-20 30 70)" fill="#ffffff" fill-opacity="0.35" {W}/>'
                f'<ellipse cx="66" cy="64" rx="12" ry="9" transform="rotate(-20 66 64)" fill="#ffffff" fill-opacity="0.35" {W}/>'
                f'<path d="M40 20 L40 62" {W}/>',
        "fish": f'<path d="M12 50 Q34 22 64 30 Q82 34 88 50 Q82 66 64 70 Q34 78 12 50 Z" fill="#ffffff" fill-opacity="0.22" {W}/>'
                f'<path d="M88 50 L98 34 L98 66 Z" fill="#ffffff" fill-opacity="0.3" {W}/>'
                f'<circle cx="30" cy="46" r="3.5" fill="#ffffff"/>'
                f'<path d="M50 30 L56 18 M50 70 L56 82" {W}/>',
        "crown": f'<path d="M12 72 L8 30 L30 48 L50 18 L70 48 L92 30 L88 72 Z" fill="#ffffff" fill-opacity="0.26" {W}/>'
                 f'<path d="M12 80 L88 80" {W}/>'
                 f'<circle cx="50" cy="60" r="4" fill="#ffffff"/>',
        "fist": f'<path d="M28 52 L28 34 Q28 28 34 28 Q40 28 40 34 L40 46 L40 26 Q40 20 46 20 Q52 20 52 26 L52 44 L52 24 Q52 18 58 18 Q64 18 64 24 L64 44 L64 30 Q64 24 70 24 Q76 24 76 30 L76 62 Q76 84 54 88 L44 88 Q28 84 24 68 Z" fill="#ffffff" fill-opacity="0.24" {W}/>'
                f'<path d="M28 62 L76 62" {W}/>',
        "skull": f'<path d="M24 48 Q24 20 50 20 Q76 20 76 48 Q76 66 62 72 L62 82 L38 82 L38 72 Q24 66 24 48 Z" fill="#ffffff" fill-opacity="0.24" {W}/>'
                 f'<circle cx="39" cy="48" r="7" fill="#ffffff"/><circle cx="61" cy="48" r="7" fill="#ffffff"/>'
                 f'<path d="M46 64 L54 64 M12 78 L88 20 M12 20 L88 78" {W}/>',
        "bolt": f'<path d="M56 6 L24 54 L46 54 L38 94 L78 42 L54 42 Z" fill="#ffffff" fill-opacity="0.3" {W}/>',
        "eye": f'<path d="M8 50 Q50 12 92 50 Q50 88 8 50 Z" fill="#ffffff" fill-opacity="0.2" {W}/>'
               f'<circle cx="50" cy="50" r="16" {W}/>'
               f'<circle cx="50" cy="50" r="6" fill="#ffffff"/>',
        "snow": f'<path d="M50 8 L50 92 M14 29 L86 71 M14 71 L86 29" {W}/>'
                f'<path d="M50 18 L42 26 M50 18 L58 26 M50 82 L42 74 M50 82 L58 74" {W}/>'
                f'<path d="M22 33 L32 33 M22 33 L26 41 M78 67 L68 67 M78 67 L74 59" {W}/>',
    }
    body = icons.get(name, icons["compass"])
    return ('<g fill="none" stroke="#ffffff" stroke-width="4.5" '
            'stroke-linecap="round" stroke-linejoin="round">' + body + '</g>')


# --------------------------------------------------------------------------- 通缉令 SVG

def render_wanted(c: dict, d: date, serial: int, total: int) -> str:
    rnd = random.Random(digest(d.isoformat()))
    spots = []
    for _ in range(46):
        x, y, r = rnd.randint(24, 596), rnd.randint(24, 856), round(rnd.uniform(1.2, 4.6), 1)
        spots.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#7a5a2c" opacity="{round(rnd.uniform(0.04, 0.13), 2)}"/>')

    en = c["en"]
    en_size = 20 if len(en) <= 18 else (17 if len(en) <= 24 else 14)
    fruit = c["fruit"] if len(c["fruit"]) <= 21 else c["fruit"][:20] + "…"
    crew = c["crew"] if len(c["crew"]) <= 20 else c["crew"][:19] + "…"
    bounty = bounty_number(c)
    bounty_size = 44 if len(bounty) <= 16 else 38
    bounty_line = f"{bounty_desc(c)} · {c['role']}" if c["bounty"] else f"悬赏金未公布 · {c['role']}"

    # 角色立绘以 base64 内嵌，SVG 作为 <img> 加载时也能显示，不依赖外部资源
    img_path = CHAR_IMAGES / f"{c['id']}.png"
    if img_path.exists():
        b64 = base64.b64encode(img_path.read_bytes()).decode("ascii")
        portrait = (f'<image xlink:href="data:image/png;base64,{b64}" x="100" y="232" '
                    f'width="420" height="240" preserveAspectRatio="xMidYMid meet"/>')
    else:  # 缺图时退回抽象图标，保证脚本永不失败
        portrait = (f'<g transform="translate(250, 280) scale(1.2)">'
                    f'{icon_svg(c["symbol"])}</g>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="620" height="880" viewBox="0 0 620 880" role="img" aria-label="{esc(c['zh'])} 的通缉令">
<defs>
  <linearGradient id="paper" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#f8eed4"/><stop offset="0.55" stop-color="#eddaB4"/><stop offset="1" stop-color="#ddc398"/>
  </linearGradient>
  <linearGradient id="portrait" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{c['c1']}"/><stop offset="1" stop-color="{c['c2']}"/>
  </linearGradient>
  <linearGradient id="photoBg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#f9efd8"/><stop offset="1" stop-color="#e7d3ad"/>
  </linearGradient>
  <radialGradient id="vignette">
    <stop offset="0.55" stop-color="#000000" stop-opacity="0"/><stop offset="1" stop-color="#5a3b18" stop-opacity="0.30"/>
  </radialGradient>
</defs>
<rect width="620" height="880" fill="url(#paper)"/>
<g>{''.join(spots)}</g>
<rect width="620" height="880" fill="url(#vignette)"/>
<rect x="16" y="16" width="588" height="848" fill="none" stroke="#4a3218" stroke-width="3"/>
<rect x="25" y="25" width="570" height="830" fill="none" stroke="#4a3218" stroke-width="1" opacity="0.55"/>
<g fill="#4a3218" opacity="0.55">
  <circle cx="36" cy="36" r="4"/><circle cx="584" cy="36" r="4"/><circle cx="36" cy="844" r="4"/><circle cx="584" cy="844" r="4"/>
</g>

<text x="310" y="66" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif" font-size="14" letter-spacing="7" fill="#5a3b18">MARINE HEADQUARTERS · 世界政府</text>
<text x="310" y="164" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif" font-size="96" font-weight="bold" letter-spacing="10" fill="#2b1c0d">WANTED</text>
<text x="310" y="194" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif" font-size="16" letter-spacing="11" fill="#5a3b18">DEAD OR ALIVE</text>
<path d="M70 206 L550 206" stroke="#4a3218" stroke-width="1.5" opacity="0.6"/>

<rect x="68" y="220" width="484" height="336" rx="5" fill="#2f2113" opacity="0.9"/>
<rect x="76" y="228" width="468" height="320" rx="3" fill="url(#photoBg)"/>
{portrait}
<rect x="76" y="476" width="468" height="72" fill="{c['c2']}" opacity="0.96"/>
<path d="M76 477 L544 477" stroke="{c['c1']}" stroke-width="3"/>
<text x="310" y="503" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif" font-size="{en_size}" font-weight="bold" letter-spacing="2" fill="#ffffff">{esc(en)}</text>
<text x="310" y="531" text-anchor="middle" font-family="'Microsoft YaHei', 'PingFang SC', sans-serif" font-size="20" font-weight="bold" fill="#fff3dc">{esc(c['zh'])}</text>
<text x="532" y="542" text-anchor="end" font-family="Georgia, serif" font-size="11" letter-spacing="1" fill="#ffffff" opacity="0.75">No. {serial:03d}/{total:03d}</text>

<path d="M70 578 L550 578" stroke="#4a3218" stroke-width="1.5" opacity="0.6"/>
<text x="310" y="610" text-anchor="middle" font-family="Georgia, serif" font-size="15" letter-spacing="8" fill="#5a3b18">BOUNTY · 悬赏金</text>
<text x="310" y="662" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif" font-size="{bounty_size}" font-weight="bold" fill="#2b1c0d">{esc(bounty)}</text>
<text x="310" y="694" text-anchor="middle" font-family="'Microsoft YaHei', 'PingFang SC', sans-serif" font-size="18" fill="#5a3b18">{esc(bounty_line)}</text>

<path d="M70 718 L550 718" stroke="#4a3218" stroke-width="1.5" opacity="0.6"/>
<text x="82" y="752" font-family="'Microsoft YaHei', 'PingFang SC', sans-serif" font-size="16" fill="#3b2813"><tspan font-family="Georgia, serif" font-size="13" letter-spacing="2">CREW</tspan>　{esc(crew)}</text>
<text x="82" y="782" font-family="'Microsoft YaHei', 'PingFang SC', sans-serif" font-size="16" fill="#3b2813"><tspan font-family="Georgia, serif" font-size="13" letter-spacing="2">FRUIT</tspan>　{esc(fruit)}</text>
<text x="82" y="818" font-family="Georgia, serif" font-size="14" letter-spacing="2" fill="#5a3b18">{d.strftime('%Y.%m.%d')} · DAILY WANTED</text>

<g transform="translate(498, 782) rotate(-16)" opacity="0.72">
  <circle r="54" fill="none" stroke="#a12b1e" stroke-width="5"/>
  <circle r="44" fill="none" stroke="#a12b1e" stroke-width="1.6"/>
  <text x="0" y="-2" text-anchor="middle" font-family="Georgia, serif" font-size="17" font-weight="bold" letter-spacing="1.5" fill="#a12b1e">MARINE</text>
  <text x="0" y="20" text-anchor="middle" font-family="Georgia, serif" font-size="10" letter-spacing="1.5" fill="#a12b1e">WORLD GOV.</text>
</g>
</svg>'''


# --------------------------------------------------------------------------- README

def render_readme(c: dict, d: date, hist: list, chars: list, meta: dict) -> str:
    template = TEMPLATE_FILE.read_text(encoding="utf-8")
    by_id = {x["id"]: x for x in chars}
    greeting = GREETINGS[digest("greeting:" + d.isoformat()) % len(GREETINGS)]
    serial = [x["id"] for x in chars].index(c["id"]) + 1
    values = {
        "DATE_LABEL": date_label(d),
        "WEEKDAY": WEEKDAYS[d.weekday()],
        "DATE_COMPACT": d.strftime("%Y%m%d"),
        "DATE_ISO": d.isoformat(),
        "GREETING": greeting,
        "CHAR_ZH": c["zh"],
        "CHAR_EN": c["en"],
        "EPITHET": c["epithet"],
        "LINE": c["line"],
        "BOUNTY_NUM": bounty_number(c),
        "BOUNTY_ZH": c["bounty_zh"],
        "BOUNTY_DESC": bounty_desc(c),
        "CREW": c["crew"],
        "ROLE": c["role"],
        "FRUIT": c["fruit"],
        "HAKI": c["haki"],
        "BIRTHDAY": c["birthday"],
        "HEIGHT": c["height"],
        "DEBUT": c["debut"],
        "TAG": c["tag"],
        "SERIAL": f"{serial:03d}",
        "TOTAL": f"{len(chars):03d}",
        "STAT_ROWS": stat_rows(c),
        "HISTORY_ROWS": history_rows(hist, by_id),
        "DATA_NOTE": meta["note"],
    }
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template


def update_history(hist: list, c: dict, d: date) -> list:
    hist = [h for h in hist if h.get("date") != d.isoformat()]
    hist.append({"date": d.isoformat(), "id": c["id"], "zh": c["zh"]})
    return hist[-60:]


# --------------------------------------------------------------------------- 预览页

PREVIEW_HTML = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ONE PIECE · 每日通缉令 · 效果预览</title>
<style>
  :root{--bg:#f6f8fa;--card:#ffffff;--line:#d8dee4;--text:#1f2328;--muted:#59636e;--accent:#a12b1e;--gold:#b8893a}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",Helvetica,Arial,sans-serif;line-height:1.6}
  header{background:#fff;border-bottom:1px solid var(--line);padding:18px 24px;position:sticky;top:0;z-index:10;box-shadow:0 1px 3px rgba(31,35,40,.04)}
  .head-inner{max-width:1000px;margin:0 auto;display:flex;flex-wrap:wrap;gap:14px;align-items:center;justify-content:space-between}
  .brand{font-weight:700;font-size:17px;letter-spacing:.3px}
  .brand span{color:var(--accent)}
  .sub{font-size:12px;color:var(--muted);font-weight:400;margin-left:10px}
  .chips{display:flex;gap:7px;flex-wrap:wrap;align-items:center}
  button{font:inherit;cursor:pointer;border:1px solid var(--line);background:#fff;color:var(--text);border-radius:20px;padding:5px 13px;font-size:12px;transition:.15s}
  button:hover{border-color:#9aa4ae;background:#f3f4f6}
  button.active{background:#24292f;color:#fff;border-color:#24292f}
  button.play{border-color:var(--gold);color:#7a5a12}
  .wrap{max-width:1000px;margin:0 auto;padding:28px 20px 60px}
  .notice{background:#fff8e6;border:1px solid #f0dca6;border-radius:8px;padding:12px 16px;font-size:13px;color:#6b511a;margin-bottom:22px}
  .notice b{color:#4a3510}
  .repo-bar{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--muted);padding:10px 4px}
  .repo-bar svg{flex:none}
  .readme{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:36px 40px 30px;box-shadow:0 1px 2px rgba(31,35,40,.04)}
  .r-head{border-bottom:1px solid var(--line);padding-bottom:6px;margin-bottom:24px;display:flex;align-items:center;gap:9px;font-size:14px;color:var(--muted)}
  .center{text-align:center}
  .poster{width:340px;max-width:100%;border-radius:3px;box-shadow:0 6px 22px rgba(60,40,15,.20);margin:6px auto 22px;display:block}
  h1{font-size:27px;line-height:1.35;margin:6px 0 10px;border-bottom:1px solid var(--line);padding-bottom:12px}
  h2{font-size:20px;margin:30px 0 12px;border-bottom:1px solid var(--line);padding-bottom:8px}
  .lead{font-size:16px;color:#3d444d;margin:0 0 6px}
  .meta{font-size:12px;color:var(--muted);margin-bottom:4px}
  table{border-collapse:collapse;width:100%;font-size:14px;margin:6px 0 4px}
  th,td{border:1px solid var(--line);padding:8px 12px;text-align:left}
  th{background:#f6f8fa;font-weight:600}
  td:first-child{width:150px;color:var(--muted)}
  code{background:#eff1f3;border-radius:4px;padding:1px 6px;font-size:12.5px;letter-spacing:-1px;color:#7a4a12}
  blockquote{border-left:4px solid var(--gold);margin:10px 0;padding:6px 16px;background:#fffbf2;color:#4a3a1c;font-size:15px}
  .foot{margin-top:30px;padding-top:18px;border-top:1px solid var(--line);text-align:center;font-size:12.5px;color:var(--muted)}
  .foot strong{color:#3d444d}
  .tabs{display:flex;gap:8px;margin:26px 0 10px}
  .src{display:none;background:#fff;border:1px solid var(--line);border-radius:6px;padding:18px}
  .src.show{display:block}
  .src pre{white-space:pre-wrap;word-break:break-word;font-size:12px;line-height:1.55;margin:0;color:#3d444d;font-family:ui-monospace,SFMono-Regular,Consolas,monospace}
  .files{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin-top:14px}
  .file{background:#fff;border:1px solid var(--line);border-radius:6px;padding:12px 14px;font-size:12.5px}
  .file code{background:none;padding:0;color:#0969da;font-weight:600}
  .file p{margin:5px 0 0;color:var(--muted)}
</style>
</head>
<body>
<header><div class="head-inner">
  <div class="brand">🏴‍☠️ ONE PIECE <span>· 每日通缉令</span><span class="sub">效果预览 · 点击日期切换「每一天」</span></div>
  <div class="chips" id="chips"></div>
  <button class="play" id="play">▶ 自动轮播</button>
</div></header>

<div class="wrap">
  <div class="notice"><b>这是 README 在 GitHub 上渲染后的近似效果。</b> 默认展示今天，其余 5 天是按同一套「每日选角」算法模拟的连续日期 —— 可以看到角色立绘、悬赏金、主题色每天都会变。仓库里的 <code>README.md</code> 与 <code>assets/wanted.svg</code> 每天由 GitHub Actions 自动重写并提交。</div>
  <div class="repo-bar">
    <svg width="16" height="16" viewBox="0 0 16 16" fill="#59636e"><path d="M2 2.5A2.5 2.5 0 0 1 4.5 0h7a2.5 2.5 0 0 1 2.5 2.5v11a.5.5 0 0 1-.8.4L8 11.3l-5.2 2.6a.5.5 0 0 1-.8-.4v-11Z"/></svg>
    <span>README.md</span><span>·</span><span id="repo-date"></span>
  </div>
  <div class="readme" id="readme"></div>

  <div class="tabs"><button id="tab-src">查看 README.md 源码</button></div>
  <div class="src" id="src"><pre id="src-text"></pre></div>

  <h2 style="margin-top:36px">📦 仓库里会有什么</h2>
  <div class="files">
    <div class="file"><code>README.md</code><p>每天自动重写的成品，就是上面这张页面</p></div>
    <div class="file"><code>assets/wanted.svg</code><p>每天重绘的通缉令，角色图内嵌在 SVG 里</p></div>
    <div class="file"><code>assets/characters/</code><p>48 位角色的立绘，本地存放，不依赖外链</p></div>
    <div class="file"><code>characters.json</code><p>角色资料库，想加角色改这里就行</p></div>
    <div class="file"><code>generate.py</code><p>选角 + 生成海报 + 生成 README，纯标准库</p></div>
    <div class="file"><code>.github/workflows/daily.yml</code><p>每天 UTC 00:00（北京 08:00）自动运行并提交</p></div>
    <div class="file"><code>history.json</code><p>登场记录，避免短期内抽到同一个角色</p></div>
  </div>
</div>

<script id="payload" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('payload').textContent);
let idx = 0, timer = null;
const chips = document.getElementById('chips');
DATA.forEach((it, i) => {
  const b = document.createElement('button');
  b.textContent = it.short;
  b.onclick = () => show(i);
  chips.appendChild(b);
});
function esc(s){return String(s).replace(/[&<>"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[ch]));}
function bar(v){const n = Math.round(v/10); return '▓'.repeat(n) + '░'.repeat(10-n);}
function show(i){
  idx = i;
  const it = DATA[i];
  [...chips.children].forEach((b,k) => b.classList.toggle('active', k===i));
  document.getElementById('repo-date').textContent = 'Last commit · ' + it.label;
  const t = it.info.tables_rows;
  document.getElementById('readme').innerHTML = `
    <div class="r-head">📖 README.md · 每天自动更新</div>
    <div class="center">
      <img class="poster" alt="今日通缉令" src="data:image/svg+xml;base64,${it.svg}">
      <h1>🏴‍☠️ 今日的悬赏目标：${esc(it.zh)}</h1>
      <p class="lead">「${esc(it.line)}」</p>
      <p class="meta">${esc(it.greeting)}</p>
      <p class="meta">ONE PIECE · 每日通缉令 · ${esc(it.label)}（${esc(it.weekday)}） · No. ${esc(it.serial)} / ${esc(it.total)}</p>
    </div>
    <h2>📋 悬赏档案</h2>
    <table><tbody>${t}</tbody></table>
    <h2>⚔️ 能力评估</h2>
    <table><thead><tr><th>能力</th><th>数值</th><th>条</th></tr></thead><tbody>
      ${it.stats.map((v,k) => `<tr><td>${['⚔️ 攻击','🛡️ 防御','💨 速度','🧠 智谋','✨ 霸气'][k]}</td><td>${v}</td><td><code>${bar(v)}</code></td></tr>`).join('')}
    </tbody></table>
    <h2>💬 今日一句</h2>
    <blockquote>${esc(it.line)}</blockquote>
    <h2>🗓️ 最近登场</h2>
    <table><thead><tr><th>日期</th><th>角色</th><th>悬赏金</th></tr></thead><tbody>
      ${it.history.map(h => `<tr><td>${esc(h[0])}</td><td>${esc(h[1])}</td><td>${esc(h[2])}</td></tr>`).join('')}
    </tbody></table>
    <div class="foot">🌟 <strong>这个 README 每天自动换一位海贼王角色</strong> 🌟<br>
    每天 UTC 00:00（北京时间 08:00）由 GitHub Actions 更新 · 也可在 Actions 页手动触发<br>
    共收录 ${esc(it.total)} 位角色 · 立绘取自 One Piece Wiki / Vivre Card 粉丝资料库 · 非商业粉丝展示 · 图片本地内嵌，无外链依赖</div>`;
  document.getElementById('src-text').textContent = it.readme;
}
document.getElementById('tab-src').onclick = function(){
  const el = document.getElementById('src');
  el.classList.toggle('show');
  this.textContent = el.classList.contains('show') ? '收起源码' : '查看 README.md 源码';
};
document.getElementById('play').onclick = function(){
  if(timer){clearInterval(timer);timer=null;this.textContent='▶ 自动轮播';return;}
  this.textContent='⏸ 暂停轮播';
  timer = setInterval(() => show((idx+1) % DATA.length), 2600);
};
show(0);
</script>
</body>
</html>
'''


def render_preview(days: list, total: int) -> str:
    payload = []
    for item in days:
        c, d, hist = item["c"], item["d"], item["hist"]
        svg = item["svg"]
        serial = item["serial"]
        rows = [
            ("🪙 悬赏金", f"<b>{esc(bounty_number(c))}</b>（{esc(bounty_desc(c))}）"),
            ("🏴‍☠️ 所属", esc(f"{c['crew']} · {c['role']}")),
            ("🍈 恶魔果实", esc(c["fruit"])),
            ("✨ 霸气", esc(c["haki"])),
            ("🎂 生日", esc(c["birthday"])),
            ("📏 身高", esc(c["height"])),
            ("🗺️ 初次登场", esc(c["debut"])),
            ("🏷️ 标签", esc(c["tag"])),
        ]
        table = "".join(f"<tr><td>{esc(k)}</td><td>{v}</td></tr>" for k, v in rows)
        by_id = item["by_id"]
        history = [[h["date"], by_id.get(h["id"], {}).get("zh", h.get("zh", "?")),
                    bounty_desc(by_id[h["id"]]) if h["id"] in by_id else "—"]
                   for h in reversed(hist[-7:])]
        payload.append({
            "short": f"{d.month}/{d.day}",
            "label": date_label(d),
            "weekday": WEEKDAYS[d.weekday()],
            "svg": base64.b64encode(svg.encode("utf-8")).decode("ascii"),
            "readme": item["readme"],
            "zh": c["zh"], "line": c["line"],
            "greeting": GREETINGS[digest("greeting:" + d.isoformat()) % len(GREETINGS)],
            "stats": c["stats"], "history": history,
            "serial": f"{serial:03d}", "total": f"{total:03d}",
            "info": {"tables_rows": table},
        })
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return PREVIEW_HTML.replace("__DATA__", data)


# --------------------------------------------------------------------------- 主流程

def main() -> None:
    ap = argparse.ArgumentParser(description="ONE PIECE 每日通缉令生成器")
    ap.add_argument("--date", help="指定日期 YYYY-MM-DD（默认今天 UTC）")
    ap.add_argument("--character", help="强制指定角色 id")
    ap.add_argument("--shuffle", action="store_true", help="忽略日期，随机抽一位")
    ap.add_argument("--skip-preview", action="store_true", help="不生成 preview.html")
    args = ap.parse_args()

    chars, meta = load_data()
    by_id = {c["id"]: c for c in chars}
    total = len(chars)
    d = date.fromisoformat(args.date) if args.date else datetime.now(CST).date()
    hist = load_history()

    c = pick_character(d, chars, hist, args.character, args.shuffle)
    serial = [x["id"] for x in chars].index(c["id"]) + 1

    svg = render_wanted(c, d, serial, total)
    new_hist = update_history(hist, c, d)
    readme = render_readme(c, d, new_hist, chars, meta)

    write_text(WANTED_FILE, svg)
    write_text(README_FILE, readme)
    write_text(HISTORY_FILE, json.dumps(new_hist, ensure_ascii=False, indent=2) + "\n")

    if not args.skip_preview:
        # 用「空历史 + 今天」重放连续 6 天，模拟每日自动切换的真实效果
        days = []
        sim_hist: list = []
        for offset in range(6):
            day = d + timedelta(days=offset)
            pick = c if offset == 0 else pick_character(day, chars, sim_hist)
            sim_hist = update_history(sim_hist, pick, day)
            s = svg if offset == 0 else render_wanted(pick, day, [x["id"] for x in chars].index(pick["id"]) + 1, total)
            r = readme if offset == 0 else render_readme(pick, day, sim_hist, chars, meta)
            days.append({"c": pick, "d": day, "hist": list(sim_hist), "svg": s,
                         "readme": r, "serial": [x["id"] for x in chars].index(pick["id"]) + 1,
                         "by_id": by_id})
        write_text(PREVIEW_FILE, render_preview(days, total))

    print(f"[{d.isoformat()}] 今日角色: {c['zh']} ({c['en']}) · 悬赏 {c['bounty_zh']} 贝利")
    print(f"  已生成 README.md / assets/wanted.svg / history.json"
          + ("" if args.skip_preview else " / preview.html"))


if __name__ == "__main__":
    main()
