# Copyright 2026 Camptocamp SA
# @author: Simone Orsi
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import textwrap

from oca_repo_maintainer.tools import manifest


def test_mark_manifest_uninstallable_no_key():
    assert manifest.mark_manifest_uninstallable("{'name': 'mod1'}") == (
        "{'name': 'mod1',\n    'installable': False,\n}\n"
    )


def test_mark_manifest_uninstallable_key_exists():
    assert (
        manifest.mark_manifest_uninstallable(
            """{'name': 'mod1', "installable": True}"""
        )
        == """{'name': 'mod1', "installable": False}"""
    )


def test_mark_manifest_uninstallable_already_false():
    manifest_text = """{'name': 'mod1', "installable": False}"""
    assert manifest.mark_manifest_uninstallable(manifest_text) == manifest_text


def test_mark_manifest_uninstallable_nested_dict():
    assert (
        manifest.mark_manifest_uninstallable(
            textwrap.dedent(
                """\
            {
                'name': 'mod1',
                'external_dependencies': {
                    'python': ['some_package'],
                },
                'license': 'AGPL-3',
            }
            """
            )
        )
        == textwrap.dedent(
            """\
        {
            'name': 'mod1',
            'external_dependencies': {
                'python': ['some_package'],
            },
            'license': 'AGPL-3',
            'installable': False,
        }
        """
        )
    )


def test_mark_modules_uninstallable(tmp_path):
    (tmp_path / "mod1").mkdir()
    (tmp_path / "mod1" / "__manifest__.py").write_text("{'name': 'mod1'}")
    (tmp_path / "mod2").mkdir()
    (tmp_path / "mod2" / "__manifest__.py").write_text(
        """{'name': 'mod2', "installable": True}"""
    )
    manifest.mark_modules_uninstallable(tmp_path)
    assert (tmp_path / "mod1" / "__manifest__.py").read_text() == (
        "{'name': 'mod1',\n    'installable': False,\n}\n"
    )
    assert (tmp_path / "mod2" / "__manifest__.py").read_text() == (
        """{'name': 'mod2', "installable": False}"""
    )
