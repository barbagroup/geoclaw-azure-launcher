#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Pi-Yueh Chuang <pychuang@gwu.edu>
#
# Distributed under terms of the BSD 3-Clause license.

"""
Test the Azure mission launcher.
"""
import os
import sys
import getpass
import logging
from helpers.azuretools import UserCredential
from helpers.azuretools import Mission


if __name__ == "__main__":

    logging.basicConfig(filename="test.log", level=logging.INFO)

    passcode = getpass.getpass("Passcode to decrypt cred.dat:")

    # download required files for the test cases
    script_dir_path = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(script_dir_path, "test_cases"))

    # start the mission
    mission = Mission()

    if os.path.isfile("test_backup_file.dat"):
        mission.init_info_from_file("test_backup_file.dat")
    else:
        mission.init_info("test", 4, ".", "STANDARD_H8", node_type="dedicated")

    mission.setup_communication(os.path.join(script_dir_path, "cred.dat"), passcode)
    mission.create_resources()

    # add tasks
    mission.add_task("test_case_1", os.path.join(script_dir_path, "test_cases", "test_case_1"), True)
    mission.add_task("test_case_2", os.path.join(script_dir_path, "test_cases", "test_case_2"), True)

    # write to a backup file
    mission.write_info_to_file()

    # monitor until all finished
    mission.monitor_and_terminate()

    # download data
    mission.download_cases()

    # clear all resources
    mission.clear_resources()

    # delete the backup file
    os.remove("test_backup_file.dat")
