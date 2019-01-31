#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Pi-Yueh Chuang <pychuang@gwu.edu>
#
# Distributed under terms of the MIT license.

"""
WIP
"""

# for i, point in enumerate(points):

#     top = point[1] + domain[0] + 10
#     bottom = point[1] - domain[1] - 10
#     left = point[0] - domain[2] - 10
#     right = point[0] + domain[3] + 10

#     coord = [(left, bottom), (right, bottom), (right, top), (left, top)]

#     result = arcpy.management.CreateFeatureclass(
#         arcpy.env.workspace, "square".format(i),
#         "POLYGON", spatial_reference=3857)
#     clipper = result[0]

#     # Write feature to new feature class
#     with arcpy.da.InsertCursor(clipper, ['SHAPE@']) as cursor:
#         cursor.insertRow([coord])

#     arcpy.AddMessage(clipper)
#     for j in range(hydro_layers.rowCount):
#         indata = hydro_layers.getRow(j).replace("\\", "/")
#         arcpy.AddMessage(os.path.join(
#                 arcpy.env.workspace, "clipper{}_{}".format(i, j)))
#         arcpy.AddMessage(indata)
#         arcpy.analysis.Clip(
#             in_features=indata,
#             clip_features=clipper,
#             out_feature_class=os.path.join(
#                 arcpy.env.workspace, "clipper{}_{}".format(i, j)))

#     arcpy.management.Delete(clipper)
