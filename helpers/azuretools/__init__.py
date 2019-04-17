#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Pi-Yueh Chuang <pychuang@gwu.edu>
#
# Distributed under terms of the BSD 3-Clause license.

"""
Utilities for launching landspill simulations on Azure Batch clusters.
"""

# auto-reloading submodules in case users reload this package
import importlib as _importlib

try:
    _importlib.reload(user_credential)
    _importlib.reload(mission_info)
    _importlib.reload(mission_controller)
    _importlib.reload(mission_monitor)
    _importlib.reload(mission)
except:
    pass

# move core classes to this level
from .user_credential import UserCredential
from .mission_info import MissionInfo
from .mission_controller import MissionController
from .mission_monitor import MissionMonitor
from .mission import Mission

# meta data
__version__ = "v1.0-alpha"
__author__ = "Pi-Yueh Chuang (pychuang@gwu.edu)"
