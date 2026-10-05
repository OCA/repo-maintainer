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
                    "maintainers": ["simahawk"],
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
            # set user on repo
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

    def test_get_previous_branch_picks_closest_lower(self):
        existing = {"14.0", "15.0", "16.0", "main"}
        self.assertEqual(self.manager._get_previous_branch("17.0", existing), "16.0")

    def test_get_previous_branch_none_falls_back_to_default(self):
        existing = {"main"}
        self.assertEqual(
            self.manager._get_previous_branch("17.0", existing, "main"), "main"
        )

    def test_get_previous_branch_none_available(self):
        existing = {"18.0"}
        self.assertIsNone(self.manager._get_previous_branch("17.0", existing))

    def test_init_branch_dispatches_to_scratch_by_default(self):
        with (
            mock.patch.object(RepoManager, "_init_branch_from_scratch") as from_scratch,
            mock.patch.object(
                RepoManager, "_init_branch_from_previous"
            ) as from_previous,
        ):
            gh_repo = mock.Mock(default_branch="16.0")
            self.manager._init_branch(
                "/tmp/clone",
                gh_repo,
                "17.0",
                {"branches": ["17.0"]},
                {"16.0"},
            )
        from_scratch.assert_called_once_with("/tmp/clone", gh_repo, "17.0")
        from_previous.assert_not_called()

    def test_init_branch_dispatches_to_previous_when_flagged(self):
        with (
            mock.patch.object(RepoManager, "_init_branch_from_scratch") as from_scratch,
            mock.patch.object(
                RepoManager, "_init_branch_from_previous"
            ) as from_previous,
        ):
            gh_repo = mock.Mock(default_branch="16.0")
            self.manager._init_branch(
                "/tmp/clone",
                gh_repo,
                "17.0",
                {"branches": ["17.0"], "new_branch_not_empty": True},
                {"16.0"},
            )
        from_previous.assert_called_once_with("/tmp/clone", gh_repo, "17.0", "16.0")
        from_scratch.assert_not_called()

    def test_init_branch_from_previous(self):
        clone_dir = tempfile.mkdtemp()
        gh_repo = mock.Mock(name="test-repo-2")
        gh_repo.name = "test-repo-2"
        with (
            mock.patch.object(RepoManager, "_run_cmd") as run_cmd,
            mock.patch.object(RepoManager, "_setup_user"),
            mock.patch.object(copier, "run_recopy") as run_recopy,
            mock.patch(
                "oca_repo_maintainer.tools.manager.mark_modules_uninstallable"
            ) as mark_uninstallable,
        ):
            self.manager._init_branch_from_previous(clone_dir, gh_repo, "17.0", "16.0")
        run_recopy.assert_called_once_with(
            clone_dir,
            data={
                "repo_name": "test-repo-2",
                "repo_slug": "test-repo-2",
                "repo_description": "test-repo-2",
                "odoo_version": "17.0",
            },
            defaults=True,
            overwrite=True,
            unsafe=True,
        )
        mark_uninstallable.assert_called_once_with(clone_dir)
        expected_cmds = (
            [
                "git",
                "clone",
                "--branch",
                "16.0",
                "--single-branch",
                f"https://{self.token}@github.com/OCA/test-repo-2",
                clone_dir,
            ],
            ["git", "checkout", "-b", "17.0"],
            ["git", "add", "-A"],
            ["git", "commit", "-m", "[MIG] Create 17.0 branch from 16.0"],
            ["git", "push", "origin", "HEAD"],
        )
        for call, cmd in zip(run_cmd.call_args_list, expected_cmds):
            self.assertEqual(call.args[0], cmd)
        os.rmdir(clone_dir)

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


class TestMigrationIssue(TestCase):
    def setUp(self):
        super().setUp()
        self.manager = RepoManager(conf_path.as_posix(), "OCA", "ghp_fake_test_token")

    def _named_mock(self, name, **kw):
        # `name` is a reserved Mock kwarg
        res = mock.Mock(**kw)
        res.name = name
        return res

    def _mock_repo(self, issues=(), milestones=(), labels=()):
        gh_repo = mock.Mock()
        gh_repo.name = "test-repo-1"
        gh_repo.issues.return_value = list(issues)
        gh_repo.milestones.return_value = list(milestones)
        gh_repo.labels.return_value = [self._named_mock(x) for x in labels]
        gh_repo.create_milestone.return_value = mock.Mock(number=7, title="17.0")
        return gh_repo

    def test_enabled(self):
        repo_data = {"branches": ["15.0", "16.0"]}
        enabled = self.manager._migration_issue_enabled
        self.assertFalse(enabled(repo_data))
        self.manager.conf_global["create_migration_issue"] = True
        self.assertTrue(enabled(repo_data))
        self.assertFalse(enabled(dict(repo_data, create_migration_issue=False)))
        self.manager.conf_global["create_migration_issue"] = False
        self.assertTrue(enabled(dict(repo_data, create_migration_issue=True)))

    def test_enabled_never_on_manual_or_tool_repos(self):
        self.manager.conf_global["create_migration_issue"] = True
        enabled = self.manager._migration_issue_enabled
        for repo_data in (
            {"branches": ["16.0"], "manual_branch_mgmt": True},
            {"branches": ["master"]},
            {"branches": ["main", "1.5"]},
            {"branches": []},
        ):
            self.assertFalse(enabled(repo_data), repo_data)
            self.assertFalse(
                enabled(dict(repo_data, create_migration_issue=True)), repo_data
            )

    def test_get_modules_list(self):
        gh_repo = mock.Mock()

        def directory_contents(path, ref, return_as=None):
            self.assertEqual(ref, "16.0")
            if path == "":
                return {
                    "mod_b": mock.Mock(type="dir", path="mod_b"),
                    "mod_a": mock.Mock(type="dir", path="mod_a"),
                    "setup": mock.Mock(type="dir", path="setup"),
                    "README.md": mock.Mock(type="file", path="README.md"),
                }
            return {
                "mod_a": {"__manifest__.py": 1},
                "mod_b": {"__openerp__.py": 1},
                "setup": {"mod_a": 1},
            }[path]

        gh_repo.directory_contents.side_effect = directory_contents
        self.assertEqual(
            self.manager._get_modules_list(gh_repo, "16.0"), ["mod_a", "mod_b"]
        )

    def test_create_issue(self):
        gh_repo = self._mock_repo(labels=("help wanted", "bug", "no stale"))
        with mock.patch.object(
            RepoManager, "_get_modules_list", return_value=["mod_a", "mod_b"]
        ) as get_modules:
            self.manager._create_migration_issue(gh_repo, "17.0", {"15.0", "16.0"})
        get_modules.assert_called_once_with(gh_repo, "16.0")
        gh_repo.create_milestone.assert_called_once_with("17.0")
        gh_repo.issues.assert_called_once_with(milestone=7, state="all")
        kw = gh_repo.create_issue.call_args.kwargs
        self.assertEqual(kw["title"], "Migration to version 17.0")
        self.assertEqual(kw["milestone"], 7)
        self.assertEqual(kw["labels"], ["help wanted", "no stale"])
        self.assertIn("Migration-to-version-17.0", kw["body"])
        self.assertIn("- [ ] mod_a\n- [ ] mod_b", kw["body"])

    def test_reuse_milestone_and_issue(self):
        milestone = mock.Mock(number=3)
        milestone.title = "17.0"
        issue = mock.Mock()
        issue.title = "Migration to version 17.0"
        gh_repo = self._mock_repo(issues=[issue], milestones=[milestone])
        with mock.patch.object(RepoManager, "_get_modules_list", return_value=[]):
            res = self.manager._create_migration_issue(gh_repo, "17.0", {"16.0"})
        self.assertIs(res, issue)
        gh_repo.create_milestone.assert_not_called()
        gh_repo.create_issue.assert_not_called()

    def test_skip_without_previous_branch(self):
        for version, existing in (
            ("17.0", set()),
            ("17.0", {"18.0"}),
            ("17.0", {"main", "16.5"}),
            ("main", {"16.0"}),
            ("17.5", {"16.0"}),
        ):
            gh_repo = self._mock_repo()
            with mock.patch.object(RepoManager, "_get_modules_list") as get_modules:
                self.manager._create_migration_issue(gh_repo, version, existing)
            get_modules.assert_not_called()
            gh_repo.create_issue.assert_not_called()

    def test_process_repositories_hook(self):
        gh_repo = self._named_mock("test-repo-1", default_branch="16.0")
        gh_repo.branches.return_value = [self._named_mock("15.0")]
        self.manager.gh = mock.Mock()
        self.manager.gh.repository.return_value = gh_repo
        self.manager.gh_org = mock.Mock()
        self.manager.gh_org.repositories.return_value = [
            self._named_mock("test-repo-1")
        ]
        self.manager.gh_org.team_by_name.return_value.repositories.return_value = []
        self.manager.conf_repo = {
            "test-repo-1": dict(
                self.manager.conf_repo["test-repo-1"], create_migration_issue=True
            )
        }
        calls = []

        def create_issue(gh_repo, version, existing_branches):
            # copy: the set is updated after the call
            calls.append((gh_repo, version, set(existing_branches)))

        with (
            mock.patch.object(RepoManager, "_create_branch"),
            mock.patch.object(
                RepoManager, "_create_migration_issue", side_effect=create_issue
            ),
        ):
            self.manager._process_repositories()
        self.assertEqual(calls, [(gh_repo, "16.0", {"15.0"})])
