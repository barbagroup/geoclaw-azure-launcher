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


if __name__ == "__main__":

    passcode = getpass.getpass("Passcode to decrypt cred.dat:")

    # get the path to the repo
    test_dir = os.path.dirname(os.path.abspath(__file__))
    backup = os.path.join(test_dir, "test_backup_file.dat")
    logging.basicConfig(filename=os.path.join(test_dir, "test.log"), level=logging.INFO)

    # add repo directory to module search path and import
    sys.path.insert(0, os.path.dirname(test_dir))
    from helpers.azuretools import Mission

    # start the mission
    mission = Mission()

    if os.path.isfile(backup):
        mission.init_info_from_file(backup)
    else:
        mission.init_info("test", 4, test_dir, "STANDARD_H8", node_type="dedicated")

    mission.setup_communication(os.path.join(test_dir, "cred.dat"), passcode)
    mission.create_resources()

    # add tasks
    mission.add_task("test_case_1", os.path.join(test_dir, "test_case_1"), True)
    mission.add_task("test_case_2", os.path.join(test_dir, "test_case_2"), True)

    # write to a backup file
    mission.write_info_to_file()

    # monitor until all finished
    mission.monitor_and_terminate()

    # download data
    mission.download_cases()

    # clear all resources
    mission.clear_resources()

    # delete the backup file
    os.remove(backup)
