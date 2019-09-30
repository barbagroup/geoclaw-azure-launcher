#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
########################################################################################################################
# Copyright © 2019 The George Washington University.
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
