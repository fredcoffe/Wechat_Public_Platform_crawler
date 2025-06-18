import requests
import pandas as pd
import time
import json
import math
import random
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# ----------------------------- 配置区域 -----------------------------
url = "https://mp.weixin.qq.com/cgi-bin/appmsg"
cookie = (
    "123"
)
# 如果登录后 Cookie 过期，需要自行替换成最新的一串。

# 基本请求参数模板
base_data = {
    "token": "123",      # 填写你自己的 token
    "lang": "zh_CN",
    "f": "json",
    "ajax": "1",
    "action": "list_ex",
    "begin": "0",              # 后面会覆盖
    "count": "10",             # 每页尽量取到 10 条（一般微信接口支持最大 10）
    "query": "",
    "fakeid": "123",  # 对应公众号的 fakeid，需要自己填写
    "type": "9",
}

# --------------------------- 1. 获取总文章数 ---------------------------
def get_total_count(session, params):
    """
    第一次请求只取 app_msg_cnt，
    这样就能知道大概一共有多少篇文章。
    """
    resp = session.get(url, params=params, timeout=10)
    resp.raise_for_status()
    content = resp.json()
    return int(content.get("app_msg_cnt", 0))

# ------------------------- 2. 单页并发请求函数 -------------------------
def fetch_one_page(begin_offset, session, params_template):
    """
    根据传入的 begin_offset 请求一页文章列表，返回该页的 app_msg_list（一个 list）。
    """
    params = params_template.copy()
    params["begin"] = str(begin_offset)
    try:
        r = session.get(url, params=params, timeout=10)
        r.raise_for_status()
        data_json = r.json()
        return data_json.get("app_msg_list", [])
    except Exception as e:
        # 如果出错，可以打印日志或重试
        print(f"[错误] 请求 begin={begin_offset} 时出错：{e}")
        return []

# --------------------------- 3. 并发获取所有文章列表 ---------------------------
def get_all_content_list(total_count, per_page=10, max_workers=5):
    """
    并发拿到所有页面的 app_msg_list 结果并合并，最后返回一个 list。
    """
    # 计算一共有多少页
    num_pages = math.ceil(total_count / per_page)
    offsets = [i * per_page for i in range(num_pages)]

    # 准备 Session 和参数
    session = requests.Session()
    session.headers.update({
        "Cookie": cookie,
        "User-Agent": base_data["User-Agent"] if "User-Agent" in base_data else "Mozilla/5.0"
    })
    # 注意：base_data 里没有写 UA，所以我们直接在 session.headers 里赋值。
    # 如果你希望 params 里也带 UA，可以把 UA 写到 base_data 之外。本示例直接给 session.headers 赋值就行。

    # 用于传给线程的参数 template
    params_template = base_data.copy()
    params_template["count"] = str(per_page)

    all_items = []
    # 使用线程池并发请求
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_offset = {
            executor.submit(fetch_one_page, b, session, params_template): b
            for b in offsets
        }
        for future in tqdm(as_completed(future_to_offset),
                           total=len(offsets),
                           desc="并发获取文章列表"):
            page_items = future.result()
            all_items.extend(page_items)
            # 这里可以加一个很短的随机 sleep，降低请求突发量
            time.sleep(random.uniform(0.1, 0.3))

    return all_items

# ------------------------- 4. 处理并保存到 CSV -------------------------
def process_and_save(content_list):
    """
    把 content_list 中的字段提取出来（title、link、create_time），
    存为 content_list.json 和 data.csv。
    """
    # 先写 json（调试时方便看结构）
    with open("content_list.json", "w", encoding="utf-8") as f:
        json.dump(content_list, f, ensure_ascii=False, indent=4)

    results = []
    for item in content_list:
        title = item.get("title", "")
        link = item.get("link", "")
        create_ts = item.get("create_time", 0)
        create_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(create_ts))
        results.append([title, link, create_time])

    df = pd.DataFrame(results, columns=["title", "link", "create_time"])
    df.to_csv("data.csv", index=False, encoding="utf-8")

# ------------------------------ 主流程 ------------------------------
if __name__ == "__main__":
    # 1. 先用一个简单 Session 拿总数
    session_temp = requests.Session()
    session_temp.headers.update({
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N)"
    })
    total = get_total_count(session_temp, base_data)
    print(f"→ 公众号文章总数: {total} 篇")

    if total <= 0:
        print("未获取到任何文章，检查 token 和 fakeid 是否正确。")
    else:
        # 2. 并发获取所有分页的文章列表
        content_list = get_all_content_list(total, per_page=10, max_workers=5)
        print(f"→ 实际拿到文章列表条目: {len(content_list)}")

        # 3. 统一处理并保存
        process_and_save(content_list)
        print("→ 已保存 content_list.json 和 data.csv")
