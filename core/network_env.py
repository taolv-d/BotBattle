import os
from typing import Any, Dict

_PROXY_KEYS = [
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
]

_PATCHED = False


def configure_network_env(llm_config: Dict[str, Any]) -> None:
    """Disable inherited proxy settings unless the config explicitly opts in."""
    if llm_config.get("use_env_proxy", False):
        return

    for key in _PROXY_KEYS:
        os.environ.pop(key, None)

    _patch_requests_session()


def _patch_requests_session() -> None:
    global _PATCHED
    if _PATCHED:
        return

    try:
        import requests.sessions
    except Exception:
        return

    original_init = requests.sessions.Session.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.trust_env = False

    requests.sessions.Session.__init__ = patched_init
    _PATCHED = True
