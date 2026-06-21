"""Setup script to copy all images into the Chrome extension folder."""
import shutil
import os

BRAIN_DIR = r"C:\Users\pc\.gemini\antigravity-ide\brain\727edc76-0854-42dc-9307-d5a553698c39"
EXT_DIR = r"c:\Users\pc\Desktop\shin\roblox\extension"

def setup():
    # Create directories
    img_dir = os.path.join(EXT_DIR, "images")
    icon_dir = os.path.join(EXT_DIR, "icons")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(icon_dir, exist_ok=True)

    # Copy game images
    game_files = {
        "jailbreak_game_1782061689200.png": "jailbreak.png",
        "murder_mystery_game_1782061700150.png": "murder_mystery.png",
        "steal_brainrot_game_1782061710551.png": "steal_brainrot.png",
    }

    for src_name, dst_name in game_files.items():
        src = os.path.join(BRAIN_DIR, src_name)
        dst = os.path.join(img_dir, dst_name)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"  Copied game image: {dst_name}")
        else:
            print(f"  WARNING: Source not found: {src_name}")

    # Create extension icons from the generated icon
    icon_src = os.path.join(BRAIN_DIR, "extension_icon_1782062953240.png")
    if os.path.exists(icon_src):
        for size in [16, 48, 128]:
            dst = os.path.join(icon_dir, f"icon{size}.png")
            shutil.copy2(icon_src, dst)
            print(f"  Created icon: icon{size}.png")
    else:
        print(f"  WARNING: Icon source not found, creating placeholder icons...")
        create_placeholder_icons(icon_dir)

    print("\nDone! Extension is ready to load in Chrome.")
    print(f"Extension folder: {EXT_DIR}")
    print("\nTo install:")
    print("  1. Open Chrome -> chrome://extensions/")
    print("  2. Enable 'Developer mode' (top right)")
    print("  3. Click 'Load unpacked'")
    print(f"  4. Select folder: {EXT_DIR}")

def create_placeholder_icons(icon_dir):
    """Create minimal PNG placeholder icons if no source available."""
    import struct
    import zlib

    def create_png(width, height, color=(59, 130, 246)):
        def chunk(chunk_type, data):
            c = chunk_type + data
            crc = struct.pack('>I', zlib.crc32(c) & 0xffffffff)
            return struct.pack('>I', len(data)) + c + crc

        header = b'\x89PNG\r\n\x1a\n'
        ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))

        raw = b''
        for y in range(height):
            raw += b'\x00'
            for x in range(width):
                raw += bytes(color)

        idat = chunk(b'IDAT', zlib.compress(raw))
        iend = chunk(b'IEND', b'')
        return header + ihdr + idat + iend

    for size in [16, 48, 128]:
        png_data = create_png(size, size)
        path = os.path.join(icon_dir, f"icon{size}.png")
        with open(path, 'wb') as f:
            f.write(png_data)
        print(f"  Created placeholder: icon{size}.png")

if __name__ == '__main__':
    print("Setting up Chrome Extension...")
    setup()
