# Copyright 2024 Camptocamp SA
# @author: Simone Orsi
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging
import sys

from .utils import ConfLoader

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logging.basicConfig(level=logging.INFO, handlers=[handler])

_logger = logging.getLogger(__name__)


class ConfFileManager:
    """Update existing configuration files."""

    def __init__(self, conf_dir):
        self.conf_dir = conf_dir
        self.conf_loader = ConfLoader(self.conf_dir)
        self.conf_repo = self.conf_loader.load_conf(
            "repo", checksum=False, by_filepath=True
        )

    def add_branch(self, branch, default=True, repo_whitelist=None):
        """Add a branch to all repositories in the configuration."""
        for filepath, repo in self.conf_repo.items():
            changed = False
            for repo_slug, repo_data in repo.items():
                if repo_whitelist and repo_slug not in repo_whitelist:
                    continue
                if self._has_manual_branch_mgmt(repo_data):
                    _logger.info(
                        "Skipping repo %s as manual_branch_mgmt is enabled.",
                        filepath.as_posix(),
                    )
                    continue
                if self._can_add_new_branch(branch, repo_data):
                    repo_data["branches"].append(branch)
                    changed = True
                if default and self._can_change_default_branch(repo_data):
                    repo_data["default_branch"] = branch
                    changed = True
            if changed:
                self.conf_loader.save_conf(filepath, repo)
                _logger.info("Branch %s added to %s.", branch, filepath.as_posix())

    def _has_manual_branch_mgmt(self, repo_data):
        return repo_data.get("manual_branch_mgmt")

    frozen_branches = ("master", "main")

    def _can_add_new_branch(self, branch, repo_data):
        branches = repo_data["branches"]
        return (
            branch not in branches
            and all(x not in branches for x in self.frozen_branches)
            and repo_data.get("default_branch") not in self.frozen_branches
        )

    def _can_change_default_branch(self, repo_data):
        return (
            # Only change if default branch is controlled via config file
            "default_branch" in repo_data
            # If the branch is "master" it means this is likely the repo of a tool
            # and we have only one working branch.
            and repo_data["default_branch"] not in self.frozen_branches
        )
