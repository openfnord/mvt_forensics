# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
import zipfile
from pathlib import Path
from typing import List, Optional

from mvt.common.command import Command

from .modules.androidqf import ANDROIDQF_MODULES
from .modules.bugreport import BUGREPORT_MODULES
from .modules.bugreport.base import BugReportModule

log = logging.getLogger(__name__)


class CmdAndroidCheckAndroidQF(Command):
    def __init__(
        self,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        ioc_files: Optional[list] = None,
        module_name: Optional[str] = None,
        serial: Optional[str] = None,
        module_options: Optional[dict] = None,
        hashes: bool = False,
    ) -> None:
        super().__init__(
            target_path=target_path,
            results_path=results_path,
            ioc_files=ioc_files,
            module_name=module_name,
            serial=serial,
            module_options=module_options,
            hashes=hashes,
            log=log,
        )

        self.name = "check-androidqf"

        # We can load AndroidQF and bugreport modules here, as
        # AndroidQF dump will contain a bugreport.
        self.modules = ANDROIDQF_MODULES + BUGREPORT_MODULES
        # TODO: Check how to namespace and deduplicate modules.

        self.format: Optional[str] = None
        self.archive: Optional[zipfile.ZipFile] = None
        self.files: List[str] = []

    def init(self):
        if os.path.isdir(self.target_path):
            self.format = "dir"
            parent_path = Path(self.target_path).absolute().parent.as_posix()
            target_abs_path = os.path.abspath(self.target_path)
            for root, subdirs, subfiles in os.walk(target_abs_path):
                for fname in subfiles:
                    file_path = os.path.relpath(os.path.join(root, fname), parent_path)
                    self.files.append(file_path)

        elif os.path.isfile(self.target_path):
            self.format = "zip"
            self.archive = zipfile.ZipFile(self.target_path)
            self.files = self.archive.namelist()

    def load_bugreport(self):
        # Refactor this file list loading
        # First we need to find the bugreport file location
        bugreport_zip_path = None
        for file_name in self.files:
            if file_name.endswith("bugreport.zip"):
                bugreport_zip_path = file_name
                break
        else:
            self.log.warning("No bugreport.zip found in the AndroidQF dump")
            return None

        if self.format == "zip":
            # Create handle to the bugreport.zip file inside the AndroidQF dump
            handle = self.archive.open(bugreport_zip_path)
            bugreport_zip = zipfile.ZipFile(handle)
        else:
            # Load the bugreport.zip file from the extracted AndroidQF dump on disk.
            parent_path = Path(self.target_path).absolute().parent.as_posix()
            bug_report_path = os.path.join(parent_path, bugreport_zip_path)
            bugreport_zip = zipfile.ZipFile(bug_report_path)

        return bugreport_zip

    def module_init(self, module):
        if isinstance(module, BugReportModule):
            bugreport_archive = self.load_bugreport()
            if not bugreport_archive:
                return
            module.from_zip(bugreport_archive, bugreport_archive.namelist())

        if self.format == "zip":
            module.from_zip_file(self.archive, self.files)
        else:
            parent_path = Path(self.target_path).absolute().parent.as_posix()
            module.from_folder(parent_path, self.files)
