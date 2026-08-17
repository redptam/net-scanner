import json
import os
import logging

LOG = logging.getLogger(__name__)

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".config", "net_scanner", "config.json")

# Ensure directory exists
os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)


def load_config():
    """Return a dict with network and ports settings.
    Returns empty dict on failure.
    """
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as exc:
        LOG.exception("Failed to load config: %s", exc)
        return {}


def save_config(network: str, ports: str):
    """Persist network/ports choices to config.json."""
    try:
        data = {"network": network, "ports": ports}
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as exc:
        LOG.exception("Failed to save config: %s", exc)

# ---------------------------------------------------------------------------
# Exported API
__all__ = ["load_config", "save_config", "CONFIG_FILE"]
