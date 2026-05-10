# WeChat Public Platform Crawler

这是一个微信公众号后台文章列表抓取工具。它按标题关键词筛选文章，生成 JSON 文件，再用 Tkinter 界面管理文章的已读/未读状态。

## 它做什么

1. 使用公众号后台 Cookie、token 和 fakeid 请求文章列表。
2. 按标题关键词筛选文章。
3. 输出 `filtered_articles_content.json`。
4. 用 `article_manager.py` 打开文章管理界面。
5. 在本地保存阅读状态到 `article_state.json`。

## 项目结构

```text
class_crawler/main.py             爬虫入口
class_crawler/article_manager.py  文章管理界面
requirements.txt                  Python 依赖
.env.example                      配置示例
```

## 快速运行

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
copy .env.example .env
python class_crawler/main.py
python class_crawler/article_manager.py
```

macOS/Linux 激活虚拟环境：

```bash
source .venv/bin/activate
```

也可以不用 `.env`，直接传参数：

```bash
python class_crawler/main.py --cookie "..." --token "..." --fakeid "..." --keyword "关键词"
```

## 安全说明

- Cookie、token、fakeid 都是敏感信息，不要写进代码，也不要提交到 GitHub。
- 运行生成的 `filtered_articles_content.json` 和 `article_state.json` 已加入忽略规则。
- 微信后台凭证会过期，运行失败时先重新获取 Cookie/token。
