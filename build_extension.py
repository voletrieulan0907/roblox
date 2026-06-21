"""
Script để build extension: minify CSS/JS + obfuscate JS + tạo ZIP mã hóa
"""
import os
import shutil
import zipfile
import re
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXTENSION_DIR = os.path.join(BASE_DIR, 'extension')
BUILD_DIR = os.path.join(BASE_DIR, 'extension_build')
STATIC_DIR = os.path.join(BASE_DIR, 'static', 'downloads')
OUTPUT_FILE = os.path.join(STATIC_DIR, 'rbx_extension.zip')

EXTENSION_PASSWORD = 'RBXTool@2024'

def minify_css(css_content):
    """Minify CSS"""
    # Remove comments
    css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
    # Remove whitespace
    css_content = re.sub(r'\s+', ' ', css_content)
    css_content = re.sub(r'\s*([{}:;,])\s*', r'\1', css_content)
    return css_content.strip()

def minify_js(js_content):
    """Minify + obfuscate JavaScript"""
    # Remove comments
    js_content = re.sub(r'//.*?$', '', js_content, flags=re.MULTILINE)
    js_content = re.sub(r'/\*.*?\*/', '', js_content, flags=re.DOTALL)
    
    # Remove unnecessary whitespace
    js_content = re.sub(r'\s+', ' ', js_content)
    js_content = re.sub(r'\s*([{}():;,=\[\]])\s*', r'\1', js_content)
    
    # Rename local variables to short names (basic obfuscation)
    # Replace common variable names
    replacements = {
        'cookie': 'c',
        'data': 'd',
        'response': 'r',
        'config': 'cfg',
        'result': 'res',
        'element': 'e',
        'document': 'doc',
        'window': 'w',
        'fetch': 'f',
        'function': 'fn',
    }
    
    for old, new in replacements.items():
        # Only replace if it's a whole word
        js_content = re.sub(r'\b' + old + r'\b', new, js_content)
    
    return js_content.strip()

def build_extension():
    """Build extension: minify + obfuscate + create encrypted ZIP"""
    
    print("🔨 Starting extension build process...\n")
    
    # Clean build directory
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    os.makedirs(BUILD_DIR, exist_ok=True)
    print(f"✅ Build directory created: {BUILD_DIR}\n")
    
    # Copy extension files to build dir
    for root, dirs, files in os.walk(EXTENSION_DIR):
        for dir_name in dirs:
            src_dir = os.path.join(root, dir_name)
            rel_path = os.path.relpath(src_dir, EXTENSION_DIR)
            dst_dir = os.path.join(BUILD_DIR, rel_path)
            os.makedirs(dst_dir, exist_ok=True)
        
        for file in files:
            src_file = os.path.join(root, file)
            rel_path = os.path.relpath(src_file, EXTENSION_DIR)
            dst_file = os.path.join(BUILD_DIR, rel_path)
            
            # Read original file
            with open(src_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Process based on file type
            if file.endswith('.css'):
                print(f"🎨 Minifying CSS: {rel_path}")
                content = minify_css(content)
            elif file.endswith('.js'):
                print(f"⚙️  Minifying & Obfuscating JS: {rel_path}")
                content = minify_js(content)
            
            # Write processed file
            os.makedirs(os.path.dirname(dst_file), exist_ok=True)
            with open(dst_file, 'w', encoding='utf-8') as f:
                f.write(content)
    
    print("\n✅ All files processed!\n")
    
    # Create encrypted ZIP
    os.makedirs(STATIC_DIR, exist_ok=True)
    
    # Remove old ZIP
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
        print(f"🗑️  Removed old ZIP: {OUTPUT_FILE}")
    
    print(f"🔐 Creating encrypted ZIP with password: {EXTENSION_PASSWORD}")
    print(f"📦 Compressing from: {BUILD_DIR}\n")
    
    try:
        with zipfile.ZipFile(OUTPUT_FILE, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.setpassword(EXTENSION_PASSWORD.encode('utf-8'))
            
            for root, dirs, files in os.walk(BUILD_DIR):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, BUILD_DIR)
                    zf.write(file_path, arcname=arcname)
                    print(f"  ✓ Added: {arcname}")
        
        # Get file size
        file_size = os.path.getsize(OUTPUT_FILE)
        file_size_mb = file_size / (1024 * 1024)
        
        print(f"\n✅ Build complete!")
        print(f"📁 Output: {OUTPUT_FILE}")
        print(f"📊 Size: {file_size_mb:.2f} MB ({file_size:,} bytes)")
        print(f"🔑 Password: {EXTENSION_PASSWORD}")
        
        # Clean build directory
        shutil.rmtree(BUILD_DIR)
        print(f"\n🧹 Build directory cleaned")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating ZIP: {e}")
        return False

if __name__ == '__main__':
    build_extension()
