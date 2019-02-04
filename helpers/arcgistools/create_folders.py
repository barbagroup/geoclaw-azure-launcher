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
import shutil
import numpy
import arcpy


def create_single_folder(workdir, xy, ignore=True):
    """Create the case folder of a single rupture point.

    The folder created uses the coordinates as the folder names. W (West) & E
    (Ease) are used to represent the sign in x direction, and N (North) & S
    (South) are used for y direction.

    Args:
        workdir [in]: str; the prefix that will be used to host the case folder.
        xy [in]: 1D numpy.ndarray with size 2 representing x & y coordinates.
        ignore [optional]: boolean indicating whether to ignore existing folder
            or not.
    """

    # change to absolute path
    workdir = os.path.abspath(workdir)

    # use W, E, N, and S to represent x & y coordinates
    x = "{}{}".format(numpy.abs(xy[0]), "E" if xy[0]>=0 else "W")
    y = "{}{}".format(numpy.abs(xy[1]), "N" if xy[1]>=0 else "S")

    # final case folder path & name
    target = os.path.join(workdir, "{}{}".format(x, y))

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
