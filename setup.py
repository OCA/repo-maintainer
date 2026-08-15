# Copyright 2023 Dixmit
# @author: Enric Tobella
# Copyright 2023 Camptocamp SA
# @author: Simone Orsi
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)


from setuptools import setup

install_requires = [
    "copier",
    "github3.py",
    "PyYAML",
    "click",
    "sphinx",
    "sphinx-rtd-theme",
]

tests_require = [
    "vcrpy",
]


setup(
    name="oca_repo_maintainer",
    version="0.0.1",
    description="Manage repositories and teams on Github",
    long_description="""
    Manage repos and teams via YAML configuration.
    This tool is able to:

    * create/update repositories
    * create/update teams and roles
    * create/update branches

    """,
    author="Odoo Community Association",
    url="http://github.com/OCA/repo-maintainer",
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require={"test": tests_require},
    # package_dir={"": ""},
    packages=[
        "oca_repo_maintainer",
        "oca_repo_maintainer.cli",
        "oca_repo_maintainer.tools",
    ],
    include_package_data=True,
    license="AGPL-3",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "oca-repo-manage = oca_repo_maintainer.cli.manage:manage",
            "oca-repo-add-branch = oca_repo_maintainer.cli.manage:add_branch",
            "oca-repo-set-default-branch = oca_repo_maintainer.cli.manage:set_default_branch",
            "oca-repo-pages = oca_repo_maintainer.cli.pages:pages",
        ]
    },
)
