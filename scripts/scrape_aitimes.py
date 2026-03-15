#!/usr/bin/env python3
"""AITimes 기사 목록 스크래핑 스크립트.

최근 N일간의 기사 제목, 날짜, URL을 JSON으로 stdout에 출력합니다.

Usage:
    python scripts/scrape_aitimes.py [--days 7] [--pages 5]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.aitimes.com/news/articleList.html"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}


def fetch_page(page: int) -> list[dict]:
    """한 페이지의 기사 목록을 파싱하여 반환."""
    resp = requests.get(BASE_URL, params={"page": page}, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    articles = []
    subjects = soup.select("h2.altlist-subject")
    for subject in subjects:
        link = subject.find("a")
        if not link:
            continue
        title = link.get_text(strip=True)
        url = link.get("href", "")
        if url and not url.startswith("http"):
            url = "https://www.aitimes.com" + url

        # 날짜는 같은 기사 항목 내 3번째 altlist-info-item
        parent = subject.find_parent(re.compile(r"li|div"), class_=re.compile(r"altlist-.+-item"))
        date_text = ""
        if parent:
            info_items = parent.select("div.altlist-info-item")
            if len(info_items) >= 3:
                date_text = info_items[2].get_text(strip=True)

        articles.append({"title": title, "url": url, "date_text": date_text})
    return articles


def parse_date(date_text: str) -> datetime | None:
    """'MM-DD HH:MM' 또는 'YYYY.MM.DD HH:MM' 형식을 파싱."""
    now = datetime.now()
    for fmt in ("%m-%d %H:%M", "%Y.%m.%d %H:%M", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(date_text.strip(), fmt)
            if dt.year == 1900:  # 연도 없는 포맷
                dt = dt.replace(year=now.year)
            return dt
        except ValueError:
            continue
    return None


def main():
    parser = argparse.ArgumentParser(description="AITimes 기사 수집")
    parser.add_argument("--days", type=int, default=7, help="최근 N일 (기본: 7)")
    parser.add_argument("--pages", type=int, default=5, help="검색할 페이지 수 (기본: 5)")
    args = parser.parse_args()

    cutoff = datetime.now() - timedelta(days=args.days)
    results = []
    stop = False

    for page in range(1, args.pages + 1):
        if stop:
            break
        articles = fetch_page(page)
        for article in articles:
            dt = parse_date(article["date_text"])
            if dt and dt < cutoff:
                stop = True
                break
            published_date = dt.strftime("%Y-%m-%d") if dt else ""
            results.append({
                "title": article["title"],
                "published_date": published_date,
                "url": article["url"],
            })

    json.dump(results, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
