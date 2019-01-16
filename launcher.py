#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Pi-Yueh Chuang <pychuang@gwu.edu>
#
# Distributed under terms of the MIT license.

"""
Main function.
"""
from src.UserCredential import UserCredential
from src.MissionController import MissionController

if __name__ == "__main__":
    user_data = UserCredential(
        "pychuangbatch",
        "RHq7wxe6njeuxIYsyGWgCm1iRA3Z7iQrrB4sU8Y929H5VSepaY8/98ZMClv8yhdpaGvfK47lBXTyM6QFGrfDeg==",
        "https://pychuangbatch.eastus.batch.azure.com",
        "pychuangstorage",
        "I0MipM8yjVswguJ/gq5rwqm0kYnQFN/o5uG1EIh/zmsX8ZfJ92kWeKagT3ov1X4J6gIIwg3+bzjOD6MHpN9KZQ==")


    mission = MissionController(user_data, "test", 2)
