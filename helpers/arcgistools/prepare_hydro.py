#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Pi-Yueh Chuang <pychuang@gwu.edu>
#
# Distributed under terms of the MIT license.

"""
Prepare hydrological feature rasters.
"""
import os
import arcpy


def prepare_hydro_single_point(in_feats, point, extent, res, out_dir, ignore=False):
    """Prepare hydro feature rasters for a single point."""

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
        
        arcpy.conversion.RasterToASCII("hydro_raster_{}".format(i), out_files[-1])
        
        arcpy.management.Delete("hydro_feat_{}".format(i))
        arcpy.management.Delete("hydro_raster_{}".format(i))

    arcpy.management.Delete(clipper)
    
    return out_files

def prepare_hydro(in_feats, points, extent, res, output_dirs, ignore=False):
    """Prepare hydro files for each rupture points by clipping base topo."""

    n_feats = in_feats.rowCount
    feats = [in_feats.getRow(i).strip("' ") for i in range(n_feats)]

    output_files = []

    for i, point in enumerate(points):
        temp = prepare_hydro_single_point(feats, point, extent, res, output_dirs[i], ignore)
        output_files.append(temp)

    return output_files
