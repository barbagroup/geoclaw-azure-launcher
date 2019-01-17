#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Pi-Yueh Chuang <pychuang@gwu.edu>
#
# Distributed under terms of the MIT license.

"""
Misc. stuff
"""
import sys
import time


def reporthook(header, current, total):
    """Progress bar

    The code snippet is adapted from:
    https://blog.shichao.io/2012/10/04/progress_speed_indicator_for_urlretrieve_in_python.html
    """
    global start_time
    if current == 0:
        start_time = time.time()
        return
    duration = time.time() - start_time
    speed = int(current/(1024*duration)) # in kilo-bytes
    percent = int(current*100/total)
    print("\r"+header+"...%d%%, %d MB, %d KB/s, %d seconds passed" %
          (percent, current/1024/1024, speed, duration), end='')
    sys.stdout.flush()
