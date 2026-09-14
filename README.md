
[![Runboat](https://img.shields.io/badge/runboat-Try%20me-875A7B.png)](https://runboat.odoo-community.org/builds?repo=OCA/repo-maintainer&target_branch=16.0)
[![Pre-commit Status](https://github.com/OCA/repo-maintainer/actions/workflows/pre-commit.yml/badge.svg?branch=16.0)](https://github.com/OCA/repo-maintainer/actions/workflows/pre-commit.yml?query=branch%3A16.0)
[![Build Status](https://github.com/OCA/repo-maintainer/actions/workflows/test.yml/badge.svg?branch=16.0)](https://github.com/OCA/repo-maintainer/actions/workflows/test.yml?query=branch%3A16.0)
[![codecov](https://codecov.io/gh/OCA/repo-maintainer/branch/16.0/graph/badge.svg)](https://codecov.io/gh/OCA/repo-maintainer)
[![Translation Status](https://translation.odoo-community.org/widgets/repo-maintainer-16-0/-/svg-badge.svg)](https://translation.odoo-community.org/engage/repo-maintainer-16-0/?utm_source=widget)

<!-- /!\ do not modify above this line -->

# Repo maintainer

This tool allows to manage repositories and teams via via YAML configuration.
Features:

* create/update repositories
* create/update teams and roles
* create/update branches
* add new branches to existing YAML conf


## Available tools

* ``oca-repo-manage`` used to automatically maintain repositories based on YAML conf (see OCA conf below)
* ``oca-repo-pages`` used to automatically generate repo inventory docs from the same YAML conf
* ``oca-repo-add-branch`` used to manually add new branches to existing conf
* ``oca-repo-set-default-branch`` used to manually set an existing branch as the default one

See [CLI reference](#cli-reference) below for the full list of options of each command.

## I can use it on my own organization?

Yes, you can. You just add the repo on your organization, add a secret called ORG_TOKEN on you secrets and modify the secrets with your information.

## OCA configuration

https://github.com/OCA/repo-maintainer-conf


## Bootstrap

You can use the script `scripts/bootstrap_data.py` to generate the conf out of existing repos. Run it with `--help` to see the options.

# Usage

## Manage repos

This action is normally performed via GH actions in the conf repo. You should not run it manually.

Yet, here's the command:


    oca-repo-manage --org $GITHUB_REPOSITORY_OWNER --token ${{secrets.GIT_PUSH_TOKEN}} --conf-dir ./conf

## Generate docs

This action is normally performed via GH actions in the conf repo. You should not run it manually.

Yet, here's the command:

    oca-repo-pages --org $GITHUB_REPOSITORY_OWNER --conf-dir conf --path docsource

## Add new branches to all repos

This action has to be performed manually when you need a new branch to be added to all repos in your conf.
Eg: when a new Odoo version is released.

Go to the conf repo on your file system and run this:

    oca-repo-add-branch --conf-dir ./conf/ --branch 18.0

Review, stage all the changes, commit and open a PR.

You can prevent this tool to edit a repo by adding ``manual_branch_mgmt`` boolean flag to repo's conf.

By default, when `oca-repo-manage` creates a new branch on GitHub it starts from an empty repo
(only the project template is applied). You can add the ``new_branch_not_empty`` boolean flag
to a repo's conf to make new branches start from the content of the closest existing branch
with a lower version instead (falling back to the repo's default branch if none is found).
In that case, the project template is re-applied for the new Odoo version and all addons are
marked as ``installable = False``, so maintainers can port them one by one.

## Set the default branch on all repos

This action has to be performed manually when you need to switch the default branch on all (or some) repos in your conf.
Eg: when a new Odoo version becomes the stable one.

Go to the conf repo on your file system and run this:

    oca-repo-set-default-branch --conf-dir ./conf/ --branch 18.0

Review, stage all the changes, commit and open a PR.

Unlike ``oca-repo-add-branch``, this command always forces ``branch`` as the default
(adding it to the repo's ``branches`` list if it's not there yet), regardless of whether
``default_branch`` was already set in the conf.

You can prevent this tool from editing a repo by adding the ``manual_branch_mgmt`` boolean
flag to the repo's conf, and repos whose current default branch is ``master`` or ``main``
are always left untouched (they are assumed to be tool repos with a single working branch).

## CLI reference

### oca-repo-manage

Setup and update repositories and teams based on the YAML conf.

| Option | Required | Default | Description |
| --- | --- | --- | --- |
| ``--conf-dir`` | yes | - | Folder where configuration is stored |
| ``--token`` | yes | env var ``GITHUB_TOKEN`` | Github token used to talk to the API |
| ``--org`` | no | ``OCA`` | The Github organization to operate on |

```
oca-repo-manage --conf-dir ./conf --org OCA --token $GITHUB_TOKEN
```

### oca-repo-pages

Generate the repo inventory docs from the YAML conf.

| Option | Required | Default | Description |
| --- | --- | --- | --- |
| ``--conf-dir`` | yes | - | Folder where configuration is stored |
| ``--path`` | yes | - | Folder where the generated pages must be written |
| ``--org`` | no | ``OCA`` | The Github organization to operate on |

```
oca-repo-pages --conf-dir ./conf --path docsource --org OCA
```

### oca-repo-add-branch

Add a new branch to all repositories in the conf (optionally setting it as default).

| Option | Required | Default | Description |
| --- | --- | --- | --- |
| ``--conf-dir`` | yes | - | Folder where configuration is stored |
| ``--branch`` | yes | - | New branch name to add |
| ``--default`` / ``--no-default`` | no | ``--default`` | Also set the new branch as the repo's default branch |
| ``--repo-whitelist`` | no | - | CSV list of repo names to update; if omitted, all repos are updated |

```
oca-repo-add-branch --conf-dir ./conf --branch 18.0 --no-default --repo-whitelist repo-a,repo-b
```

A repo is skipped when it has ``manual_branch_mgmt: true`` in its conf, or when it already
has ``master``/``main`` among its branches or as its default branch.

### oca-repo-set-default-branch

Force an existing (or new) branch as the default branch on all or given repositories.

| Option | Required | Default | Description |
| --- | --- | --- | --- |
| ``--conf-dir`` | yes | - | Folder where configuration is stored |
| ``--branch`` | yes | - | Branch name to set as default |
| ``--repo-whitelist`` | no | - | CSV list of repo names to update; if omitted, all repos are updated |

```
oca-repo-set-default-branch --conf-dir ./conf --branch 18.0 --repo-whitelist repo-a,repo-b
```

A repo is skipped when it has ``manual_branch_mgmt: true`` in its conf, or when its current
default branch is ``master``/``main``.

## Licenses

This repository is licensed under [AGPL-3.0](LICENSE).

----
OCA, or the [Odoo Community Association](http://odoo-community.org/), is a nonprofit
organization whose mission is to support the collaborative development of Odoo features
and promote its widespread use.
