#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
########################################################################################################################
# Copyright © 2019-2020 Pi-Yueh Chuang, Lorena A. Barba, and G2 Integrated Solutions, LLC.
# All Rights Reserved.
#
# Contributors: Pi-Yueh Chuang <pychuang@gwu.edu>
#               J. Tracy Thorleifson <tracy.thorleifson@g2-is.com>
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
Create folders for each rupture point.
"""
import os
import shutil
import numpy
import re

def create_single_folder(workdir, xy, case_name_method="Rupture point easting and northing", ignore=True):
    """Create the case folder of a single rupture point.

    Modified to allow for field based case naming. - 2019/06/28 - G2 Integrated Solutions, LLC - JTT

    The folder created uses the coordinates as the folder names by default. W (West) & E
    (Ease) are used to represent the sign in x direction, and N (North) & S
    (South) are used for y direction.

    If the user specifies field-based case naming, the folder created uses the case field value
    for the point as the folder name.

    Args:
        workdir [in]: str; the prefix that will be used to host the case folder.
        xy [in]: 1D numpy.ndarray with size 2 representing x & y coordinates (default),
            or size 3, representing x & y coordinates & case name field value (field-based case name).
        case_name_method [in]: Valid values are "Rupture point easting and northing" (default) or
            "Rupture point field value" (for field-based case naming).
        ignore [optional]: boolean indicating whether to ignore existing folder
            or not.
    """

    # change to absolute path
    workdir = os.path.abspath(workdir)

    # use W, E, N, and S to represent x & y coordinates
    x = "{}{}".format(numpy.abs(xy[0]), "E" if xy[0]>=0 else "W")
    y = "{}{}".format(numpy.abs(xy[1]), "N" if xy[1]>=0 else "S")
    case_name = ""
    if case_name_method == "Rupture point field value":
        case_name = re.sub("[^a-zA-Z0-9]", "_", xy[2])

    # Azure task does not accept .(a dot) in task names, so replace with _
    x = x.replace(".", "_")
    y = y.replace(".", "_")

    # final case folder path & name
    if case_name_method == "Rupture point easting and northing":
        target = os.path.join(workdir, "{}{}".format(x, y))
    else:  # case_name_method == "Rupture point field value"
        target = os.path.join(workdir, case_name)

    # check if the case folder already exists
    if os.path.isdir(target):
        if ignore:
            return target
        else:
            shutil.rmtree(target)

    # create folder
    os.makedirs(target)

    return target

def create_folders(workdir, xy, ignore=True):
    """Create the case folders for multiple rupture points.

    The folders created use the coordinates as the folder names.  W (West) & E
    (Ease) are used to represent the sign in x direction, and N (North) & S
    (South) are used for y direction.

    Args:
        workdir [in]: str; the prefix that will be used to host the case folders.
        xy [in]: 2D numpy.ndarray with shape of Npt x 2, where the second
            dimension is the x, y coordinates.
        ignore [optional]: boolean indicating whether to ignore existing folders
            or not.
    """

    # change to absolute path
    workdir = os.path.abspath(workdir)

    # empty numpy ndarray to hold paths of created folders
    output = []

    # create each folder
    for i, point in enumerate(xy):
        output.append(create_single_folder(workdir, point, ignore))

    return output
