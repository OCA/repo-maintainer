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

    def test_set_default_branch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            shutil.copytree(conf_path.as_posix(), temp_dir, dirs_exist_ok=True)
            manager = ConfFileManager(temp_dir)
            manager.set_default_branch("15.0")

            conf = manager.conf_loader.load_conf("repo")
            # already known branch: becomes default, no duplicate added
            self.assertEqual(conf["test-repo-1"]["branches"], ["16.0", "15.0"])
            self.assertEqual(conf["test-repo-1"]["default_branch"], "15.0")
            # repo has no `default_branch` key at all: it gets forced
            self.assertEqual(conf["test-repo-2"]["branches"], ["13.0", "12.0", "15.0"])
            self.assertEqual(conf["test-repo-2"]["default_branch"], "15.0")

    def test_set_default_branch_repo_whitelist(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            shutil.copytree(conf_path.as_posix(), temp_dir, dirs_exist_ok=True)
            manager = ConfFileManager(temp_dir)
            manager.set_default_branch("15.0", repo_whitelist=["test-repo-2"])

            conf = manager.conf_loader.load_conf("repo")
            # not whitelisted: untouched
            self.assertEqual(conf["test-repo-1"]["default_branch"], "16.0")
            self.assertEqual(conf["test-repo-1"]["branches"], ["16.0", "15.0"])
            # whitelisted: forced
            self.assertEqual(conf["test-repo-2"]["branches"], ["13.0", "12.0", "15.0"])
            self.assertEqual(conf["test-repo-2"]["default_branch"], "15.0")

    def test_set_default_branch_preserve_master(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            shutil.copytree(
                conf_path_with_tools.as_posix(), temp_dir, dirs_exist_ok=True
            )
            manager = ConfFileManager(temp_dir)
            manager.set_default_branch("100.0")

            conf = manager.conf_loader.load_conf("repo")
            self.assertEqual(
                conf["test-repo-for-addons"]["branches"], ["16.0", "15.0", "100.0"]
            )
            self.assertEqual(conf["test-repo-for-addons"]["default_branch"], "100.0")
            # frozen (master/main default branches): untouched
            self.assertEqual(conf["test-repo-for-tools-1"]["branches"], ["master"])
            self.assertEqual(conf["test-repo-for-tools-1"]["default_branch"], "master")
            self.assertEqual(conf["test-repo-for-tools-2"]["branches"], [])
            self.assertEqual(conf["test-repo-for-tools-2"]["default_branch"], "main")

    def test_set_default_branch_skip_manual_mgmt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            shutil.copytree(
                conf_path_with_tools.as_posix(), temp_dir, dirs_exist_ok=True
            )
            manager = ConfFileManager(temp_dir)
            manager.set_default_branch("100.0")

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


class TestMutate(TestCase):
    """Unit tests for the per-repo mutation helpers, without touching disk."""

    def setUp(self):
        super().setUp()
        self.manager = ConfFileManager(conf_path.as_posix())

    def test_mutate_add_branch(self):
        repo_data = {"branches": ["16.0", "15.0"], "default_branch": "16.0"}
        changed = self.manager._mutate_add_branch("100.0", True, repo_data)
        self.assertTrue(changed)
        self.assertEqual(repo_data["branches"], ["16.0", "15.0", "100.0"])
        self.assertEqual(repo_data["default_branch"], "100.0")

    def test_mutate_add_branch_no_default(self):
        repo_data = {"branches": ["16.0", "15.0"], "default_branch": "16.0"}
        changed = self.manager._mutate_add_branch("100.0", False, repo_data)
        self.assertTrue(changed)
        self.assertEqual(repo_data["branches"], ["16.0", "15.0", "100.0"])
        self.assertEqual(repo_data["default_branch"], "16.0")

    def test_mutate_add_branch_already_present(self):
        # branch already listed: not duplicated, but still promoted to default
        repo_data = {"branches": ["16.0", "15.0"], "default_branch": "16.0"}
        changed = self.manager._mutate_add_branch("15.0", True, repo_data)
        self.assertTrue(changed)
        self.assertEqual(repo_data["branches"], ["16.0", "15.0"])
        self.assertEqual(repo_data["default_branch"], "15.0")

    def test_mutate_add_branch_frozen(self):
        repo_data = {"branches": ["master"], "default_branch": "master"}
        changed = self.manager._mutate_add_branch("100.0", True, repo_data)
        self.assertFalse(changed)
        self.assertEqual(repo_data["branches"], ["master"])
        self.assertEqual(repo_data["default_branch"], "master")

    def test_mutate_add_branch_no_default_key(self):
        # `default_branch` not controlled via config: don't touch it
        repo_data = {"branches": ["16.0", "15.0"]}
        changed = self.manager._mutate_add_branch("100.0", True, repo_data)
        self.assertTrue(changed)
        self.assertEqual(repo_data["branches"], ["16.0", "15.0", "100.0"])
        self.assertNotIn("default_branch", repo_data)

    def test_mutate_set_default_already_default(self):
        repo_data = {"branches": ["16.0", "15.0"], "default_branch": "15.0"}
        changed = self.manager._mutate_set_default("15.0", repo_data)
        self.assertFalse(changed)
        self.assertEqual(repo_data["branches"], ["16.0", "15.0"])

    def test_mutate_set_default_known_branch(self):
        repo_data = {"branches": ["16.0", "15.0"], "default_branch": "16.0"}
        changed = self.manager._mutate_set_default("15.0", repo_data)
        self.assertTrue(changed)
        self.assertEqual(repo_data["branches"], ["16.0", "15.0"])
        self.assertEqual(repo_data["default_branch"], "15.0")

    def test_mutate_set_default_new_branch(self):
        repo_data = {"branches": ["13.0", "12.0"]}
        changed = self.manager._mutate_set_default("15.0", repo_data)
        self.assertTrue(changed)
        self.assertEqual(repo_data["branches"], ["13.0", "12.0", "15.0"])
        self.assertEqual(repo_data["default_branch"], "15.0")

    def test_mutate_set_default_frozen(self):
        repo_data = {"branches": ["master"], "default_branch": "master"}
        changed = self.manager._mutate_set_default("100.0", repo_data)
        self.assertFalse(changed)
        self.assertEqual(repo_data["branches"], ["master"])
        self.assertEqual(repo_data["default_branch"], "master")
