"""从 SPONSORS.md 生成 sponsors.json。

SPONSORS.md 是人工维护的赞助者名单（GitHub 上直接可读），
本脚本将其解析为结构化 JSON，供应用内赞助页通过 CDN 拉取。

档位规则：
- ¥200/月：昵称置顶、加粗，附 👑 标识
- ¥80/月：昵称加粗展示
- ¥30/月：列入赞助者名单

输出按档位从高到低排序，同档保持文件内顺序（即赞助时间先后）。
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = ROOT / "SPONSORS.md"
OUTPUT_PATH = ROOT / "sponsors.json"

# 从形如 “## 👑 土豪赞助（¥200/月）” 的小节标题中提取档位金额
TIER_RE = re.compile(r"¥\s*(\d+)")
# 水平分隔线（--- / *** / ___）
HR_RE = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")
# 空档位的占位符
EMPTY_PLACEHOLDERS = {"暂无", "暫無", ""}


def _read(path: Path) -> str:
    return path.read_bytes().decode("utf-8-sig")


def _clean_name(raw: str) -> str:
    """从列表项中提取纯净昵称，去除列表标记、皇冠 emoji 与加粗/斜体标记。"""
    name = raw.strip()
    name = re.sub(r"^[-*+]\s+", "", name)
    name = name.replace("👑", "")
    name = name.replace("**", "")
    name = name.replace("__", "")
    return name.strip().strip("*_").strip()


def parse_sponsors(markdown: str) -> list[dict]:
    sponsors: list[dict] = []
    current_tier: int | None = None
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            match = TIER_RE.search(stripped)
            current_tier = int(match.group(1)) if match else None
            continue
        if current_tier is None:
            continue
        if not stripped.startswith(("-", "*", "+")):
            continue
        if HR_RE.match(stripped):
            continue
        if stripped.strip("*_ ") in EMPTY_PLACEHOLDERS:
            continue
        name = _clean_name(stripped)
        if not name:
            continue
        sponsors.append({"name": name, "tier": current_tier})
    # 按档位从高到低排序；Python 排序稳定，同档保持文件内顺序（赞助时间先后）
    sponsors.sort(key=lambda item: item["tier"], reverse=True)
    return sponsors


def main() -> None:
    markdown = _read(SOURCE_PATH)
    sponsors = parse_sponsors(markdown)
    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sponsors": sponsors,
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Generated {OUTPUT_PATH.name} with {len(sponsors)} sponsor(s).")


if __name__ == "__main__":
    main()
