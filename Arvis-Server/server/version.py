"""Compatibility wrapper to expose version via 'server.version'.

NOTE: `from version import *` does NOT import names starting with `_`.
Our version constants are named like `__server_version__`, so we must
explicitly import them.
"""

from version import (  # noqa: F401
	__server_name__,
	__server_version__,
	API_MIN_CLIENT_VERSION,
	API_VERSION,
	check_client_compatibility,
	get_full_server_info,
	get_server_name,
	get_server_version,
)

__all__ = [
	"__server_name__",
	"__server_version__",
	"API_VERSION",
	"API_MIN_CLIENT_VERSION",
	"get_server_version",
	"get_server_name",
	"get_full_server_info",
	"check_client_compatibility",
]
