from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

options = Options()
driver = webdriver.Chrome(options=options)

# Mở trang Roblox trước khi thêm cookie
driver.get("https://www.roblox.com/")
time.sleep(3)

# Xóa cookie cũ (nếu có)
driver.delete_all_cookies()

# Thêm cookie .ROBLOSECURITY
driver.add_cookie({
    "name": ".ROBLOSECURITY",
    "value": "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_CAEaAhADIhwKBGR1aWQSFDE1MTQwMzI3MTUyMDk0OTc1NTc4KAM.RuxJYZbr_jpg9XrlfzF3bfMJ86Nq0L7DxEdGt3hFEUznkJuvqQKJvIB3xr2Eg8dKy4M4XBZ1aoWSOqvfvDRGBAOyi4BAqH3FqzoA06UVbMWyUK98Vemfh-Ph_IblseK0kC4PNewCj2TBcAFdzXdiAmIE7Zrn3DBX7oKw4Z_UcWWHwMbk2o3aAS5_IwXpYBBiufTDv7KCP3cf_p4xxnIrCgTcX_U7n4HRUdbkJz5gwfY_0C0IoWZw9G99DMyMeUjYZbogeN5hEOvXsV6QNfvZdkcZsmL-sqbNP5nZnmdEU-szcGlj7JtEWM14m29utWgVYQXK7sAY6gCf7RvJF4fRz5vbvklL6k7nusR-QtztMDF-THyicgNxlNJkBZZ4cbhQDSV7emZXPLCoEQXbh6of7xoAOyEJa2UwDfgCXrgSqfWeqMZIcrqrvWriE6zSGCR652RbkG98_FpR0o5HiqpBOTpUIjEDCfTHjTXh7L-mW2y6DT46P_bBDE9YBbFJSBAjnjXqzMIZFmVsDgachEBNZXvgjgtnVlBYRLFYztUoPYd7p3KgEC2mVF3V48jCR2J0iiC2ueOFKaa4H2TqOPNGegM1HzQEZFTaPJRBzSnFx_pU1yODjCVtf1WdmIlTQs7SIjg6fu471cOgJ_pPaO3CEwTuf8c",
    "domain": ".roblox.com",
    "path": "/",
    "secure": True,
})

# Tải lại trang để đăng nhập
driver.refresh()

input("Nhấn Enter để thoát...")
driver.quit()