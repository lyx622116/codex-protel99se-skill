"""Optional read-only Win32 window inspection. No input, launch or save actions."""

import argparse
import json
import sys


def inspect_windows(pid, handle=None, details=False):
    if sys.platform != "win32":
        raise RuntimeError("This optional inspector requires Windows")
    from pywinauto import Application
    import win32process

    app = Application(backend="win32").connect(process=pid, timeout=10)
    windows = app.windows(visible_only=False)
    result = {"pid": pid, "read_only": True, "windows": []}
    for window in windows:
        result["windows"].append({
            "handle": window.handle, "title": window.window_text(),
            "class": window.class_name(), "visible": window.is_visible(),
            "enabled": window.is_enabled(),
        })
    if handle is not None:
        if win32process.GetWindowThreadProcessId(handle)[1] != pid:
            raise ValueError("Selected window belongs to a different process")
        window = app.window(handle=handle).wrapper_object()
        result["selected"] = {"handle": handle, "title": window.window_text(),
                              "class": window.class_name()}
        if details:
            result["children"] = [
                {"handle": item.handle, "title": item.window_text(), "class": item.class_name()}
                for item in window.children()
            ]
            menu = window.menu()
            result["menu"] = menu.get_properties() if menu else None
    return result


def positive_int(value):
    number = int(value, 0)
    if number <= 0:
        raise argparse.ArgumentTypeError("Expected a positive PID or handle")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", required=True, type=positive_int)
    parser.add_argument("--handle", type=positive_int)
    parser.add_argument("--details", action="store_true", help="Read children and menus of the chosen window")
    args = parser.parse_args(argv)
    if args.details and args.handle is None:
        parser.error("--details requires an observed --handle")
    try:
        print(json.dumps(inspect_windows(args.pid, args.handle, args.details),
                         ensure_ascii=False, indent=2, default=str))
        return 0
    except Exception as error:
        print(json.dumps({"error": str(error), "native_verified": False}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
