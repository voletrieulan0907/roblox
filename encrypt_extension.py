"""
Script để mã hóa extension và nén thành file ZIP với password
"""
import os
import shutil
import zipfile
import sys
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXTENSION_DIR = os.path.join(BASE_DIR, 'extension')
STATIC_DIR = os.path.join(BASE_DIR, 'static', 'downloads')
OUTPUT_FILE = os.path.join(STATIC_DIR, 'rbx_extension.zip')

# Mật khẩu mã hóa
EXTENSION_PASSWORD = 'RBXTool@2024'

def create_encrypted_zip():
    """Tạo file ZIP mã hóa extension"""
    
    # Tạo thư mục downloads nếu chưa có
    os.makedirs(STATIC_DIR, exist_ok=True)
    
    # Xóa file cũ nếu có
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
        print(f"✅ Đã xóa file cũ: {OUTPUT_FILE}")
    
    # Kiểm tra extension dir có tồn tại không
    if not os.path.exists(EXTENSION_DIR):
        print(f"❌ Không tìm thấy extension dir: {EXTENSION_DIR}")
        return False
    
    try:
        # Tạo ZIP với mật khẩu
        print(f"🔐 Đang mã hóa extension với password: {EXTENSION_PASSWORD}")
        print(f"📦 Compressing: {EXTENSION_DIR}")
        
        with zipfile.ZipFile(OUTPUT_FILE, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Set password
            zf.setpassword(EXTENSION_PASSWORD.encode('utf-8'))
            
            # Add all files from extension directory
            for root, dirs, files in os.walk(EXTENSION_DIR):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, EXTENSION_DIR)
                    zf.write(file_path, arcname=arcname)
                    print(f"  ✓ Added: {arcname}")
        
        file_size = os.path.getsize(OUTPUT_FILE) / 1024  # KB
        print(f"\n✅ Thành công!")
        print(f"📁 Output: {OUTPUT_FILE}")
        print(f"📊 Size: {file_size:.2f} KB")
        print(f"🔑 Password: {EXTENSION_PASSWORD}")
        print(f"\n💡 Để giải nén:")
        print(f"   - Windows: Dùng 7-Zip hoặc WinRAR")
        print(f"   - Mac/Linux: unzip -P '{EXTENSION_PASSWORD}' rbx_extension.zip")
        
        return True
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False

if __name__ == '__main__':
    success = create_encrypted_zip()
    sys.exit(0 if success else 1)
