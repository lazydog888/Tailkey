"""Portable Windows entry point. Picks tailcat or same-Wi-Fi mode automatically."""
import multiprocessing
from pathlib import Path
import sys


def main():
    multiprocessing.freeze_support()
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root / "webrtc"))
    args = sys.argv[1:]
    # No menu: tailcat when DERP is reachable, otherwise same-Wi-Fi. `--lan` forces same-Wi-Fi only.
    if not args:
        args = ["--auto"]
    elif args == ["--lan"]:
        args = []
    print("Tailkey / 遠端數字鍵盤", flush=True)
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
