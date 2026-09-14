# Copyright 2026 Camptocamp SA
# @author: Simone Orsi
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import ast
import re
from pathlib import Path

# Deliberately duplicated from OCA/maintainer-tools (tools/manifest.py, added in
# https://github.com/OCA/maintainer-tools/pull/663) rather than depending on it:
# that project installs a bare top-level `tools` module (collision-prone to import
# from another package) and pulls in a large, unrelated dependency set (selenium,
# twine, ERPpeek, ...) just to reuse this small helper.

MANIFEST_NAME = "__manifest__.py"


def mark_manifest_uninstallable(manifest_text):
    """Return `manifest_text` with `installable` forced to `False`."""
    manifest = ast.literal_eval(manifest_text)
    if "installable" not in manifest:
        src = r",?\s*}\s*$"
        dest = ",\n    'installable': False,\n}\n"
    else:
        src = "[\"']installable[\"']\\s*:\\s*True"
        dest = '"installable": False'
    return re.sub(src, dest, manifest_text, flags=re.DOTALL)


def mark_modules_uninstallable(addons_dir):
    """Set `installable = False` on every addon manifest in `addons_dir`."""
    for manifest_path in Path(addons_dir).glob(f"*/{MANIFEST_NAME}"):
        manifest_text = manifest_path.read_text(encoding="utf-8")
        new_manifest_text = mark_manifest_uninstallable(manifest_text)
        if new_manifest_text != manifest_text:
            manifest_path.write_text(new_manifest_text, encoding="utf-8")
