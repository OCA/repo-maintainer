# Copyright 2023 Dixmit
# @author: Enric Tobella
# Copyright 2023 Camptocamp SA
# @author: Simone Orsi
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import hashlib
import logging
from pathlib import Path

import yaml

_logger = logging.getLogger(__name__)


class SmartDict(dict):
    """Dotted notation dict."""

    def __getattr__(self, attrib):
        val = self.get(attrib)
        return self.__class__(val) if type(val) is dict else val


class ConfLoader:
    def __init__(self, conf_dir):
        self.conf_dir = Path(conf_dir)
        self.checksum = self._load_checksum()

    def _load_checksum(self):
        return self.load_conf("checksum", checksum=False)

    def load_conf(self, name, checksum=True, by_filepath=False):
        conf = {}
        path = self.conf_dir / name
        filepath = path.with_suffix(".yml")
        if filepath.exists():
            # direct yml files
            data = self._load_conf_from_file(filepath, checksum=checksum)
            if by_filepath:
                conf[filepath] = data
            else:
                conf.update(data)
        else:
            # folders containing ymls
            for filepath in path.rglob("*.yml"):
                data = self._load_conf_from_file(filepath, checksum=checksum)
                if by_filepath:
                    conf[filepath] = data
                else:
                    conf.update(data)
        return SmartDict(conf)

    def save_conf(self, filepath, conf):
        # TODO Use ruamel.yaml to keep the original format of the file.
        # Yet, is not critical for now, because the pre-commit conf
        # on repo-maintainer-conf will take care of it.
        # However, it would be nice to have it here too.
        with filepath.open("w") as f:
            # at least keep the quotes consistent, you silly pyyaml
            txt = yaml.dump(conf).replace(*"'", *'"')
            f.write(txt)

    def _load_conf_from_file(self, filepath, checksum=True):
        conf = {}
        with filepath.open() as fd:
            content = fd.read()
            if not content:
                return conf
            if checksum and self._file_changed(filepath, content):
                conf.update(yaml.safe_load(content))
                self._store_checksum(filepath, content)
            elif not checksum:
                conf.update(yaml.safe_load(content))
            else:
                _logger.info(
                    "%s not changed: skipping", self._filepath_for_checksum(filepath)
                )
        return conf

    def _file_changed(self, filepath, content):
        return self._make_md5(content) != self.checksum.get(
            self._filepath_for_checksum(filepath)
        )

    def _make_md5(self, content):
        return hashlib.md5(content.encode()).hexdigest()

    def save_checksum(self):
        if self.checksum:
            with open(self.conf_dir / "checksum.yml", "w") as f:
                yaml.dump(dict(self.checksum), f)

    def _store_checksum(self, filepath, content):
        self.checksum[self._filepath_for_checksum(filepath)] = self._make_md5(content)

    def _filepath_for_checksum(self, filepath):
        return filepath.relative_to(self.conf_dir).as_posix()
