#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Pi-Yueh Chuang <pychuang@gwu.edu>
#
# Distributed under terms of the MIT license.

"""
Prepare topagraphy files for each rupture points by clipping base topo.
"""
import os
import arcpy
import numpy


def prepare_topo(base, points, extent, output_dirs, ignore=False):
    """Prepare topagraphy files for each rupture points by clipping base topo."""

    output_files = []

    for i, point in enumerate(points):
        output_files.append(os.path.join(output_dirs[i], "topo.asc"))
        prepare_topo_single(base, point, extent, output_files[i], ignore)

    return output_files


def prepare_topo_single(base, point, extent, output, ignore=False):
    """Prepare the topo file for a rupture point by clipping base topo."""

    top = point[1] + extent[0] + 10
    bottom = point[1] - extent[1] - 10
    left = point[0] - extent[2] - 10
    right = point[0] + extent[3] + 10

    if os.path.isfile(output):
        if ignore:
            return
        else:
            os.remove(output)

    # clip base topo and create a new raster
    arcpy.management.Clip(
        in_raster=base,
        rectangle="{} {} {} {}".format(left, bottom, right, top),
        out_raster="temp",
        nodata_value="-9999",
        maintain_clipping_extent="NO_MAINTAIN_EXTENT")

    # output the clipped topo to case folder
    arcpy.conversion.RasterToASCII("temp", output)

    # remove the temporary raster
    arcpy.management.Delete("temp")
