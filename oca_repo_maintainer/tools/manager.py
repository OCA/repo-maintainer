# Copyright 2023 Dixmit
# @author: Enric Tobella
# Copyright 2023 Camptocamp SA
# @author: Simone Orsi
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging
import shutil
import subprocess
import sys
import tempfile
from subprocess import CalledProcessError

import copier
import github3
from github3.exceptions import NotFoundError

from .manifest import mark_modules_uninstallable
from .utils import ConfLoader

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logging.basicConfig(level=logging.INFO, handlers=[handler])

_logger = logging.getLogger(__name__)


def check_call(cmd, cwd=None, log_error=True, extra_cmd_args=False, env=None):
    if extra_cmd_args:
        cmd += extra_cmd_args
    cp = subprocess.run(
        cmd,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=cwd,
        env=env,
    )
    if cp.returncode and log_error:
        _logger.error(
            f"command {cp.args} in {cwd} failed with return code {cp.returncode} "
            f"and output:\n{cp.stdout}"
        )
    cp.check_returncode()


class RepoManager:
    """Setup and update repositories and teams."""

    def __init__(self, conf_dir, org, token, force=False):
        self.conf_dir = conf_dir
        self.conf_loader = ConfLoader(self.conf_dir)
        self.token = token
        self.org = org
        self.force = force
        self.conf_global = self.conf_loader.load_conf("global", checksum=False)
        self.conf_psc = self.conf_loader.load_conf("psc", checksum=not force)
        self.conf_repo = self.conf_loader.load_conf("repo", checksum=not force)
        self.new_repo_template = self.conf_global.get("template")

    def run(self):
        self._setup_gh()
        self._process_psc()
        self._process_repositories()
        self._save_checksum()

    def _setup_gh(self):
        self.gh = github3.login(token=self.token)
        self.gh_org = self.gh.organization(self.org)

    def _setup_user(self, clone_dir):
        """Ensure user is properly configured on current repo."""
        gh_user = self.gh.me()
        try:
            name = subprocess.check_output("git config user.name".split(" ")).strip()
        except CalledProcessError:
            name = None
        if not name:
            self._run_cmd(
                ["git", "config", "user.name", gh_user.name or gh_user.login],
                cwd=clone_dir,
            )
        try:
            email = subprocess.check_output("git config user.email".split(" ")).strip()
        except CalledProcessError:
            email = None
        if not email:
            self._run_cmd(
                ["git", "config", "user.email", gh_user.email],
                cwd=clone_dir,
            )

    def _process_psc(self):
        if not self.conf_psc:
            _logger.info("No team to process")
            return
        for team, data in self.conf_psc.items():
            _logger.info("Processing team %s" % team)
            try:
                gh_team = self.gh_org.team_by_name(team)
            except NotFoundError:
                gh_team = self.gh_org.create_team(team, privacy="closed")
            members = data.get("members", []) + self.conf_global["maintainers"]
            representatives = data.get("representatives", [])
            done_members = []
            done_representatives = []
            for member in gh_team.members(role="member"):
                if member.login not in members:
                    if member.login not in representatives:
                        _logger.info("Revoking membership for %s" % member.login)
                        gh_team.revoke_membership(member.login)
                else:
                    done_members.append(member.login)
            for member in gh_team.members(role="maintainer"):
                if member.login not in representatives:
                    if member.login not in members:
                        _logger.info("Revoking membership for %s" % member.login)
                        gh_team.revoke_membership(member.login)
                else:
                    done_representatives.append(member.login)
            for member in members:
                if member not in done_members:
                    _logger.info("Adding membership to %s" % member)
                    gh_team.add_or_update_membership(member, role="member")
            for member in representatives:
                if member not in done_representatives:
                    _logger.info("Adding membership to %s" % member)
                    gh_team.add_or_update_membership(member, role="maintainer")

    def _process_repositories(self):
        if not self.conf_repo:
            _logger.info("No repo to process")
            return
        repositories = self.gh_org.repositories()
        repo_keys = [repo.name for repo in repositories]
        gh_admin_team = self.gh_org.team_by_name(self.conf_global.get("owner"))
        gh_maintainer_teams = [
            self.gh_org.team_by_name(maintainer_team)
            for maintainer_team in self.conf_global.get("team_maintainers")
        ]
        team_repos = {}
        for repo, repo_data in self.conf_repo.items():
            if repo not in repo_keys:
                gh_repo = self.gh_org.create_repository(
                    repo, repo, team_id=gh_admin_team.id
                )
                for gh_maintainer_team in gh_maintainer_teams:
                    gh_maintainer_team.add_repository(
                        "{}/{}".format(self.org, repo), "admin"
                    )
                repo_branches = []
            else:
                gh_repo = self.gh.repository(self.org, repo)
                repo_branches = [branch.name for branch in gh_repo.branches()]
            if repo_data["psc"] not in team_repos:
                gh_team = self.gh_org.team_by_name(repo_data["psc"])
                team_repos[repo_data["psc"]] = {
                    "team": gh_team,
                    "repos": [repo.name for repo in gh_team.repositories()],
                }
            if repo not in team_repos[repo_data["psc"]]["repos"]:
                team_repos[repo_data["psc"]]["team"].add_repository(
                    "{}/{}".format(self.org, repo), "push"
                )
            for member in repo_data.get("maintainers", []):
                gh_repo.add_collaborator(member)
            existing_branches = set(repo_branches)
            for branch in sorted(repo_data.get("branches")):
                branch = str(branch)
                if branch not in existing_branches:
                    self._create_branch(gh_repo, branch, repo_data, existing_branches)
                    existing_branches.add(branch)
            branch = repo_data.get("default_branch")
            if branch and gh_repo.default_branch != branch:
                gh_repo.edit(name=gh_repo.name, default_branch=branch)

    def _create_branch(self, gh_repo, version, repo_data=None, existing_branches=None):
        clone_dir = tempfile.mkdtemp()
        try:
            self._init_branch(clone_dir, gh_repo, version, repo_data, existing_branches)
        except CalledProcessError:
            _logger.error("Something failed when the new repo was being created")
            raise
        finally:
            shutil.rmtree(clone_dir)

    def _init_branch(
        self, clone_dir, gh_repo, version, repo_data=None, existing_branches=None
    ):
        repo_data = repo_data or {}
        source_branch = None
        if repo_data.get("new_branch_not_empty"):
            source_branch = self._get_previous_branch(
                version, existing_branches or set(), gh_repo.default_branch
            )
        if source_branch:
            self._init_branch_from_previous(clone_dir, gh_repo, version, source_branch)
        else:
            self._init_branch_from_scratch(clone_dir, gh_repo, version)

    @staticmethod
    def _parse_version(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _get_previous_branch(self, version, existing_branches, default_branch=None):
        """Find the closest existing branch strictly before `version`.

        Falls back to `default_branch` when no earlier branch exists,
        as it is the best available proxy for "the previous state" of the repo.
        """
        target = self._parse_version(version)
        candidates = []
        if target is not None:
            for branch in existing_branches:
                parsed = self._parse_version(branch)
                if parsed is not None and parsed < target:
                    candidates.append((parsed, branch))
        if candidates:
            return max(candidates)[1]
        if default_branch and default_branch in existing_branches:
            return default_branch
        return None

    def _init_branch_from_previous(self, clone_dir, gh_repo, version, source_branch):
        """Create `version` off `source_branch`, keeping its content.

        All addons are marked `installable = False`, as a new Odoo version
        branch is expected to start empty from a functional standpoint,
        even though the code is not.
        """
        self._run_cmd(
            [
                "git",
                "clone",
                "--branch",
                source_branch,
                "--single-branch",
                f"https://{self.token}@github.com/{self.org}/{gh_repo.name}",
                clone_dir,
            ],
            cwd=None,
        )
        self._setup_user(clone_dir)
        self._run_cmd(
            ["git", "checkout", "-b", version],
            cwd=clone_dir,
        )
        copier.run_recopy(
            clone_dir,
            data={
                "repo_name": gh_repo.name,
                "repo_slug": gh_repo.name,
                "repo_description": gh_repo.name,
                "odoo_version": version,
            },
            defaults=True,
            overwrite=True,
            unsafe=True,
        )
        mark_modules_uninstallable(clone_dir)
        self._run_cmd(
            ["git", "add", "-A"],
            cwd=clone_dir,
        )
        self._run_cmd(
            [
                "git",
                "commit",
                "-m",
                f"[MIG] Create {version} branch from {source_branch}",
            ],
            cwd=clone_dir,
        )
        self._run_cmd(
            ["git", "push", "origin", "HEAD"],
            cwd=clone_dir,
        )

    def _init_branch_from_scratch(self, clone_dir, gh_repo, version):
        copier.run_copy(
            self.new_repo_template,
            clone_dir,
            defaults=True,
            unsafe=True,
            data={
                "repo_name": gh_repo.name,
                "repo_slug": gh_repo.name,
                "repo_description": gh_repo.name,
                "odoo_version": version,
            },
        )
        self._run_cmd(
            ["git", "init"],
            cwd=clone_dir,
        )
        self._setup_user(clone_dir)
        self._run_cmd(
            ["git", "add", "-A"],
            cwd=clone_dir,
        )
        self._run_cmd(
            ["git", "commit", "-m", "Initial commit"],
            cwd=clone_dir,
        )
        self._run_cmd(
            ["git", "checkout", "-b", version],
            cwd=clone_dir,
        )
        self._run_cmd(
            ["git", "remote", "add", "origin", gh_repo.url],
            cwd=clone_dir,
        )
        self._run_cmd(
            [
                "git",
                "remote",
                "set-url",
                "--push",
                "origin",
                f"https://{self.token}@github.com/{self.org}/{gh_repo.name}",
            ],
            cwd=clone_dir,
        )
        self._run_cmd(
            ["git", "push", "origin", "HEAD"],
            cwd=clone_dir,
        )

    def _run_cmd(self, cmd, cwd, **kw):
        check_call(cmd, cwd, **kw)

    def _save_checksum(self):
        self.conf_loader.save_checksum()
