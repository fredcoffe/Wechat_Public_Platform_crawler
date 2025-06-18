import requests
import math
import time
import random
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm  # 用于进度条

# ———— 配置区 ————
URL_LIST = "https://mp.weixin.qq.com/cgi-bin/appmsg"

# 请替换为你从公众号后台 F12 Network 拷到的有效 Cookie
COOKIE = "你的 COOKIE"

# 请替换为你的 token 和 fakeid
TOKEN = "你的 token"
FAKEID = "fakeid"

# 每页抓 10 条（微信接口最大支持 10）
PER_PAGE = 10
# 并发线程数，可根据网络情况调整
MAX_WORKERS = 5

# 筛选标题时的关键字
KEYWORD = "关键字"

# ———— 构造正则模式 ————
# 将 KEYWORD 拆成一个个字符，用 '.*' 串联，得到 like "本.*科.*展"
# re.escape 确保如果 KEYWORD 中包含特殊字符（如 .、*、? 等）也能正确转义
pattern = ".*".join(map(re.escape, KEYWORD))
# 编译一个忽略大小写的正则，匹配模式：只要 title 中依次出现 KEYWORD 的各字符即可
regex = re.compile(pattern, flags=re.IGNORECASE)

# ———— 初始化 Session & 基础参数 ————
session = requests.Session()
session.headers.update({
    "Cookie": COOKIE,
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/90.0.4430.212 Safari/537.36"
    )
})

base_params = {
    "token": TOKEN,
    "lang": "zh_CN",
    "f": "json",
    "ajax": "1",
    "action": "list_ex",
    "begin": "0",
    "count": str(PER_PAGE),
    "query": "",
    "fakeid": FAKEID,
    "type": "9",
}


def get_total_count():
    """
    第一次请求只拿 app_msg_cnt，以便估算总页数。
    返回公众号标示的总文章数（int），或 0 如果失败。
    """
    try:
        resp = session.get(URL_LIST, params=base_params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return int(data.get("app_msg_cnt", 0))
    except Exception:
        return 0


def fetch_one_page(offset):
    """
    根据 offset（即 begin）拉取一页列表：返回该页的 app_msg_list（list）。
    如果请求失败或没有数据，则返回空 list。
    """
    params = base_params.copy()
    params["begin"] = str(offset)
    try:
        r = session.get(URL_LIST, params=params, timeout=10)
        r.raise_for_status()
        j = r.json()
        return j.get("app_msg_list", []) or []
    except Exception:
        return []


def collect_filtered_links():
    """
    1. 获取 app_msg_cnt，计算理论页数；
    2. 并发地对每个 offset 发 fetch_one_page，带进度条显示进度；
    3. 在每页结果里用正则 regex 搜索 title，只要按顺序出现 KEYWORD 中各字符即可，
       即可收集 {title, link, create_time}。
    """
    total = get_total_count()
    if total <= 0:
        print("→ 未能获取到文章总数，退出。")
        return []

    page_count = math.ceil(total / PER_PAGE)
    offsets = [i * PER_PAGE for i in range(page_count)]

    filtered = []
    empty_streak = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_one_page, off): off for off in offsets}

        # tqdm 跟踪 as_completed 的进度，总数为 len(offsets)
        for future in tqdm(as_completed(futures),
                           total=len(offsets),
                           desc="分页抓取进度"):
            page_items = future.result()
            if not page_items:
                empty_streak += 1
                # 连续 3 次都没内容，就停止
                if empty_streak >= 3:
                    break
            else:
                empty_streak = 0
                for it in page_items:
                    title = it.get("title", "")
                    # 用预先编译好的 regex 去匹配标题
                    if regex.search(title):
                        filtered.append({
                            "title": title,
                            "link": it.get("link", ""),
                            "create_time": it.get("create_time", 0)
                        })
            # 防风控，短暂随机休眠
            time.sleep(random.uniform(0.05, 0.15))

    return filtered


def main():
    results = collect_filtered_links()
    if not results:
        print("→ 没有筛出符合条件的文章。")
        return

    with open("filtered_articles_content.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    print(f"→ 已保存 {len(results)} 条到 filtered_articles_content.json")


if __name__ == "__main__":
    main()
