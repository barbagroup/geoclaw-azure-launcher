#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Pi-Yueh Chuang <pychuang@gwu.edu>
#
# Distributed under terms of the MIT license.

"""
A function to report download/upload progress.
"""
import re


def reporthook(prefix, output, current, total):
    """Progress bar for a download/upload task.

    Args:
        prefix [in]: a string that will prefix to the progress output.
        output [in]: a file object.
        current [in]: currently downloaded size (bytes).
        total [in]: total size that will be downloaded (bytes).
    """

    current = int(current/1024/1024) # MB
    total = int(total/1024/1024) # MB

    line = prefix + " ... {:d} MB / {:d} MB ({:3d} %)".format(
        current, total, int(current*100/total))
    print("\r"+(len(line)+10)*" ", end='', file=output)
    print("\r"+line, end='', file=output)
    output.flush()

def path_ignored(filepath, ignore_patterns):
    """An utility to check if the file path match any of the ignore patterns.

    The ignore patterns is a list of regular expression (Python style).

    Args:
        filepath [in]: the path of a file.
        ignore_patterns [in]: a list of regular expression strings.
    """

    assert isinstance(filepath, str), "Type error!"
    assert isinstance(ignore_patterns, list), "Type error!"

    for pattern in ignore_patterns:
        result = re.search(pattern, filepath)

        if result is not None:
            return True

    return False
