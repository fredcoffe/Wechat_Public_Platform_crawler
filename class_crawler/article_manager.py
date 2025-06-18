# -*- coding: utf-8 -*-
"""
完整爬虫管理界面脚本（带翻页与已阅/未读二级界面）：
- 从 filtered_articles_content.json 中读取文章列表
- 提供“未读文章”和“已阅文章”两个选项卡，每个都支持翻页
- 点击标题可在浏览器打开文章链接
- 点击“已阅”或“标记未读”按钮切换状态，并自动保存到本地 article_state.json
- 下次启动时，状态自动恢复
"""

import json
import os
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox

# 文件路径配置
JSON_FILE = "filtered_articles_content.json"
STATE_FILE = "article_state.json"
ITEMS_PER_PAGE = 10  # 每页显示的文章数


def load_articles():
    """加载文章列表及状态"""
    if not os.path.exists(JSON_FILE):
        messagebox.showerror("错误", f"未找到文件: {JSON_FILE}")
        return []

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        articles = json.load(f)

    # 初始化状态：如果已有 STATE_FILE，就加载已有状态；否则默认全部未读
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as sf:
            state = json.load(sf)
    else:
        state = {}

    # 将“已读”状态填充到文章数据中
    for art in articles:
        link = art.get("link")
        art["read"] = state.get(link, False)

    return articles


def save_state(articles):
    """将文章阅读状态写入 STATE_FILE"""
    state = {art["link"]: art["read"] for art in articles}
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=4)


class PaginatedFrame(ttk.Frame):
    def __init__(self, master, articles, parent_app, *args, **kwargs):
        """
        master: 父容器（Notebook）
        articles: 本分页框要显示的文章列表（未读或已阅）
        parent_app: ArticleManagerApp 的实例，用于在状态切换后刷新视图
        """
        super().__init__(master, *args, **kwargs)
        self.articles = articles
        self.parent_app = parent_app  # 保存父级应用实例
        self.page_index = 0
        self.total_pages = max(1, (len(self.articles) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

        # 创建内容区域和翻页导航区域
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        self.nav_frame = ttk.Frame(self)
        self.nav_frame.pack(fill=tk.X)

        self.prev_btn = ttk.Button(self.nav_frame, text="<< 上一页", command=self.prev_page)
        self.prev_btn.pack(side=tk.LEFT, padx=5, pady=5)
        self.page_label = ttk.Label(self.nav_frame, text="")
        self.page_label.pack(side=tk.LEFT, padx=5)
        self.next_btn = ttk.Button(self.nav_frame, text="下一页 >>", command=self.next_page)
        self.next_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self.show_page()

    def show_page(self):
        """根据 page_index 显示当前页的文章"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        start = self.page_index * ITEMS_PER_PAGE
        end = start + ITEMS_PER_PAGE
        page_items = self.articles[start:end]

        for art in page_items:
            self._create_article_row(self.content_frame, art)

        self.page_label.config(text=f"第 {self.page_index + 1} 页 / 共 {self.total_pages} 页")
        self.prev_btn.config(state=tk.NORMAL if self.page_index > 0 else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if self.page_index < self.total_pages - 1 else tk.DISABLED)

    def prev_page(self):
        if self.page_index > 0:
            self.page_index -= 1
            self.show_page()

    def next_page(self):
        if self.page_index < self.total_pages - 1:
            self.page_index += 1
            self.show_page()

    def _create_article_row(self, parent_frame, art):
        """
        创建文章一行：标题（可点击打开链接） + 阅读/取消按钮
        """
        row = ttk.Frame(parent_frame)
        row.pack(fill=tk.X, padx=5, pady=2)

        lbl = ttk.Label(row, text=art.get("title"), foreground="blue", cursor="hand2")
        lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        lbl.bind("<Button-1>", lambda e, url=art.get("link"): webbrowser.open(url))

        btn_text = "标记未读" if art.get("read", False) else "已阅"
        btn = ttk.Button(row, text=btn_text, width=8, command=lambda a=art: self.toggle_read_status(a))
        btn.pack(side=tk.RIGHT, padx=5)

    def toggle_read_status(self, art):
        """切换某篇文章的已读状态，并调用父应用刷新视图与持久化"""
        art["read"] = not art.get("read", False)
        save_state(self.parent_app.articles)  # 保存到全局文章列表
        self.parent_app.refresh_views()       # 让父应用重建各分页视图


class ArticleManagerApp:
    def __init__(self, master, articles):
        self.master = master
        self.master.title("文章管理器 - 每日积累“背三句”")
        self.articles = articles

        # 使用 Notebook 实现二级界面：未读 与 已阅
        self.notebook = ttk.Notebook(master)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 初始化未读和已阅两个子列表
        self.refresh_article_lists()

        # 创建两个分页框
        self.unread_frame = PaginatedFrame(self.notebook, self.unread_articles, parent_app=self)
        self.read_frame = PaginatedFrame(self.notebook, self.read_articles, parent_app=self)

        self.notebook.add(self.unread_frame, text="未读文章")
        self.notebook.add(self.read_frame, text="已阅文章")

    def refresh_article_lists(self):
        """根据 self.articles 更新 self.unread_articles 和 self.read_articles"""
        self.unread_articles = [a for a in self.articles if not a.get("read", False)]
        self.read_articles = [a for a in self.articles if a.get("read", False)]

    def refresh_views(self):
        """在切换阅读状态后重新构建分页视图"""
        # 1. 重新分类文章
        self.refresh_article_lists()

        # 2. 移除原有的分页框并销毁
        self.notebook.forget(self.unread_frame)
        self.notebook.forget(self.read_frame)

        # 3. 重新创建新的分页框
        self.unread_frame = PaginatedFrame(self.notebook, self.unread_articles, parent_app=self)
        self.read_frame = PaginatedFrame(self.notebook, self.read_articles, parent_app=self)

        # 4. 添加到 Notebook
        self.notebook.add(self.unread_frame, text="未读文章")
        self.notebook.add(self.read_frame, text="已阅文章")


def main():
    root = tk.Tk()
    articles = load_articles()
    app = ArticleManagerApp(root, articles)
    root.geometry("800x600")
    root.mainloop()


if __name__ == "__main__":
    main()
