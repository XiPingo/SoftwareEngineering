import sys
import main

def main_fuzz():
    data = sys.stdin.buffer.read()
    if not data:
        return
    s = data.decode(errors="ignore")
    main.safe_float(s)
    main.copy_image_to_storage(s)

if __name__ == "__main__":
    main_fuzz()

