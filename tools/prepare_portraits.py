#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新裁切角色立绘（可选工具，仅本地使用，需要 Pillow）。

从 characters.json 里的 image 字段读取来源文件名，下载原始立绘，
裁成 420x240 的透明 PNG 存到 assets/characters/。
主生成流程 generate.py 不依赖本脚本，也不依赖 Pillow。

用法:
    python tools/prepare_portraits.py                # 重新生成全部立绘
    python tools/prepare_portraits.py --keep-cache   # 保留下载的原图缓存
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote

from PIL import Image

BASE = Path(__file__).resolve().parent.parent
CACHE = BASE / ".cache" / "onepiece_raw"
OUT = BASE / "assets" / "characters"
RAW_REPO = "https://github.com/xdinterface/op-trmnl-plugin-data/raw/refs/heads/main/images/"

# 取景窗口至少覆盖原图上部的这个比例，保证头部完整露出
MIN_RATIO = 0.58
# 少数「大头特写」需要更大的取景范围
OVERRIDE_RATIO = {"chopper": 0.62}


def sources() -> list[tuple[str, str]]:
    data = json.loads((BASE / "characters.json").read_text(encoding="utf-8"))
    return [(c["id"], c["image"]) for c in data["characters"] if c.get("image")]


def download(item: tuple[str, str]) -> tuple[str, bool]:
    cid, name = item
    dest = CACHE / f"{cid}.png"
    if dest.exists() and dest.stat().st_size > 20000:
        try:
            Image.open(dest).load()
            return cid, True
        except Exception:
            pass
    url = RAW_REPO + quote(name, safe=".-_")
    for _ in range(3):
        r = subprocess.run(
            ["curl", "-sL", "--max-time", "90", "-o", str(dest), "-w", "%{http_code}", url],
            capture_output=True, text=True,
        )
        if r.returncode == 0 and r.stdout.strip() == "200" and dest.exists():
            try:
                Image.open(dest).load()
                return cid, True
            except Exception:
                pass
    return cid, False


def prepare(cid: str) -> int:
    im = Image.open(CACHE / f"{cid}.png").convert("RGBA")
    bbox = im.getchannel("A").getbbox()          # 去掉四周透明留白
    if bbox:
        im = im.crop(bbox)
    w, h = im.size

    fill_h = round(240 / (420 / w))              # 按宽度填满时需要的取景高度
    keep_h = round(h * OVERRIDE_RATIO.get(cid, MIN_RATIO))
    crop_h = min(h, max(fill_h, keep_h))         # 取较大者 => 头部不会被挤出去

    upper = im.crop((0, 0, w, crop_h))
    scale = min(420 / upper.width, 240 / upper.height)   # 等比缩放，不拉伸
    new_w = max(1, round(upper.width * scale))
    new_h = max(1, round(upper.height * scale))
    resized = upper.resize((new_w, new_h), Image.LANCZOS)

    canvas = Image.new("RGBA", (420, 240), (0, 0, 0, 0))
    canvas.alpha_composite(resized, ((420 - new_w) // 2, (240 - new_h) // 2))
    out = OUT / f"{cid}.png"
    canvas.save(out, optimize=True)
    return out.stat().st_size


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-cache", action="store_true", help="保留下载的原始立绘缓存")
    args = ap.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    src = sources()

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(download, src))
    failed = [cid for cid, ok in results if not ok]
    print(f"downloaded: {len(src) - len(failed)}/{len(src)}")
    if failed:
        print("FAILED:", ", ".join(failed))

    sizes = []
    for cid, ok in results:
        if not ok:
            continue
        try:
            sizes.append(prepare(cid))
        except Exception as e:
            print("prepare failed:", cid, str(e)[:100])
    if sizes:
        print(f"portraits: {len(sizes)} | total {sum(sizes)/1024/1024:.2f} MB "
              f"| avg {sum(sizes)/len(sizes)/1024:.0f} KB | max {max(sizes)/1024:.0f} KB")

    if not args.keep_cache:
        shutil.rmtree(CACHE, ignore_errors=True)
        print("raw cache removed")


if __name__ == "__main__":
    main()
