#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Pi-Yueh Chuang <pychuang@gwu.edu>
#
# Distributed under terms of the MIT license.

"""
Test the Azure mission launcher.
"""
import os
import sys
from helpers.azuretools import UserCredential
from helpers.azuretools import Mission


if __name__ == "__main__":

    # download required files for the test cases
    script_dir_path = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(script_dir_path, "test_cases"))

    from download_data import download_all

    download_all()

    # start the mission
    user_data = UserCredential(
        credential_file=os.path.join(script_dir_path, "credential.txt"))

    mission = Mission(
        user_data, "test", 4,
        [os.path.join(script_dir_path, "test_cases/test_case_1"),
         os.path.join(script_dir_path, "test_cases/test_case_2")])

    mission.start()
    mission.monitor_wait_download()
    mission.clear_resources()
