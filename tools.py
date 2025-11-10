# tools.py
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

# Path to the JSON catalog of apps
CATALOG_PATH = Path(__file__).parent / "apps_catalog.json"


def load_apps() -> List[Dict[str, Any]]:
    """Load the femtech apps catalog from JSON."""
    with open(CATALOG_PATH, "r") as f:
        return json.load(f)


def recommend_apps(
    goal: str,
    platform: Optional[str] = None,
    max_price: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Simple tool: recommend a few femtech apps based on goal and user preferences.

    goal: e.g. "menopause_symptom_tracking" or "cycle_tracking"
    platform: e.g. "iOS" or "Android" (optional)
    max_price: maximum monthly price in USD (optional)
    """
    apps = load_apps()
    results: List[Dict[str, Any]] = []

    for app in apps:
        # Filter by goal
        if goal not in app.get("goals", []):
            continue

        # Filter by platform if provided
        if platform and platform not in app.get("platforms", []):
            continue

        # Filter by price if provided
        price = app.get("pricing", {}).get("monthly", 0)
        if max_price is not None and price > max_price:
            continue

        results.append(app)

    # Keep it small for UX
    return results[:3]
