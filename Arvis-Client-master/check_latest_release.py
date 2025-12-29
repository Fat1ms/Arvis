"""
Quick smoke test for UpdateChecker: prints latest release info and selected asset.
Run:
  python check_latest_release.py
Optionally override repository via ENV:
  set ARVIS_GITHUB_REPO=Fat1ms/Arvis-Client
"""

from utils.update_checker import UpdateChecker


def main() -> int:
    upd = UpdateChecker()
    info = upd.check_for_updates()
    if not info:
        print("No update available or failed to fetch latest release.")
        return 0

    print(f"Latest version: {info.get('version')} - {info.get('name')}")
    assets = info.get('assets', [])
    print(f"Assets ({len(assets)}):")
    for a in assets:
        print(f"  - {a.get('name')} :: {a.get('browser_download_url')}")

    # Try asset selection
    from pathlib import Path

    dl = upd.download_update(info, progress_callback=lambda p: None)
    if dl and Path(dl).exists():
        print(f"Selected asset downloaded to: {dl}")
    else:
        print("Failed to select or download asset.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
