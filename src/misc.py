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

    line = header + \
        " ... {:d} MB / {:d} MB".format(
            int(current/1024/1024), int(total/1024/1024))
    print("\r"+(len(line)+10)*" ", end='')
    print("\r"+line, end='')
    sys.stdout.flush()
