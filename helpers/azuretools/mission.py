#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
########################################################################################################################
# Copyright © 2019 The George Washington University and G2 Integrated Solutions, LLC.
# All Rights Reserved.
#
# Contributors: Pi-Yueh Chuang <pychuang@gwu.edu>
#               J. Tracy Thorleifson <tracy.thorleifson@g2-is.com>
#
# Licensed under the BSD-3-Clause License (the "License").
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at: https://opensource.org/licenses/BSD-3-Clause
#
# BSD-3-Clause License:
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided
# that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the
#    following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the
#    following disclaimer in the documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or
#    promote products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
# GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
########################################################################################################################

"""
A class represeting a batch of simulations.
"""
import os
import sys
import logging
from .user_credential import UserCredential
from .mission_info import MissionInfo
from .mission_controller import MissionController
from .mission_status_reporter import MissionStatusReporter


class Mission:
    """ class represeting a batch of simulation tasks."""

    def __init__(self):
        """Default constructor."""

        self.info = None # information holder
        self.logger = None # logger

        self.credential = None # Azure credential
        self.controller = None # resource controller
        self.reporter = None # status reporter

    def __del__(self):
        """Destructor."""

        self.logger.handlers[0].close()
        self.logger.removeHandler(self.logger.handlers[0])

    def _init_logger(self, level=logging.INFO):
        """Initialize logger."""

        self.logger = logging.getLogger("AzureMission")
        self.logger.setLevel(level)

        formatter = logging.Formatter("[%(asctime)s][%(levelname)s][%(filename)s] %(message)s\n")
        fh = logging.FileHandler(os.path.join(self.info.wd, "AzureMission.log"), "w", "utf-8")
        fh.setLevel(level)
        fh.setFormatter(formatter)

        self.logger.addHandler(fh)

        self.logger.info("AzureMission logger initialization succeeded.")

    def init_info(self, mission_name="", n_nodes_max=0, wd=".", vm_type="STANDARD_H8",
             node_type="dedicated", log_level=logging.INFO, pool_image="g2integratedsolutions/landspill:g2bionic1_1"):
        """Initialize the information.

        Args:
            mission_name [in]: A str for the name of this mission.
            n_nodes_max [in]: Total number of computing nodes requested.
            wd [in]: working directory. (default: current directory)
            vm_type [in]: The type of virtual machine. (default: STANDARD_H8)
            node_type [in]: Either "dedicated" (default) or "low-priority".
            log_level [in]: Python logging level.
            6/28/2019 - G2 Integrated Solutions - JTT
            pool_image [in]: Name of the Azure pool Docker image
        """

        self.info = MissionInfo(mission_name, n_nodes_max, wd, vm_type, node_type, pool_image)
        self._init_logger(log_level)

        self.logger.info("Mission instance initialization succeeded.")

    def init_info_from_file(self, filename, log_level=logging.INFO):
        """Read a MissionInfo instance from a file.

        Args:
            filename [in]: the file where the backup file is located.
            log_level [in]: Python logging level.

        Return:
            The UTC time stamp at when the backup is done.
        """

        self.info = MissionInfo()
        self.info.read_mission_info(filename)
        self._init_logger(log_level)

        self.logger.info("Mission instance read succeeded.")

    def write_info_to_file(self):
        """Backup the MissionInfo instance to a file.

        Return:
            The UTC time stamp at when the backup is done.
        """

        self.info.write_mission_info()

        self.logger.info("Mission instance write succeeded.")

    def setup_communication(self, cred_file=None, cred_pass=None, cred=None):
        """Setup communication between local and Azure.

        Can provide either cred_file + cred_pass or cred.

        Args:
            cred_file [in]: encrypted file containing credential.
            cred_pass [in]: passcode to decrypt the file.
            cred [in]: an UserCredential instance.
        """

        if cred is None:
            assert cred_file is not None and cred_pass is not None, \
                "If cred is None, cred_file & cred_pass can not be None."

            self.credential = UserCredential()
            self.credential.read_encrypted(cred_pass, cred_file)
        else:
            assert cred_file is None and cred_pass is None, \
                "If cred is not None, cred_file & cred_pass must be None."

            self.credential = cred

        self.controller = MissionController(self.credential)
        self.reporter = MissionStatusReporter(self.credential)

        self.logger.info("Local-Azure communication setup succeeded.")

    def create_resources(self, pool=True, job=True, storage=True):
        """Create resources on Azure.

        Args:
            pool [in]: whether to create pool (default: True)
            job [in]: whether to create job (default: True)
            storage [in]: whether to create storage container (default: True)
        """

        if pool:
            self.controller.create_pool(self.info)
            self.logger.info("Pool of the mission %s created.", self.info.name)

        if job:
            self.controller.create_job(self.info)
            self.logger.info("Job of the mission %s created.", self.info.name)

        if storage:
            self.controller.create_storage_container(self.info)
            self.controller.get_storage_container_access_tokens(self.info)
            self.logger.info("Storage of the mission %s created.", self.info.name)

        self.logger.info("Resources of the mission %s created.", self.info.name)

    def clear_resources(self, pool=True, job=True, storage=True):
        """Delete resources on Azure.

        Args:
            pool [in]: whether to delete pool (default: True)
            job [in]: whether to delete job (default: True)
            storage [in]: whether to delete storage container (default: True)
        """

        if storage:
            self.controller.delete_storage_container(self.info)
            self.info.container_url = None
            self.info.container_token = None

            if os.path.isfile(self.info.backup_file):
                os.remove(self.info.backup_file)

            logging.info("Storage of the mission %s deleted.", self.info.name)

        if job:
            self.controller.delete_job(self.info)
            logging.info("Job of the mission %s deleted.", self.info.name)

        if pool:
            self.controller.delete_pool(self.info)
            logging.info("Pool of the mission %s deleted.", self.info.name)

        logging.info("Resources of the mission %s deleted.", self.info.name)

    def add_task(self, casename, casepath, ignore_exist=True):
        """Add additional task to the task scheduler."""

        self.logger.debug("Adding {}".format(casename))
        self.controller.add_task(self.info, casename, casepath, ignore_exist)
        self.logger.debug("Done adding {}".format(casename))

    def get_monitor_string(self):
        """Get a string for outputing."""

        return self.reporter.get_overview_string(self.info)

    def monitor_and_terminate(self):
        """Print status until all tasks are done and terminate mission."""
        import time
        import datetime

        keep_running = True

        while keep_running:

            print()
            print(datetime.datetime.now().replace(microsecond=0))
            print(self.get_monitor_string())

            time.sleep(30)

            _, status = self.reporter.get_job_status(self.info)
            if status["active"]+status["running"] == 0:
                keep_running = False

        print("All tasks done.")

    def download_case(
            self, casename, syncmode=True, ignore_raw_data=True, ignore_figures=True,
            ignore_rasters=True, ignore_noexist=False):
        """Download a case folder.

        Args:
            casename [in]: the case to be downloaded.
            syncmode [in]: to use sync mode or always download.
            ignore_raw_data [in]: ignore GeoClaw raw data (default: True)
            ignore_figures [in]: ignore figures (default: True)
            ignore_rasters [in]: ignore raster files (default: True)
        """

        ignore_patterns = ["__pycache__"]

        if ignore_raw_data:
            ignore_patterns += [".*?\.data", "fort\..*?"]

        if ignore_figures:
            ignore_patterns += ["_plots"]

        if ignore_rasters:
            ignore_patterns += [".*?\.asc", ".*?\.prj"]

        try:
            self.controller.download_cloud_dir(
                self.info, casename, self.info.tasks[casename]["path"], 
                syncmode, ignore_patterns)
        except KeyError:
            if ignore_noexist:
                pass
            else:
                raise

    def download_all_cases(
            self, syncmode=True, ignore_raw_data=True, ignore_figures=True,
            ignore_rasters=True):
        """Download all case folders.

        Args:
            syncmode [in]: to use sync mode or always download.
            ignore_raw_data [in]: ignore GeoClaw raw data (default: True)
            ignore_figures [in]: ignore figures (default: True)
            ignore_rasters [in]: ignore raster files (default: True)
        """

        ignore_patterns = ["__pycache__"]

        if ignore_raw_data:
            ignore_patterns += [".*?\.data", "fort\..*?"]

        if ignore_figures:
            ignore_patterns += ["_plots"]

        if ignore_rasters:
            ignore_patterns += [".*?\.asc", ".*?\.prj"]

        for casename, values in self.info.tasks.items():
            self.controller.download_cloud_dir(
                self.info, casename, values["path"], syncmode, ignore_patterns)

    def get_graphical_monitor(self, cred_file, cred_pass):
        """Get a graphical monitor."""
        import subprocess

        this_file = os.path.abspath(__file__)
        exec_file = os.path.join(os.path.dirname(this_file), "graphical_monitor.py")

        subprocess.Popen([
            "python", exec_file, self.info.name, cred_file, cred_pass])
