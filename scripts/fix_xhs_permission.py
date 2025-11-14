"""
修复小红书权限问题的脚本
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "MediaCrawler"))

from playwright.async_api import async_playwright


async def clear_xhs_cookies():
    """清除小红书的cookie缓存"""
    cookie_path = Path(__file__).parent.parent / "MediaCrawler" / "browser_data" / "xhs_browser_context" / "xiaohongshu_login_state.json"

    if cookie_path.exists():
        print(f"删除旧的cookie文件: {cookie_path}")
        cookie_path.unlink()
        print("Cookie已清除")
    else:
        print("没有找到cookie文件")


async def manual_login():
    """手动登录小红书"""
    print("开始手动登录小红书...")
    print("请在打开的浏览器中完成以下步骤：")
    print("1. 扫码或手机号登录")
    print("2. 完成所有验证（滑块验证等）")
    print("3. 确保能正常浏览小红书内容")
    print("4. 完成后按Enter键继续...")

    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-setuid-sandbox',
                '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
        )

        # 创建上下文
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # 添加初始化脚本，隐藏自动化特征
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en']
            });
            window.chrome = {
                runtime: {}
            };
            Object.defineProperty(navigator, 'permissions', {
                get: () => ({
                    query: () => Promise.resolve({state: 'granted'})
                })
            });
        """)

        # 打开小红书
        page = await context.new_page()
        await page.goto("https://www.xiaohongshu.com/explore")

        # 等待用户完成登录
        input("完成登录后，按Enter键继续...")

        # 保存cookies
        cookies = await context.cookies()
        storage_state = await context.storage_state()

        # 保存到文件
        cookie_dir = Path(__file__).parent.parent / "MediaCrawler" / "browser_data" / "xhs_browser_context"
        cookie_dir.mkdir(parents=True, exist_ok=True)

        cookie_file = cookie_dir / "xiaohongshu_login_state.json"
        with open(cookie_file, 'w', encoding='utf-8') as f:
            json.dump(storage_state, f, ensure_ascii=False, indent=2)

        print(f"Cookie已保存到: {cookie_file}")

        # 测试搜索功能
        print("\n测试搜索功能...")
        await page.goto("https://www.xiaohongshu.com/search_result?keyword=美食")
        await page.wait_for_timeout(3000)

        # 检查是否有搜索结果
        try:
            await page.wait_for_selector(".note-item", timeout=5000)
            print("✅ 搜索功能正常！")
        except:
            print("❌ 搜索功能异常，请检查账号状态")

        await browser.close()


async def test_with_cdp():
    """使用CDP模式测试"""
    print("\n使用CDP模式测试...")

    # 更新配置文件
    config_path = Path(__file__).parent.parent / "MediaCrawler" / "config" / "base_config.py"

    print("建议的配置修改：")
    print("1. 设置 HEADLESS = False")
    print("2. 设置 ENABLE_CDP_MODE = True")
    print("3. 设置 LOGIN_TYPE = 'cookie'")
    print("4. 清空 COOKIES 字段")
    print("\n完成配置后，请重新运行爬虫")


async def main():
    """主函数"""
    print("小红书权限问题修复工具")
    print("=" * 50)
    print("1. 清除旧的Cookie")
    print("2. 手动重新登录")
    print("3. 使用CDP模式建议")
    print("=" * 50)

    choice = input("请选择操作 (1/2/3): ")

    if choice == "1":
        await clear_xhs_cookies()
    elif choice == "2":
        await clear_xhs_cookies()
        await manual_login()
    elif choice == "3":
        await test_with_cdp()
    else:
        print("无效的选择")


if __name__ == "__main__":
    asyncio.run(main())