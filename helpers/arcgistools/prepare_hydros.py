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
Prepare hydrological feature rasters.
"""
import os
import arcpy


def prepare_single_point_hydros(in_feats, point, extent, res, out_dir, ignore=False):
    """Prepare hydro feature rasters for a single point."""

    if not os.path.isdir(out_dir):
        raise FileNotFoundError("{} does not exist.".format(out_dir))

    top = point[1] + extent[0] + 10
    bottom = point[1] - extent[1] - 10
    left = point[0] - extent[2] - 10
    right = point[0] + extent[3] + 10
    coord = [(left, bottom), (right, bottom), (right, top), (left, top)]

    result = arcpy.management.CreateFeatureclass(
        arcpy.env.workspace, "square", "POLYGON",
        spatial_reference=3857)
    clipper = result[0]

    # Write feature to new feature class
    with arcpy.da.InsertCursor(clipper, ['SHAPE@']) as cursor:
        cursor.insertRow([coord])

    out_files = []
    for i, feat in enumerate(in_feats):

        out_files.append(os.path.join(out_dir, "hydro_{}.asc".format(i)))
        if os.path.isfile(out_files[-1]):
            if ignore:
                continue
            else:
                os.remove(out_files[-1])

        arcpy.analysis.Clip(
            in_features=feat, clip_features=clipper,
            out_feature_class="hydro_feat_{}".format(i))

        arcpy.conversion.FeatureToRaster(
            "hydro_feat_{}".format(i), "FType",
            "hydro_raster_{}".format(i), res)

        arcpy.conversion.RasterToASCII(
            "hydro_raster_{}".format(i), out_files[-1])

        arcpy.management.Delete("hydro_feat_{}".format(i))
        arcpy.management.Delete("hydro_raster_{}".format(i))

    arcpy.management.Delete(clipper)

    return out_files

def prepare_hydros(in_feats, points, extent, res, out_dirs, ignore=False):
    """Prepare hydro files for each rupture points by clipping base topo."""

    outputs = []

    for i, point in enumerate(points):
        outputs.append(
            prepare_single_point_hydros(
                in_feats, point, extent, res, out_dirs[i], ignore))

    return outputs
