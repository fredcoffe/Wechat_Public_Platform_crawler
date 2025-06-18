2025.6.4
数据分析方法课大作业

这是一个微信公众号爬取的项目，他能指定标题包含特定字符的文章进行爬取（main.py内容）
爬取后会生成filtered_articles_content.json的json文件，然后运行article_manager.exe来启动，界面中可管理你对文章的读取

注意事项：
1.爬取设置，在main.py中，配置区的COOKIE = "你的COOKIE", TOKEN = "你的TOKEN", FAKEID = "你的FAKEID", KEYWORD = '每日积累“背三句”' 要填写自己的（下方说明如何获取）
2.在main.py最后的def main():函数中with open("filtered_articles_content.json", "w", encoding="utf-8") as f:中"filtered_articles_content.json"是生成的文件名，有需要可以改写备份，但界面能读取的只有名为filtered_articles_content.json的文件
3.article_manager.exe和filtered_articles_content.json要在同一个目录下，否则会报错