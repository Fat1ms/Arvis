"""Skeleton adapter for optional Heretic integration.

Important: Heretic is AGPL-3.0. This module intentionally does not include
Heretic sources. It attempts to import the external package at runtime and
fails gracefully with instructions for the user.
"""
from typing import Any


class HereticEngine:
    def __init__(self):
        self.available = False
        try:
            # try dynamic import of heretic package or CLI wrapper
            import heretic  # type: ignore

            self.heretic = heretic
            self.available = True
        except Exception:
            self.heretic = None
            self.available = False

    def is_available(self) -> bool:
        return self.available

    def run_decensor(self, model_name: str, **kwargs: Any) -> str:
        """Run Heretic to decensor a model. Returns path to decensored model or raises.

        This is a placeholder; the real implementation must be provided by the
        integrator and only executed when the user explicitly installs Heretic.
        """
        if not self.available:
            raise RuntimeError(
                "Heretic is not installed. Install it manually (e.g. `pip install heretic-llm`) and restart Arvis. Heretic is AGPL-3.0 licensed."
            )

        # Example (pseudo): result = self.heretic.run(model_name, **kwargs)
        # return result
        raise NotImplementedError("Heretic integration must be implemented by the integrator.")
