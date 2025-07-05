import os
import time
import argparse
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def create_proxy_extension(proxy_host, proxy_port, proxy_user, proxy_pass):
    """Create a Chrome proxy extension with authentication"""
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """

    background_js = """
    var config = {
        mode: "fixed_servers",
        rules: {
        singleProxy: {
            scheme: "http",
            host: "%s",
            port: parseInt(%s)
        },
        bypassList: ["localhost"]
        }
    };

    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }

    chrome.webRequest.onAuthRequired.addListener(
        callbackFn,
        {urls: ["<all_urls>"]},
        ['blocking']
    );
    """ % (proxy_host, proxy_port, proxy_user, proxy_pass)

    return {
        "manifest.json": manifest_json,
        "background.js": background_js
    }

def main():
    parser = argparse.ArgumentParser(description='YouTube Viewer with Proxies and Profiles')
    parser.add_argument('proxy_file', help='Path to working proxy file (user:pass@ip:port or ip:port)')
    parser.add_argument('youtube_url', help='YouTube video URL')
    parser.add_argument('--watch-time', type=int, default=60, 
                        help='Seconds to watch video (default: 60)')
    parser.add_argument('--headless', action='store_true', 
                        help='Run browsers in headless mode')
    parser.add_argument('--profiles-dir', default='chrome_profiles',
                        help='Directory to store Chrome profiles (default: chrome_profiles)')
    parser.add_argument('--vnc-index', type=int, default=-1,
                        help='Index of instance to make visible for VNC (default: -1)')
    args = parser.parse_args()

    # Read proxies from file
    with open(args.proxy_file) as f:
        proxies = [line.strip() for line in f if line.strip()]

    # Create profiles directory
    os.makedirs(args.profiles_dir, exist_ok=True)
    
    drivers = []
    print(f"Launching {len(proxies)} Chrome instances with unique profiles...")
    
    for i, proxy in enumerate(proxies):
        try:
            print(f"\n--- Instance {i+1}/{len(proxies)} ---")
            print(f"Proxy: {proxy}")
            
            # Create profile directory
            profile_path = os.path.join(args.profiles_dir, f"profile_{i+1}")
            os.makedirs(profile_path, exist_ok=True)
            
            chrome_options = Options()
            chrome_options.add_argument(f"--user-data-dir={profile_path}")
            
            # Handle VNC visibility
            if args.vnc_index == i:
                print("Running in VISIBLE mode for VNC")
                chrome_options.add_argument("--window-size=1920,1080")
                chrome_options.add_argument("--auto-open-devtools-for-tabs")
            elif args.headless:
                chrome_options.add_argument("--headless=new")
                chrome_options.add_argument("--window-size=1280,720")
            
            # Parse proxy details
            if "@" in proxy:
                auth, server = proxy.split("@")
                user, password = auth.split(":")
                host, port = server.split(":")
            else:
                host, port = proxy.split(":")
                user, password = None, None

            # Handle proxy authentication
            if user and password:
                extension = create_proxy_extension(host, port, user, password)
                extension_dir = os.path.join(profile_path, "proxy_extension")
                os.makedirs(extension_dir, exist_ok=True)
                for filename, content in extension.items():
                    with open(os.path.join(extension_dir, filename), "w") as f:
                        f.write(content)
                chrome_options.add_argument(f"--load-extension={os.path.abspath(extension_dir)}")
            else:
                chrome_options.add_argument(f"--proxy-server=http://{host}:{port}")

            # Initialize driver
            driver = webdriver.Chrome(options=chrome_options)
            drivers.append(driver)
            
            # Open YouTube video
            print("Loading YouTube video...")
            driver.get(args.youtube_url)
            
            # Accept cookies
            try:
                WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, 
                    '//*[@id="content"]/div[2]/div[6]/div[1]/ytd-button-renderer[2]/yt-button-shape/button'))
                ).click()
                print("Accepted cookies")
            except Exception:
                print("Cookie consent not found or already accepted")
            
            # Play video
            WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.ytp-large-play-button"))
            ).click()
            print("Video started playing")
            
            # Mute audio
            time.sleep(2)
            driver.find_element(By.CSS_SELECTOR, "button.ytp-mute-button").click()
            print("Audio muted")
            
            # Randomize playback speed slightly
            speed = 1.0 + (i % 3) * 0.25  # 1.0, 1.25, or 1.5
            driver.execute_script(f"document.querySelector('video').playbackRate = {speed};")
            print(f"Playback speed set to: {speed}x")
            
            # Scroll down to comments to simulate engagement
            driver.execute_script("window.scrollTo(0, 500);")
            print("Scrolled to comments section")
            
        except Exception as e:
            print(f"Error with proxy {proxy}: {str(e)}")
            continue

    # Simulate watching
    print(f"\nSimulating watch time for {len(drivers)} instances ({args.watch_time} seconds)...")
    
    # Periodically interact with videos
    start_time = time.time()
    while time.time() - start_time < args.watch_time:
        remaining = int(args.watch_time - (time.time() - start_time))
        print(f"\rWatching... {remaining} seconds remaining", end="", flush=True)
        
        # Random interactions every 15 seconds
        for i, driver in enumerate(drivers):
            try:
                if time.time() - start_time > args.watch_time:
                    break
                    
                # Scroll randomly
                scroll_pos = 300 + (i % 5) * 200
                driver.execute_script(f"window.scrollTo(0, {scroll_pos});")
                
                # Randomly pause/resume (25% chance)
                if i % 4 == 0:
                    video = driver.find_element(By.TAG_NAME, "video")
                    if video.get_attribute("paused"):
                        driver.execute_script("arguments[0].play();", video)
                    else:
                        driver.execute_script("arguments[0].pause();", video)
                
            except Exception:
                pass
                
        time.sleep(15)

    # Clean up
    print("\n\nClosing all browsers...")
    for driver in drivers:
        try:
            driver.quit()
        except:
            pass

    print("All browsers closed. Done!")

if __name__ == "__main__":
    main()
