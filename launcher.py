"""Portable Windows entry point. No services start until a mode is chosen."""
import multiprocessing
from pathlib import Path
import sys


def main():
    multiprocessing.freeze_support()
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root / "webrtc"))
    args = sys.argv[1:]
    if not args:
        print("Tailkey / 遠端數字鍵盤\n")
        print("1. Same Wi-Fi or phone hotspot / 同 Wi-Fi 或手機熱點")
        print("2. Tailcat + WebRTC experiment / 跨網路直連原型")
        print("0. Exit / 離開\n")
        try:
            choice = input("Choose / 選擇 [1]: ").strip() or "1"
        except EOFError:
            return
        if choice == "0":
            return
        if choice not in ("1", "2"):
            print("Invalid choice / 選項無效")
            return
        args = ["--tailcat"] if choice == "2" else []
    sys.argv = ["Tailkey", *args]
    from app import main as run
    try:
        run()
    except KeyboardInterrupt:
        pass
    except Exception as error:
        print(f"Tailkey stopped / 啟動失敗: {error}", file=sys.stderr)
        input("Press Enter to close / 按 Enter 關閉…")
    except SystemExit as error:
        if error.code:
            input("Press Enter to close / 按 Enter 關閉…")


if __name__ == "__main__":
    main()
