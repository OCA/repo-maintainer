# Copyright 2024 Camptocamp SA
# @author: Simone Orsi
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import shutil
import tempfile
from unittest import TestCase

from click.testing import CliRunner

from oca_repo_maintainer.cli.manage import add_branch, set_default_branch
from oca_repo_maintainer.tools.conf_file_manager import ConfFileManager

from .common import conf_path


class TestCliSetDefaultBranch(TestCase):
    def setUp(self):
        super().setUp()
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)
        shutil.copytree(conf_path.as_posix(), self.temp_dir, dirs_exist_ok=True)

    def _load_conf(self):
        return ConfFileManager(self.temp_dir).conf_loader.load_conf("repo")

    def test_set_default_branch(self):
        result = self.runner.invoke(
            set_default_branch,
            ["--conf-dir", self.temp_dir, "--branch", "15.0"],
        )
        self.assertEqual(result.exit_code, 0, result.output)
        conf = self._load_conf()
        # already known branch: becomes default, no duplicate added
        self.assertEqual(conf["test-repo-1"]["branches"], ["16.0", "15.0"])
        self.assertEqual(conf["test-repo-1"]["default_branch"], "15.0")
        # repo without a configured default_branch: gets one forced
        self.assertEqual(conf["test-repo-2"]["branches"], ["13.0", "12.0", "15.0"])
        self.assertEqual(conf["test-repo-2"]["default_branch"], "15.0")

    def test_set_default_branch_repo_whitelist(self):
        result = self.runner.invoke(
            set_default_branch,
            [
                "--conf-dir",
                self.temp_dir,
                "--branch",
                "15.0",
                "--repo-whitelist",
                "test-repo-2",
            ],
        )
        self.assertEqual(result.exit_code, 0, result.output)
        conf = self._load_conf()
        # not whitelisted: untouched
        self.assertEqual(conf["test-repo-1"]["default_branch"], "16.0")
        # whitelisted: new branch added and set as default
        self.assertEqual(conf["test-repo-2"]["branches"], ["13.0", "12.0", "15.0"])
        self.assertEqual(conf["test-repo-2"]["default_branch"], "15.0")

    def test_add_branch_no_default(self):
        result = self.runner.invoke(
            add_branch,
            ["--conf-dir", self.temp_dir, "--branch", "100.0", "--no-default"],
        )
        self.assertEqual(result.exit_code, 0, result.output)
        conf = self._load_conf()
        self.assertIn("100.0", conf["test-repo-1"]["branches"])
        self.assertNotEqual(conf["test-repo-1"]["default_branch"], "100.0")
