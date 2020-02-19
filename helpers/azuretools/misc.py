#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
########################################################################################################################
# Copyright © 2019-2020 Pi-Yueh Chuang and Lorena A. Barba
# All Rights Reserved.
#
# Contributors: Pi-Yueh Chuang <pychuang@gwu.edu>
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
