#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Pi-Yueh Chuang <pychuang@gwu.edu>
#
# Distributed under terms of the MIT license.

"""
Create folders for each rupture point.
"""
import os
import numpy
import arcpy


def create_folders(workdir, xy):
    """Create folders for each rupture point

    The folders created use the coordinates as the folder names. If there are
    negative numbers in the coordinates, the minus sign will be replaced with
    character N.

    Args:
        workdir [in]: str; the prefix that will be used to host folders.
        xy [in]: 2D numpy.ndarray with shape of Npt x 2, where the second
            dimension is the x, y coordinates.
    """

    # change to absolute path
    workdir = os.path.abspath(workdir)

    # create necessarry directories
    if not os.path.isdir(workdir):
        os.makedirs(workdir)

    # empty numpy ndarray to hold paths of created folders
    output = []

    # create each folder
    for i, point in enumerate(xy):
        target = "{}_{}".format(point[0], point[1])
        target = target.replace("-", "N")
        output.append(os.path.join(workdir, target))

        try:
            os.makedirs(output[i])
        except FileExistsError as err:
            pass

    return output
