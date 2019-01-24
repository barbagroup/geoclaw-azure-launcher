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
from helpers import UserCredential
from helpers import Mission


if __name__ == "__main__":

    user_data = UserCredential(credential_file="./credential.txt")
    mission = Mission(user_data, "test", 4, ["./test-case-1", "./test-case-2"])

    mission.start()
    mission.monitor_wait_download()
    mission.clear_resources()
