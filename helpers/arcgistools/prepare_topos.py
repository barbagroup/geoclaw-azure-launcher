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

def prepare_topos(base, points, extent, out_dirs, ignore=False):
    """Prepare topagraphy files for each rupture points by clipping base topo."""

    outputs = []

    for i, point in enumerate(points):
        outputs.append(
            prepare_topo_single(base, point, extent, out_dirs[i], ignore))

    return outputs

def prepare_single_topo(base, point, extent, out_dir, ignore=False):
    """Prepare the topo file for a rupture point by clipping base topo."""

    top = point[1] + extent[0] + 10
    bottom = point[1] - extent[1] - 10
    left = point[0] - extent[2] - 10
    right = point[0] + extent[3] + 10

    if not os.path.isdir(out_dir):
        raise FileNotFoundError("{} does not exist.".format(out_dir))

    output = os.path.join(out_dir, "topo.asc")

    if os.path.isfile(output):
        if ignore:
            return output
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

    return output
