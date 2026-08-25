"""
抖音个人账号「喜欢」&「收藏」视频抓取脚本
运行方式：python douyin_scraper.py
"""
import json
import os
import time
import csv
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

USERNAME = os.getenv("DOUYIN_USERNAME")
PASSWORD = os.getenv("DOUYIN_PASSWORD")

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")
STATE_FILE = os.path.join(PROJECT_DIR, "douyin_state.json")


class DouyinScraper:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None

    def launch(self):
        print("[INFO] 正在启动浏览器...")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            viewport={"width": 1920, "height": 1080},
        )
        if os.path.exists(STATE_FILE):
            print("[INFO] 加载已保存的登录状态...")
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
            context.add_cookies(state.get("cookies", []))
        self.page = context.new_page()
        from playwright_stealth import Stealth
        Stealth().apply_stealth_sync(self.page)
        self.page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )
        print("[INFO] 浏览器启动完成\n")
        return context

    def login(self):
        print("[INFO] 正在登录抖音...")
        # 导航到个人主页触发登录弹窗
        self.page.goto("https://www.douyin.com/user/self", wait_until="domcontentloaded", timeout=60000)
        self.page.wait_for_timeout(5000)

        # 点击登录按钮
        self.page.click(".semi-button-primary", force=True)
        self.page.wait_for_timeout(3000)

        # 点击密码登录（用JS确保找到正确元素）
        self.page.evaluate(r"""
            () => {
                const all = document.querySelectorAll('*');
                for (const el of all) {
                    if (el.innerText && el.innerText.trim() === '密码登录' && el.tagName === 'SPAN') {
                        el.click();
                        return;
                    }
                }
            }
        """)
        self.page.wait_for_timeout(2000)

        # 填写账号密码
        self.page.fill('input[placeholder*="手机号"]', USERNAME)
        self.page.fill('input[placeholder*="密码"]', PASSWORD)

        # 点击登录按钮（弹窗内位置约1135,670）
        self.page.mouse.click(1135, 670)
        print("[INFO] 已提交登录，等待结果...")
        self.page.wait_for_timeout(8000)

        # 处理"是否保存登录信息？"弹窗
        save_dialog = self.page.query_selector('text=是否保存登录信息')
        if save_dialog:
            cancel_btn = self.page.query_selector('text=取消')
            if cancel_btn:
                cancel_btn.click()
                self.page.wait_for_timeout(2000)

        # 检查登录结果
        text = self.page.evaluate("document.body.innerText")
        if "未登录" in text[:500]:
            print("[WARN] 登录失败，请检查账号密码是否正确")
            self.page.screenshot(path=os.path.join(OUTPUT_DIR, "login_failed.png"))
            return False

        print(f"[INFO] 登录成功！当前URL: {self.page.url}")

        # 保存登录状态
        state = self.page.context.storage_state()
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        print(f"[INFO] 登录状态已保存到: {STATE_FILE}\n")
        return True

    def _close_save_dialog(self):
        """关闭'是否保存登录信息？'弹窗"""
        try:
            dialog = self.page.query_selector('text=是否保存登录信息', timeout=3000)
            if dialog:
                cancel = self.page.query_selector('text=取消', timeout=2000)
                if cancel:
                    cancel.click()
                    self.page.wait_for_timeout(1000)
        except Exception:
            pass

    def scrape_tab(self, tab_name, tab_param):
        """抓取指定Tab的视频"""
        print(f"\n{'='*50}")
        print(f"[INFO] 开始抓取「{tab_name}」...")
        print(f"{'='*50}")

        collected = []
        seen_ids = set()

        def on_response(response):
            url = response.url
            if ("aweme" in url or "feed" in url) and response.status == 200:
                try:
                    data = response.json()
                    items = data.get("aweme_list", [])
                    if not items:
                        items = data.get("data", [])
                    for item in items:
                        aweme_id = item.get("aweme_id", "")
                        if aweme_id and aweme_id not in seen_ids:
                            seen_ids.add(aweme_id)
                            stats = item.get("statistics", {})
                            video = item.get("video", {})
                            play_addr = video.get("play_addr", {})
                            url_list = play_addr.get("url_list", [])
                            cover = item.get("cover", {})
                            cover_list = cover.get("url_list", []) if cover else []
                            collected.append({
                                "aweme_id": aweme_id,
                                "title": item.get("desc", ""),
                                "play_url": url_list[0] if url_list else "",
                                "cover_url": cover_list[0] if cover_list else "",
                                "likes": stats.get("digg_count", 0),
                                "comments": stats.get("comment_count", 0),
                                "plays": stats.get("play_count", 0),
                                "collects": stats.get("collect_count", 0),
                                "shares": stats.get("share_count", 0),
                                "create_time": item.get("create_time", 0),
                                "duration": item.get("duration", 0),
                                "author": item.get("author", {}).get("nickname", ""),
                            })
                            print(f"  [收集] {aweme_id[:8]}... | {item.get('desc','')[:30]}...")
                except Exception:
                    pass

        self.page.on("response", on_response)

        try:
            # 先导航到主页建立session
            self.page.goto("https://www.douyin.com", wait_until="domcontentloaded", timeout=30000)
            self.page.wait_for_timeout(5000)
            self._close_save_dialog()

            # 导航到对应Tab（URL方式更可靠）
            tab_url_param = {"喜欢": "like", "收藏": "favorite_collection"}
            tab_url = tab_url_param.get(tab_name, tab_param)
            print(f"[INFO] 导航到「{tab_name}」...")
            self.page.goto(f"https://www.douyin.com/user/self?showTab={tab_url}", wait_until="domcontentloaded", timeout=30000)
            self.page.wait_for_timeout(8000)
            self._close_save_dialog()
            print(f"[INFO] 页面URL: {self.page.url}")

            # 滚动加载 - 持续滚动直到没有新内容
            prev_height = 0
            no_change_count = 0
            max_scrolls = 100
            total_api_calls = 0

            for i in range(max_scrolls):
                current_height = self.page.evaluate("document.body.scrollHeight")
                if current_height == prev_height:
                    no_change_count += 1
                    if no_change_count >= 5:
                        print(f"[INFO] 连续5次无变化，停止")
                        break
                else:
                    no_change_count = 0
                prev_height = current_height

                self.page.evaluate("window.scrollBy(0, 2000)")
                self.page.wait_for_timeout(2000)
                self._close_save_dialog()
                total_api_calls += 1

                if i % 5 == 0:
                    cards = self.page.evaluate("document.querySelectorAll('a[href*=\"/video/\"]').length")
                    print(f"[INFO] 滚动{total_api_calls}次，已收集{len(collected)}条，页面卡片{cards}个")

                # 检查是否到底
                scroll_bottom = self.page.evaluate("window.scrollY + window.innerHeight")
                doc_height = self.page.evaluate("document.body.scrollHeight")
                if scroll_bottom >= doc_height - 200:
                    print("[INFO] 已滚动到页面底部")
                    break

            # 等待所有XHR完成
            self.page.wait_for_timeout(3000)
            self._close_save_dialog()

            print(f"[INFO] 「{tab_name}」抓取完成，共 {len(collected)} 条视频（API调用{total_api_calls}次）")

        finally:
            self.page.remove_listener("response", on_response)

        return collected

    def export_results(self, videos, tab_name):
        """导出结果"""
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        json_path = os.path.join(OUTPUT_DIR, f"douyin_{tab_name}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "tab": tab_name,
                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total": len(videos),
                "videos": videos,
            }, f, ensure_ascii=False, indent=2)
        print(f"[INFO] JSON已保存: {json_path}")

        csv_path = os.path.join(OUTPUT_DIR, f"douyin_{tab_name}.csv")
        if videos:
            fieldnames = ["aweme_id", "title", "play_url", "cover_url", "likes", "comments", "plays", "collects", "shares", "create_time", "author"]
            with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for v in videos:
                    writer.writerow({k: v.get(k, "") for k in fieldnames})
            print(f"[INFO] CSV已保存: {csv_path}")

    def run(self):
        """主流程"""
        context = self.launch()

        # 检查是否需要登录
        self.page.goto("https://www.douyin.com", wait_until="domcontentloaded", timeout=15000)
        self.page.wait_for_timeout(3000)
        text = self.page.evaluate("document.body.innerText")
        if "未登录" in text[:300] or "登录" in text[:300]:
            self.login()
        else:
            print("[INFO] 使用已保存的登录状态\n")

        # 抓取喜欢
        liked = self.scrape_tab("喜欢", "like")
        self.export_results(liked, "喜欢")

        # 抓取收藏
        bookmarked = self.scrape_tab("收藏", "favorite_collection")
        self.export_results(bookmarked, "收藏")

        print(f"\n{'='*50}")
        print(f"[OK] 全部完成！")
        print(f"  喜欢: {len(liked)} 条 -> output/douyin_喜欢.json/.csv")
        print(f"  收藏: {len(bookmarked)} 条 -> output/douyin_收藏.json/.csv")
        print(f"{'='*50}")

        self.browser.close()
        self.playwright.stop()


if __name__ == "__main__":
    scraper = DouyinScraper()
    scraper.run()
