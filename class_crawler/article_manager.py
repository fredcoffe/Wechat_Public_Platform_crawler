# -*- coding: utf-8 -*-
"""Tkinter article manager for crawler output."""

import json
import webbrowser
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

BASE_DIR = Path(__file__).resolve().parent
JSON_FILE = BASE_DIR / "filtered_articles_content.json"
STATE_FILE = BASE_DIR / "article_state.json"
ITEMS_PER_PAGE = 10


def load_articles():
    """Load article list and read/unread state."""
    if not JSON_FILE.exists():
        messagebox.showerror("错误", f"未找到文件: {JSON_FILE}")
        return []

    articles = json.loads(JSON_FILE.read_text(encoding="utf-8"))
    state = json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {}

    for article in articles:
        link = article.get("link")
        article["read"] = state.get(link, False)

    return articles


def save_state(articles):
    """Persist read/unread state."""
    state = {article["link"]: article.get("read", False) for article in articles if article.get("link")}
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


class PaginatedFrame(ttk.Frame):
    def __init__(self, master, articles, parent_app, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.articles = articles
        self.parent_app = parent_app
        self.page_index = 0
        self.total_pages = max(1, (len(self.articles) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

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
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        start = self.page_index * ITEMS_PER_PAGE
        end = start + ITEMS_PER_PAGE
        for article in self.articles[start:end]:
            self._create_article_row(self.content_frame, article)

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

    def _create_article_row(self, parent_frame, article):
        row = ttk.Frame(parent_frame)
        row.pack(fill=tk.X, padx=5, pady=2)

        title = article.get("title") or "未命名文章"
        label = ttk.Label(row, text=title, foreground="blue", cursor="hand2")
        label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        label.bind("<Button-1>", lambda _event, url=article.get("link"): webbrowser.open(url or ""))

        btn_text = "标记未读" if article.get("read", False) else "已阅"
        button = ttk.Button(row, text=btn_text, width=8, command=lambda item=article: self.toggle_read_status(item))
        button.pack(side=tk.RIGHT, padx=5)

    def toggle_read_status(self, article):
        article["read"] = not article.get("read", False)
        save_state(self.parent_app.articles)
        self.parent_app.refresh_views()


class ArticleManagerApp:
    def __init__(self, master, articles):
        self.master = master
        self.master.title("微信公众号文章管理器")
        self.articles = articles

        self.notebook = ttk.Notebook(master)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.refresh_views(initial=True)

    def refresh_article_lists(self):
        self.unread_articles = [item for item in self.articles if not item.get("read", False)]
        self.read_articles = [item for item in self.articles if item.get("read", False)]

    def refresh_views(self, initial=False):
        self.refresh_article_lists()
        if not initial:
            for tab_id in self.notebook.tabs():
                self.notebook.forget(tab_id)

        self.unread_frame = PaginatedFrame(self.notebook, self.unread_articles, parent_app=self)
        self.read_frame = PaginatedFrame(self.notebook, self.read_articles, parent_app=self)
        self.notebook.add(self.unread_frame, text="未读文章")
        self.notebook.add(self.read_frame, text="已阅文章")


def main():
    root = tk.Tk()
    ArticleManagerApp(root, load_articles())
    root.geometry("800x600")
    root.mainloop()


if __name__ == "__main__":
    main()
