#!/usr/bin/env python3
"""归档 bing-wallpaper.md 并为每个年度归档生成展示文件。

规则：
- 当年记录保留在 bing-wallpaper.md，往年记录归档到 archive/bing-wallpaper-YYYY.md；
- 为 archive/ 下每个年度文件生成 showcase/bing-wallpaper-YYYY.md 展示文件（图片墙，类似 README）；
- 幂等：可重复执行，已归档记录不丢失，展示文件每次重建。

用于 GitHub Actions 月度定时归档任务（支持手动触发），也可在本地一次性迁移历史数据。
"""
import re
from datetime import date
from pathlib import Path

# 仓库根目录（脚本位于 scripts/ 下，故向上取一级）
ROOT = Path(__file__).resolve().parent.parent
BING_FILE = ROOT / "bing-wallpaper.md"
ARCHIVE_DIR = ROOT / "archive"
SHOWCASE_DIR = ROOT / "showcase"
HEADER = "## Bing Wallpaper"
# 匹配形如 "2026-10-14 | [描述](链接) " 的记录行
ENTRY_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \| ")
# 解析记录行，提取日期、描述、图片地址
ENTRY_PARSE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}) \| \[(.*)\]\((.*)\)\s*$")
# 缩略图参数，与 Java 端 Images.toString() 保持一致
SMALL_SUFFIX = "&pid=hp&w=384&h=216&rs=1&c=4"


def read_entries(path: Path):
    """读取文件中的壁纸记录（忽略标题行与空行），按原顺序返回。"""
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if ENTRY_RE.match(line):
            entries.append(line)
    return entries


def write_entries(path: Path, entries):
    """将壁纸记录写入文件，格式与 Java 端保持一致：标题行 + 逐条记录（空行分隔）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    parts = [HEADER + "\n"]
    for entry in entries:
        parts.append(entry + "\n\n")
    path.write_text("".join(parts), encoding="utf-8")


def parse_entry(entry: str):
    """解析记录行，返回 (日期, 描述, 图片地址)，解析失败返回 None。"""
    matched = ENTRY_PARSE_RE.match(entry)
    if not matched:
        return None
    return matched.group(1), matched.group(2), matched.group(3)


def build_showcase(year: str, entries) -> str:
    """生成图片墙展示内容（三列网格，样式与 README 一致）。"""
    lines = [f"{HEADER} {year}", "", "|      |      |      |", "| :----: | :----: | :----: |"]
    row = []
    for entry in entries:
        parsed = parse_entry(entry)
        if parsed is None:
            continue
        day, desc, url = parsed
        row.append(f"![]({url}{SMALL_SUFFIX}){day} [download 4k]({url})")
        if len(row) == 3:
            lines.append("|" + "|".join(row) + "|")
            row = []
    if row:
        lines.append("|" + "|".join(row) + "|")
    return "\n".join(lines) + "\n"


def write_showcase(year: str, entries) -> Path:
    """为指定年度生成展示文件 showcase/bing-wallpaper-YYYY.md。"""
    path = SHOWCASE_DIR / f"bing-wallpaper-{year}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_showcase(year, entries), encoding="utf-8")
    return path


def main():
    """拆分主文件：当年写入 bing-wallpaper.md，往年归档到 archive/ 并重建展示文件。"""
    entries = read_entries(BING_FILE)
    current_year = str(date.today().year)

    by_year = {}
    for entry in entries:
        by_year.setdefault(entry[:4], []).append(entry)

    current_entries = []
    archived_years = []
    for year, items in by_year.items():
        if year == current_year:
            current_entries.extend(items)
        elif re.fullmatch(r"\d{4}", year):
            archived_years.append((year, items))

    # 主文件仅保留当年记录
    current_entries.sort(key=lambda e: e[:10], reverse=True)
    write_entries(BING_FILE, current_entries)

    # 往年记录合并进各自归档文件（与已有归档去重，按日期倒序）
    for year, items in archived_years:
        archive_file = ARCHIVE_DIR / f"bing-wallpaper-{year}.md"
        existing = read_entries(archive_file)
        merged = sorted(set(existing + items), key=lambda e: e[:10], reverse=True)
        write_entries(archive_file, merged)

    # 为 archive/ 下每个年度文件重建展示文件
    archive_files = sorted(ARCHIVE_DIR.glob("bing-wallpaper-*.md"), key=lambda p: p.name, reverse=True)
    for archive_file in archive_files:
        matched = re.fullmatch(r"bing-wallpaper-(\d{4})\.md", archive_file.name)
        if not matched:
            continue
        year = matched.group(1)
        entries_of_year = read_entries(archive_file)
        write_showcase(year, entries_of_year)
        print(f"showcase {year}: {len(entries_of_year)} entries -> showcase/bing-wallpaper-{year}.md")

    print(f"current year {current_year}: {len(current_entries)} entries -> bing-wallpaper.md")


if __name__ == "__main__":
    main()
