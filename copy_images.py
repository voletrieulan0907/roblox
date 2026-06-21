import shutil, os

src_dir = r"C:\Users\pc\.gemini\antigravity-ide\brain\727edc76-0854-42dc-9307-d5a553698c39"
dst_dir = r"c:\Users\pc\Desktop\shin\roblox\static\images"

os.makedirs(dst_dir, exist_ok=True)

files = {
    "jailbreak_game_1782061689200.png": "jailbreak.png",
    "murder_mystery_game_1782061700150.png": "murder_mystery.png",
    "steal_brainrot_game_1782061710551.png": "steal_brainrot.png",
}

for src_name, dst_name in files.items():
    shutil.copy2(os.path.join(src_dir, src_name), os.path.join(dst_dir, dst_name))
    print(f"Copied {src_name} -> {dst_name}")

print("Done!")
