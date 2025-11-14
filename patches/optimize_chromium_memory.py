#!/usr/bin/env python3
"""
Patch MediaCrawler to add memory optimization flags for Chromium
This script is called from entrypoint.sh to patch the browser launch parameters
"""
import os
import sys

def patch_xhs_core():
    """Add memory optimization flags to XHS crawler browser launch"""
    xhs_core_path = "/app/MediaCrawler/media_platform/xhs/core.py"

    # Read the file
    with open(xhs_core_path, 'r') as f:
        content = f.read()

    # Add memory optimization args to browser launch
    # These args help reduce memory usage in containerized environments
    browser_args = [
        "--disable-dev-shm-usage",  # Use /tmp instead of /dev/shm
        "--disable-gpu",  # Disable GPU hardware acceleration
        "--no-sandbox",  # Already in use
        "--disable-setuid-sandbox",
        "--disable-web-security",
        "--disable-features=VizDisplayCompositor",
        "--disable-background-timer-throttling",
        "--disable-renderer-backgrounding",
        "--disable-features=TranslateUI",
        "--disable-ipc-flooding-protection",
        "--max_old_space_size=512",  # Limit V8 heap size
        "--single-process",  # Run in single process mode (saves memory)
        "--no-zygote",  # Disable zygote process
        "--memory-pressure-off",  # Disable memory pressure handling
    ]

    # Check if we need to patch launch_persistent_context
    if "launch_persistent_context(" in content and "args=" not in content.split("launch_persistent_context(")[1].split(")")[0]:
        # Add args parameter to launch_persistent_context
        content = content.replace(
            "browser_context = await chromium.launch_persistent_context(\n                user_data_dir=user_data_dir,",
            f"browser_context = await chromium.launch_persistent_context(\n                user_data_dir=user_data_dir,\n                args={browser_args},"
        )
        print("Patched launch_persistent_context with memory optimization args")

    # Check if we need to patch regular launch
    if "browser = await chromium.launch(headless=headless" in content and "args=" not in content.split("await chromium.launch(")[1].split(")")[0]:
        content = content.replace(
            "browser = await chromium.launch(headless=headless, proxy=playwright_proxy)",
            f"browser = await chromium.launch(headless=headless, proxy=playwright_proxy, args={browser_args})"
        )
        print("Patched chromium.launch with memory optimization args")

    # Write the patched content back
    with open(xhs_core_path, 'w') as f:
        f.write(content)

    print(f"Successfully patched {xhs_core_path} with memory optimizations")

def patch_other_platforms():
    """Apply similar patches to other platform crawlers if needed"""
    platforms = ["douyin", "weibo", "bilibili", "kuaishou", "zhihu", "tieba"]

    for platform in platforms:
        core_path = f"/app/MediaCrawler/media_platform/{platform}/core.py"
        if os.path.exists(core_path):
            try:
                with open(core_path, 'r') as f:
                    content = f.read()

                # Apply similar patches if browser launch is found
                if "chromium.launch" in content:
                    # Similar patching logic
                    print(f"Found browser launch in {platform}/core.py - would need patching")
            except Exception as e:
                print(f"Could not patch {platform}: {e}")

if __name__ == "__main__":
    try:
        patch_xhs_core()
        # Optionally patch other platforms
        # patch_other_platforms()
        print("Memory optimization patches applied successfully")
    except Exception as e:
        print(f"Error applying patches: {e}", file=sys.stderr)
        sys.exit(1)