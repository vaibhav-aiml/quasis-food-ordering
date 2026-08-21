"""Blinkit Appium Diagnostic & Smoke Test CLI.

Usage:
    python scripts/smoke_test_blinkit.py --check-env
    python scripts/smoke_test_blinkit.py --inspect-screen
    python scripts/smoke_test_blinkit.py --search "Amul milk"
    python scripts/smoke_test_blinkit.py --add-to-cart "Amul Taaza Toned Milk"
    python scripts/smoke_test_blinkit.py --checkout
"""

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Configure UTF-8 for console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.adapters.blinkit.appium_adapter import BlinkitAppiumAdapter
from app.adapters.blinkit.locators import LOCATORS
from app.adapters.types import SearchQuery
from app.automation.driver_manager import DriverManager
from app.core.config import get_settings
from app.domain.product import ProductRequest
from app.domain.raw_product_result import RawProductResult


def check_env() -> bool:
    """Check ADB, connected Android devices, Blinkit package, and Appium server."""
    print("=" * 60)
    print("BLINKIT APPIUM ENVIRONMENT DIAGNOSTICS")
    print("=" * 60)
    all_ok = True
    devices = []

    # 1. ADB check
    try:
        res = subprocess.run(["adb", "devices"], capture_output=True, text=True, check=True)
        lines = [line.strip() for line in res.stdout.strip().split("\n")[1:] if line.strip()]
        devices = [line.split()[0] for line in lines if "device" in line]
        if devices:
            print(f"[OK] ADB Devices found: {', '.join(devices)}")
        else:
            print("[WARN] No active Android devices/emulators attached via ADB.")
            print("       -> Start an emulator or connect a device with USB debugging enabled.")
            all_ok = False
    except Exception as e:
        print(f"[FAIL] ADB not available: {e}")
        all_ok = False

    # 2. Blinkit package check on device
    if devices:
        try:
            device = devices[0]
            pkg = LOCATORS.app_package
            res = subprocess.run(
                ["adb", "-s", device, "shell", "pm", "list", "packages", pkg],
                capture_output=True,
                text=True,
                check=True,
            )
            if pkg in res.stdout:
                print(f"[OK] Package '{pkg}' is installed on device '{device}'.")
            else:
                print(f"[WARN] Package '{pkg}' NOT found on device '{device}'.")
                print(f"       -> Please install the Blinkit app on your device.")
                all_ok = False
        except Exception as e:
            print(f"[WARN] Could not verify installed packages: {e}")

    # 3. Appium server check
    settings = get_settings()
    appium_url = settings.appium_server_url.rstrip("/")
    candidates = [
        f"{appium_url}/status",
        f"{appium_url}/wd/hub/status" if not appium_url.endswith("/wd/hub") else f"{appium_url}/status",
    ]
    appium_reachable = False
    for status_url in candidates:
        try:
            req = urllib.request.Request(status_url, headers={"User-Agent": "ShoppingAgentSmokeTest"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                ready = data.get("value", {}).get("ready", True)
                print(f"[OK] Appium Server reachable at {status_url} (ready={ready})")
                appium_reachable = True
                break
        except Exception:
            continue

    if not appium_reachable:
        print(f"[FAIL] Appium Server not reachable at {appium_url} or {appium_url}/wd/hub")
        print("       -> Start Appium via: npx appium (or appium server)")
        all_ok = False

    print("=" * 60)
    return all_ok


def inspect_screen() -> None:
    """Inspect current foreground activity and dump XML hierarchy."""
    print("=" * 60)
    print("DEVICE SCREEN INSPECTION")
    print("=" * 60)
    try:
        res = subprocess.run(["adb", "devices"], capture_output=True, text=True, check=True)
        lines = [line.strip() for line in res.stdout.strip().split("\n")[1:] if line.strip()]
        devices = [line.split()[0] for line in lines if "device" in line]
        if not devices:
            print("[FAIL] No connected Android device found.")
            return

        device = devices[0]
        # Current focus
        focus_res = subprocess.run(
            ["adb", "-s", device, "shell", "dumpsys", "window", "windows"],
            capture_output=True,
            text=True,
        )
        focus_lines = [l.strip() for l in focus_res.stdout.split("\n") if "mCurrentFocus" in l or "mFocusedApp" in l]
        print(f"Device: {device}")
        for l in focus_lines:
            print(f"Focus info: {l}")

        # Dump hierarchy
        print("\nDumping UI hierarchy XML to blinkit_screen_dump.xml...")
        dump_res = subprocess.run(
            ["adb", "-s", device, "exec-out", "uiautomator", "dump", "/dev/tty"],
            capture_output=True,
            text=True,
        )
        if dump_res.stdout:
            out_file = backend_dir / "blinkit_screen_dump.xml"
            out_file.write_text(dump_res.stdout, encoding="utf-8")
            print(f"[OK] UI hierarchy saved to {out_file}")
            print(f"File size: {len(dump_res.stdout)} chars")
    except Exception as e:
        print(f"[FAIL] Screen inspection failed: {e}")


def test_search(query_text: str) -> None:
    """Run a live search against Blinkit using BlinkitAppiumAdapter."""
    print(f"Executing live Blinkit search for: '{query_text}'...")
    settings = get_settings()
    adapter = BlinkitAppiumAdapter(settings)
    query = SearchQuery(products=[ProductRequest(name=query_text)])

    try:
        results = adapter.search(query, timeout=15.0)
        print(f"\nSearch returned {len(results)} items:")
        for idx, item in enumerate(results, 1):
            print(f"  [{idx}] {item.raw_title} | Price: {item.raw_price} | ETA: {item.raw_eta} | Qty: {item.raw_quantity}")
    except Exception as exc:
        print(f"\n[ERROR] Search failed: {exc}")


def test_add_to_cart(product_title: str) -> None:
    """Test adding an item to the Blinkit cart."""
    print(f"Executing live Blinkit add_to_cart for: '{product_title}'...")
    settings = get_settings()
    adapter = BlinkitAppiumAdapter(settings)
    product = RawProductResult(
        store_id="blinkit",
        raw_title=product_title,
        raw_price="0",
        raw_eta="unknown",
        raw_quantity="unknown",
    )
    result = adapter.add_to_cart(product)
    if result.success:
        print(f"[SUCCESS] Product '{product_title}' added to cart successfully!")
    else:
        print(f"[FAILED] Could not add '{product_title}' to cart: {result.message}")


def test_checkout() -> None:
    """Test navigating to checkout up to the payment screen."""
    print("Executing live Blinkit checkout navigation...")
    settings = get_settings()
    adapter = BlinkitAppiumAdapter(settings)
    state = adapter.checkout()
    print(f"Checkout State: status='{state.status}', message='{state.message}'")
    if state.status == "ready_for_payment":
        print("[SUCCESS] Successfully reached payment screen without confirming payment.")
    else:
        print(f"[FAILED] Checkout failed: {state.message}")


def main():
    parser = argparse.ArgumentParser(description="Blinkit Appium Diagnostic & Smoke Test")
    parser.add_argument("--check-env", action="store_true", help="Check ADB, device, package, and Appium server")
    parser.add_argument("--inspect-screen", action="store_true", help="Inspect current foreground app & UI XML hierarchy")
    parser.add_argument("--search", type=str, help="Execute live search for product term")
    parser.add_argument("--add-to-cart", type=str, help="Execute live add to cart for product title")
    parser.add_argument("--checkout", action="store_true", help="Execute live checkout up to payment screen")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    if args.check_env:
        check_env()
    if args.inspect_screen:
        inspect_screen()
    if args.search:
        test_search(args.search)
    if args.add_to_cart:
        test_add_to_cart(args.add_to_cart)
    if args.checkout:
        test_checkout()


if __name__ == "__main__":
    main()
