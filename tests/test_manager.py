# Copyright 2023 Dixmit
# @author: Enric Tobella
# Copyright 2023 Camptocamp SA
# @author: Simone Orsi
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import hashlib
import json
import os
import tempfile
from unittest import TestCase, mock

import copier

from oca_repo_maintainer.tools.manager import RepoManager

from .common import conf_path, conf_path2, vcr


class TestManager(TestCase):
    def setUp(self):
        super().setUp()
        self.org = "OCA"
        # IMPORTANT: when you want to record or update cassettes
        # you  must replace this token w/ a real one before running tests.
        # SUPER IMPORTANT: after you do that,
        # replace the real token everywhere before staging changes
        self.token = "ghp_fake_test_token"
        self.manager = RepoManager(conf_path.as_posix(), self.org, self.token)

    def test_init(self):
        self.assertEqual(self.manager.org, self.org)
        self.assertEqual(self.manager.token, self.token)
        self.assertEqual(
            self.manager.conf_global,
            {
                "owner": "board",
                "template": "git+https://github.com/OCA/oca-addons-repo-template",
                "team_maintainers": [],
                "maintainers": [],
            },
        )
        self.assertEqual(
            self.manager.conf_psc,
            {
                "test-team-1": {
                    "name": "Test team 1",
                    "members": ["simahawk"],
                    "representatives": ["simahawk"],
                },
                "test-team-2": {
                    "name": "Test team 2",
                    "members": ["simahawk", "etobella"],
                    "representatives": ["etobella"],
                },
            },
        )
        self.assertEqual(
            self.manager.conf_repo,
            {
                "test-repo-1": {
                    "name": "Test repo 1",
                    "description": "Repo used to run real tests on oca-repo-manage tool.",
                    "psc": "test-team-1",
                    "maintainers": [],
                    "default_branch": "16.0",
                    "branches": ["16.0", "15.0"],
                    "category": "Logistics",
                },
                "test-repo-2": {
                    "name": "Repository 2",
                    "description": "Repo used to run real tests on oca-repo-manage tool.",
                    "psc": "test-team-2",
                    "maintainers": ["simahawk", "etobella"],
                    "branches": ["13.0", "12.0"],
                    "category": "Accounting",
                },
            },
        )
        self.assertEqual(
            self.manager.new_repo_template, self.manager.conf_global["template"]
        )

    def test_checksum(self):
        cs_filepath = conf_path / "checksum.yml"
        if cs_filepath.exists():
            os.remove(cs_filepath.as_posix())
        for fname in ("psc/psc1", "psc/psc2", "repo/repo1", "repo/repo2"):
            filepath = conf_path / f"{fname}.yml"
            with filepath.open() as fd:
                self.assertEqual(
                    self.manager.conf_loader.checksum[
                        filepath.relative_to(conf_path).as_posix()
                    ],
                    hashlib.md5(fd.read().encode()).hexdigest(),
                )
        self.manager._save_checksum()
        self.assertTrue(cs_filepath.exists())
        os.remove(cs_filepath.as_posix())

    @vcr.use_cassette("setup_gh")
    def test_setup_gh(self):
        self.manager._setup_gh()
        self.assertTrue(self.manager.gh)
        self.assertEqual(self.manager.gh_org.url, "https://api.github.com/orgs/OCA")

    def test_process_psc(self):
        with vcr.use_cassette("setup_gh"):
            self.manager._setup_gh()
        with vcr.use_cassette("process_psc") as cassette:
            self.manager._process_psc()
        # check reques to get existing team
        expected_requests = (
            # check the 1st team that already exists
            {
                "url": "https://api.github.com/orgs/OCA/teams/test-team-1",
                "method": "GET",
            },
            # get members
            {
                "url": "https://api.github.com/organizations/119798021/team/8630739/members?role=member&per_page=100",  # noqa
                "method": "GET",
            },
            # get maintainers
            {
                "url": "https://api.github.com/organizations/119798021/team/8630739/members?role=maintainer&per_page=100",  # noqa
                "method": "GET",
            },
            # set simahawk as member
            {
                "url": "https://api.github.com/organizations/119798021/team/8630739/memberships/simahawk",  # noqa
                "method": "PUT",
                "body": {"role": "member"},
            },
            # get team 2 which does NOT exist
            {
                "url": "https://api.github.com/orgs/OCA/teams/test-team-2",  # noqa
                "method": "GET",
            },
            # create team
            {
                "url": "https://api.github.com/orgs/OCA/teams",
                "method": "POST",
                "body": {
                    "name": "test-team-2",
                    "repo_names": [],
                    "maintainers": [],
                    "permission": "pull",
                    "privacy": "closed",
                },
            },
            # get members
            {
                "url": "https://api.github.com/organizations/119798021/team/8630747/members?role=member&per_page=100",  # noqa
                "method": "GET",
            },
            # get maintainers
            {
                "url": "https://api.github.com/organizations/119798021/team/8630747/members?role=maintainer&per_page=100",  # noqa
                "method": "GET",
            },
            # set simahawk as member
            {
                "url": "https://api.github.com/organizations/119798021/team/8630747/memberships/simahawk",  # noqa
                "method": "PUT",
                "body": {"role": "member"},
            },
            # set etobella as member
            {
                "url": "https://api.github.com/organizations/119798021/team/8630747/memberships/etobella",  # noqa
                "method": "PUT",
                "body": {"role": "member"},
            },
            # set etobella as maintainer
            {
                "url": "https://api.github.com/organizations/119798021/team/8630747/memberships/etobella",  # noqa
                "method": "PUT",
                "body": {"role": "maintainer"},
            },
        )
        for req, expected in zip(cassette.requests, expected_requests):
            for k in ("url", "method"):
                self.assertEqual(getattr(req, k), expected[k])
            if expected.get("body"):
                self.assertEqual(json.loads(req.body), expected["body"])

    def test_process_repo(self):
        with vcr.use_cassette("setup_gh"):
            self.manager._setup_gh()
        # generate clone dir here and force it to take control on it
        clone_dir_1 = tempfile.mkdtemp()
        clone_dir_2 = tempfile.mkdtemp()

        def mkdtemp():
            # after the 1st git operation the dir will be removed
            if os.path.exists(clone_dir_1):
                return clone_dir_1
            return clone_dir_2

        with vcr.use_cassette("process_repositories") as cassette:
            with (
                mock.patch.object(tempfile, "mkdtemp", mkdtemp),
                mock.patch.object(RepoManager, "_run_cmd") as run_cmd,
                # FIXME: this must be tested too
                mock.patch.object(RepoManager, "_setup_user"),
                mock.patch.object(copier, "run_copy") as run_copy,
            ):
                self.manager._process_repositories()

        # check 2 calls to copier, 1 for branch 13 and one for branch 12
        expected_copier_cmd = (
            self._expected_copier_cmd(clone_dir_1, "12.0"),
            self._expected_copier_cmd(clone_dir_2, "13.0"),
        )
        for call, cmd in zip(run_copy.call_args_list, expected_copier_cmd):
            self.assertEqual(call.args, cmd["cmd"])
            self.assertEqual(call.kwargs, cmd["kw"])
        # check git operations
        expected_git_ops = self._expected_git_ops(
            clone_dir_1, "12.0"
        ) + self._expected_git_ops(clone_dir_2, "13.0")

        for call, op in zip(run_cmd.call_args_list, expected_git_ops):
            self.assertEqual(call.args[0], op["cmd"])
            self.assertEqual(call.kwargs, op["kw"])

        # sorted as seen in cassette (not real calls)
        expected_requests = (
            # get repos
            {
                "url": "https://api.github.com/orgs/OCA/repos?per_page=100",
                "method": "GET",
            },
            # get board team
            {
                "url": "https://api.github.com/orgs/OCA/teams/board",
                "method": "GET",
            },
            # get repo
            {
                "url": "https://api.github.com/repos/OCA/test-repo-1",
                "method": "GET",
            },
            # get branches
            {
                "url": "https://api.github.com/repos/OCA/test-repo-1/branches?per_page=100",  # noqa
                "method": "GET",
            },
            # get team
            {
                "url": "https://api.github.com/orgs/OCA/teams/test-team-1",
                "method": "GET",
            },
            # get team repos
            {
                "url": "https://api.github.com/organizations/119798021/team/8630739/repos?per_page=100",  # noqa
                "method": "GET",
            },
            # set default branch
            {
                "url": "https://api.github.com/repos/OCA/test-repo-1",
                "method": "PATCH",
                "body": {"name": "test-repo-1", "default_branch": "16.0"},
            },
            # create repo 2
            {
                "url": "https://api.github.com/orgs/OCA/repos",
                "method": "POST",
                "body": {
                    "name": "test-repo-2",
                    "description": "test-repo-2",
                    "homepage": "",
                    "private": False,
                    "has_issues": True,
                    "has_wiki": True,
                    "license_template": "",
                    "auto_init": False,
                    "gitignore_template": "",
                    "has_projects": True,
                    "team_id": 7089887,
                },
            },
            # get team 2
            {
                "url": "https://api.github.com/orgs/OCA/teams/test-team-2",
                "method": "GET",
            },
            # get team 2 repos
            {
                "url": "https://api.github.com/organizations/119798021/team/8630747/repos?per_page=100",  # noqa
                "method": "GET",
            },
            # set perm
            {
                "url": "https://api.github.com/organizations/119798021/team/8630747/repos/OCA/test-repo-2",  # noqa
                "method": "PUT",
                "body": {"permission": "push"},
            },
            # add user on repo
            {
                "url": "https://api.github.com/repos/OCA/test-repo-2/collaborators/simahawk",  # noqa
                "method": "PUT",
                "body": None,
            },
            {
                "url": "https://api.github.com/user",
                "method": "GET",
            },
            {
                "url": "https://api.github.com/user",
                "method": "GET",
            },
            # get repo collaborators
            {
                "url": (
                    "https://api.github.com/repos/OCA/"
                    "test-repo-1/collaborators?affiliation=all&per_page=100"
                ),
                "method": "GET",
            },
            # get repo collaborators
            {
                "url": (
                    "https://api.github.com/repos/OCA/"
                    "test-repo-2/collaborators?affiliation=all&per_page=100"
                ),
                "method": "GET",
            },
            # remove user on repo
            {
                "url": "https://api.github.com/repos/OCA/test-repo-2/collaborators/etobella",
                "method": "PUT",
            },
            {
                "url": "https://api.github.com/repos/OCA/test-repo-2/collaborators/petrus-v",
                "method": "DELETE",
            },
            {
                "url": "https://api.github.com/repos/OCA/test-repo-1/collaborators/simahawk",
                "method": "DELETE",
            },
        )
        for req, expected in zip(cassette.requests, expected_requests):
            for k in ("url", "method"):
                self.assertEqual(
                    getattr(req, k), expected[k], f"{k} wrong for {req.url}"
                )
            if expected.get("body"):
                self.assertEqual(json.loads(req.body), expected["body"])

    def _expected_copier_cmd(self, clone_dir, branch):
        return {
            "cmd": ("git+https://github.com/OCA/oca-addons-repo-template", clone_dir),
            "kw": {
                "data": {
                    "odoo_version": branch,
                    "repo_description": "test-repo-2",
                    "repo_name": "test-repo-2",
                    "repo_slug": "test-repo-2",
                },
                "defaults": True,
                "unsafe": True,
            },
        }

    def _expected_git_ops(self, clone_dir, branch):
        ops = (
            {
                "cmd": ["git", "init"],
                "kw": {
                    "cwd": clone_dir,
                },
            },
            {
                "cmd": ["git", "add", "-A"],
                "kw": {
                    "cwd": clone_dir,
                },
            },
            {
                "cmd": ["git", "commit", "-m", "Initial commit"],
                "kw": {
                    "cwd": clone_dir,
                },
            },
            {
                "cmd": ["git", "checkout", "-b", branch],
                "kw": {
                    "cwd": clone_dir,
                },
            },
            {
                "cmd": [
                    "git",
                    "remote",
                    "add",
                    "origin",
                    "https://api.github.com/repos/OCA/test-repo-2",
                ],
                "kw": {
                    "cwd": clone_dir,
                },
            },
            {
                "cmd": [
                    "git",
                    "remote",
                    "set-url",
                    "--push",
                    "origin",
                    f"https://{self.token}@github.com/OCA/test-repo-2",
                ],
                "kw": {
                    "cwd": clone_dir,
                },
            },
            {
                "cmd": ["git", "push", "origin", "HEAD"],
                "kw": {
                    "cwd": clone_dir,
                },
            },
        )
        return ops

    # TODO: do the same for repos
    def test_process_psc_no_change(self):
        cs_filepath = conf_path2 / "checksum.yml"
        if cs_filepath.exists():
            os.remove(cs_filepath.as_posix())
        manager = RepoManager(conf_path2.as_posix(), self.org, self.token)
        self.assertTrue(manager.conf_psc)
        self.assertTrue(manager.conf_repo)
        manager._save_checksum()
        # FIXME: not sure why logs are not captured... however, this is working!
        # logger_name = "oca_repo_maintainer.tools.utils"
        # with self.assertLogs(logger_name, "INFO") as capt:
        #     manager = RepoManager(conf_path2.as_posix(), self.org, self.token)
        #     expected = [
        #         f"INFO:{logger_name}:psc/psc1.yml not changed: skipping",
        #         f"INFO:{logger_name}:psc/psc2.yml not changed: skipping",
        #         f"INFO:{logger_name}:repo/repo1.yml not changed: skipping",
        #         f"INFO:{logger_name}:repo/repo2.yml not changed: skipping",
        #     ]
        #     self.assertEqual(sorted(capt.output), sorted(expected))
        manager = RepoManager(conf_path2.as_posix(), self.org, self.token)
        self.assertFalse(manager.conf_psc)
        self.assertFalse(manager.conf_repo)
        # logger_name = "oca_repo_maintainer.tools.manager"
        # with self.assertLogs(logger_name, "INFO") as capt:
        #     manager._process_psc()
        #     expected = [
        #         f"INFO:{logger_name}:No team to process",
        #     ]
        #     self.assertEqual(capt.output, expected)
