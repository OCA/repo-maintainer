# Copyright 2024 Camptocamp SA
# @author: Simone Orsi
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import shutil
import tempfile
from unittest import TestCase

from oca_repo_maintainer.tools.conf_file_manager import ConfFileManager

from .common import conf_path, conf_path_with_tools


class TestManager(TestCase):
    def test_add_branch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            shutil.copytree(conf_path.as_posix(), temp_dir, dirs_exist_ok=True)
            manager = ConfFileManager(temp_dir)
            manager.add_branch("100.0")

            conf = manager.conf_loader.load_conf("repo")
            self.assertTrue(conf)
            for __, repo_data in conf.items():
                self.assertIn("100.0", repo_data["branches"])
                if "default_branch" in repo_data:
                    self.assertEqual(repo_data["default_branch"], "100.0")

    def test_add_branch_no_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            shutil.copytree(conf_path.as_posix(), temp_dir, dirs_exist_ok=True)
            manager = ConfFileManager(temp_dir)
            manager.add_branch("100.0", default=False)

            conf = manager.conf_loader.load_conf("repo")
            self.assertTrue(conf)
            for __, repo_data in conf.items():
                self.assertIn("100.0", repo_data["branches"])
                if "default_branch" in repo_data:
                    self.assertNotEqual(repo_data["default_branch"], "100.0")

    def test_add_branch_repo_whitelist(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            shutil.copytree(conf_path.as_posix(), temp_dir, dirs_exist_ok=True)
            manager = ConfFileManager(temp_dir)
            manager.add_branch("100.0", default=True, repo_whitelist=["test-repo-2"])

            conf = manager.conf_loader.load_conf("repo")
            self.assertEqual(conf["test-repo-1"]["branches"], ["16.0", "15.0"])
            self.assertEqual(conf["test-repo-2"]["branches"], ["13.0", "12.0", "100.0"])

    def test_preserve_master(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            shutil.copytree(
                conf_path_with_tools.as_posix(), temp_dir, dirs_exist_ok=True
            )
            manager = ConfFileManager(temp_dir)
            conf = manager.conf_loader.load_conf("repo")

            self.assertEqual(conf["test-repo-for-addons"]["branches"], ["16.0", "15.0"])
            self.assertEqual(conf["test-repo-for-addons"]["default_branch"], "16.0")
            self.assertEqual(conf["test-repo-for-tools-1"]["branches"], ["master"])
            self.assertEqual(conf["test-repo-for-tools-1"]["default_branch"], "master")
            self.assertEqual(conf["test-repo-for-tools-2"]["branches"], [])
            self.assertEqual(conf["test-repo-for-tools-2"]["default_branch"], "main")
            self.assertEqual(
                conf["test-repo-for-tools-with-no-branches"]["branches"], []
            )
            self.assertEqual(
                conf["test-repo-for-tools-with-no-branches"]["default_branch"], "master"
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            shutil.copytree(
                conf_path_with_tools.as_posix(), temp_dir, dirs_exist_ok=True
            )
            manager = ConfFileManager(temp_dir)
            manager.add_branch("100.0")

            conf = manager.conf_loader.load_conf("repo")

            self.assertEqual(
                conf["test-repo-for-addons"]["branches"], ["16.0", "15.0", "100.0"]
            )
            self.assertEqual(conf["test-repo-for-addons"]["default_branch"], "100.0")
            self.assertEqual(conf["test-repo-for-tools-1"]["branches"], ["master"])
            self.assertEqual(conf["test-repo-for-tools-1"]["default_branch"], "master")
            self.assertEqual(conf["test-repo-for-tools-2"]["branches"], [])
            self.assertEqual(conf["test-repo-for-tools-2"]["default_branch"], "main")
            self.assertEqual(
                conf["test-repo-for-tools-with-no-branches"]["branches"], []
            )
            self.assertEqual(
                conf["test-repo-for-tools-with-no-branches"]["default_branch"], "master"
            )

    def test_skip_manual_mgmt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            shutil.copytree(
                conf_path_with_tools.as_posix(), temp_dir, dirs_exist_ok=True
            )
            manager = ConfFileManager(temp_dir)
            conf = manager.conf_loader.load_conf("repo")

            self.assertEqual(conf["test-repo-for-addons"]["branches"], ["16.0", "15.0"])
            self.assertEqual(conf["test-repo-for-addons"]["default_branch"], "16.0")
            self.assertEqual(
                conf["test-repo-for-addons-manual"]["branches"], ["16.0", "15.0"]
            )
            self.assertEqual(
                conf["test-repo-for-addons-manual"]["default_branch"], "16.0"
            )
            self.assertEqual(
                conf["test-repo-for-addons-manual"]["manual_branch_mgmt"], True
            )

            manager.add_branch("100.0")

            conf = manager.conf_loader.load_conf("repo")

            self.assertEqual(
                conf["test-repo-for-addons"]["branches"], ["16.0", "15.0", "100.0"]
            )
            self.assertEqual(conf["test-repo-for-addons"]["default_branch"], "100.0")
            self.assertEqual(
                conf["test-repo-for-addons-manual"]["branches"], ["16.0", "15.0"]
            )
            self.assertEqual(
                conf["test-repo-for-addons-manual"]["default_branch"], "16.0"
            )
