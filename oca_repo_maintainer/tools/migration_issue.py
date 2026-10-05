# Copyright 2026 Camptocamp SA
# @author: Simone Orsi
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

# Ported from OCA/maintainer-tools (tools/create_migration_issue.py)
# so that migration issues get created by the same tool (and token)
# that creates new branches. See `manifest.py` for why we don't depend on it.

import re

MANIFESTS = ("__openerp__.py", "__manifest__.py")
ISSUE_LABELS = ("help wanted", "work in progress", "no stale")
WIKI_URL = "https://github.com/OCA/maintainer-tools/wiki"
# Same as `is_main_branch` in OCA/maintainer-tools
ODOO_VERSION_RE = re.compile(r"^(6\.1|\d+\.0)$")


def is_odoo_version(branch):
    return bool(ODOO_VERSION_RE.match(str(branch)))


def migration_issue_title(version):
    return f"Migration to version {version}"


def migration_issue_body(version, modules):
    body = (
        f"# Todo\n\n{WIKI_URL}/Migration-to-version-{version}\n\n"
        "# Modules to migrate\n\n"
    )
    body += "\n".join([f"- [ ] {x}" for x in modules])
    body += (
        f"\n\nMissing module? Check {WIKI_URL}/"
        "%5BFAQ%5D-Missing-modules-in-migration-issue-list"
    )
    return body
