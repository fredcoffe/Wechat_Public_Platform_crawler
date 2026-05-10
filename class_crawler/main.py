import argparse
import json
import math
import os
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from tqdm import tqdm

URL_LIST = "https://mp.weixin.qq.com/cgi-bin/appmsg"
PER_PAGE = 10


def build_regex(keyword: str) -> re.Pattern:
    pattern = ".*".join(map(re.escape, keyword))
    return re.compile(pattern, flags=re.IGNORECASE)


def require_value(name: str, value: str) -> str:
    if not value:
        raise RuntimeError(f"缺少配置 {name}，请在环境变量或命令行参数中提供。")
    return value


class WeChatArticleCrawler:
    def __init__(self, cookie: str, token: str, fakeid: str, keyword: str, workers: int = 5):
        self.cookie = require_value("WX_COOKIE", cookie)
        self.token = require_value("WX_TOKEN", token)
        self.fakeid = require_value("WX_FAKEID", fakeid)
        self.keyword = require_value("WX_KEYWORD", keyword)
        self.workers = max(1, workers)
        self.regex = build_regex(self.keyword)
        self.session = requests.Session()
        self.session.headers.update({
            "Cookie": self.cookie,
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/90.0.4430.212 Safari/537.36"
            ),
        })

    @property
    def base_params(self) -> dict[str, str]:
        return {
            "token": self.token,
            "lang": "zh_CN",
            "f": "json",
            "ajax": "1",
            "action": "list_ex",
            "begin": "0",
            "count": str(PER_PAGE),
            "query": "",
            "fakeid": self.fakeid,
            "type": "9",
        }

    def get_total_count(self) -> int:
        response = self.session.get(URL_LIST, params=self.base_params, timeout=15)
        response.raise_for_status()
        data = response.json()
        return int(data.get("app_msg_cnt", 0))

    def fetch_one_page(self, offset: int) -> list[dict]:
        params = self.base_params.copy()
        params["begin"] = str(offset)
        try:
            response = self.session.get(URL_LIST, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get("app_msg_list", []) or []
        except Exception as exc:
            print(f"抓取 offset={offset} 失败: {exc}")
            return []

    def collect_filtered_links(self) -> list[dict]:
        total = self.get_total_count()
        if total <= 0:
            print("未能获取文章总数，请检查 Cookie、token 和 fakeid 是否有效。")
            return []

        offsets = [index * PER_PAGE for index in range(math.ceil(total / PER_PAGE))]
        filtered: list[dict] = []
        empty_streak = 0

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {executor.submit(self.fetch_one_page, offset): offset for offset in offsets}
            for future in tqdm(as_completed(futures), total=len(offsets), desc="分页抓取进度"):
                page_items = future.result()
                if not page_items:
                    empty_streak += 1
                    if empty_streak >= 3:
                        break
                    continue

                empty_streak = 0
                for item in page_items:
                    title = item.get("title", "")
                    if self.regex.search(title):
                        filtered.append({
                            "title": title,
                            "link": item.get("link", ""),
                            "create_time": item.get("create_time", 0),
                        })
                time.sleep(random.uniform(0.05, 0.15))

        return filtered


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="按标题关键词抓取微信公众号文章列表。")
    parser.add_argument("--cookie", default=os.getenv("WX_COOKIE", ""), help="微信公众号后台 Cookie")
    parser.add_argument("--token", default=os.getenv("WX_TOKEN", ""), help="微信公众号后台 token")
    parser.add_argument("--fakeid", default=os.getenv("WX_FAKEID", ""), help="公众号 fakeid")
    parser.add_argument("--keyword", default=os.getenv("WX_KEYWORD", ""), help="标题筛选关键词")
    parser.add_argument("--workers", type=int, default=int(os.getenv("WX_MAX_WORKERS", "5")))
    parser.add_argument(
        "--output",
        default=os.getenv("WX_OUTPUT", "filtered_articles_content.json"),
        help="输出 JSON 文件名",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    crawler = WeChatArticleCrawler(args.cookie, args.token, args.fakeid, args.keyword, args.workers)
    results = crawler.collect_filtered_links()
    if not results:
        print("没有筛出符合条件的文章。")
        return

    output_path = Path(args.output)
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已保存 {len(results)} 条文章到 {output_path}")


if __name__ == "__main__":
    main()
