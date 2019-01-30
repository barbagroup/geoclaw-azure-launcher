#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
# vim:ft=python
# vim:ff=unix
#
# Copyright © 2019 Pi-Yueh Chuang <pychuang@gwu.edu>
#
# Distributed under terms of the MIT license.

"""
ArcGIS Pro Python toolbox.
"""
import numpy


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Land-spill Azure"
        self.alias = "landspill"

        # List of tool classes associated with this toolbox
        self.tools = [LandSpillSimulationsOnAzure]


class LandSpillSimulationsOnAzure(object):
    """Run Lans-Spill Simulations on Azure

    Create simulation case folders on local machine, upload cases to Azure, run
    simulations on Azure, and then download results."
    """

    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Run Lans-Spill Simulations on Azure"
        self.description = \
            "Create simulation case folders on local machine, " + \
            "upload cases to Azure, run simulations on Azure, " + \
            "and then download results."

        self.canRunInBackground = False # no effect in ArcGIS Pro

    def getParameterInfo(self):
        """Define parameter definitions"""

        params = []

        # =====================================================================
        # Basic section
        # =====================================================================

        # basic: working directory
        working_dir = arcpy.Parameter(
            category="Basic", displayName="Working Directory", name="working_dir",
            datatype="DEWorkspace", parameterType="Required", direction="Input")

        working_dir.defaultEnvironmentName = "workspace"

        # basic: rupture point
        rupture_point = arcpy.Parameter(
            category="Basic", displayName="Rupture point", name="rupture_point",
            datatype="GPFeatureLayer", parameterType="Required", direction="Input")

        rupture_point.filter.list = ["Point"]

        # basic: leak profile
        leak_profile = arcpy.Parameter(
            category="Basic", displayName="Leak profile", name="leak_profile",
            datatype="GPValueTable", parameterType="Required", direction="Input")

        leak_profile.columns = [
            ["GPDouble", "End time (sec)"], ["GPDouble", "Rate (m^3/sec)"]]

        # basic: base topography
        topo_layer = arcpy.Parameter(
            category="Basic", displayName="Base topography", name="topo_layer",
            datatype="GPRasterLayer", parameterType="Required", direction="Input")

        # basic: finest resolution
        x_res = arcpy.Parameter(
            category="Basic", displayName="X resolution (m)", name="x_res",
            datatype="GPDouble", parameterType="Required", direction="Input")

        y_res = arcpy.Parameter(
            category="Basic", displayName="Y resolution (m)", name="y_res",
            datatype="GPDouble", parameterType="Required", direction="Input")

        # basic: computational extent relative to point source
        dist_top = arcpy.Parameter(
            category="Basic",
            displayName="Relative computational doamin: top (m)",
            name="dist_top",
            datatype="GPDouble", parameterType="Required", direction="Input")

        dist_bottom = arcpy.Parameter(
            category="Basic",
            displayName="Relative computational doamin: bottom (m)",
            name="dist_bottom",
            datatype="GPDouble", parameterType="Required", direction="Input")

        dist_left = arcpy.Parameter(
            category="Basic",
            displayName="Relative computational doamin: left (m)",
            name="dist_left",
            datatype="GPDouble", parameterType="Required", direction="Input")

        dist_right = arcpy.Parameter(
            category="Basic",
            displayName="Relative computational doamin: right (m)",
            name="dist_right",
            datatype="GPDouble", parameterType="Required", direction="Input")

        dist_top.value = dist_bottom.value = dist_left.value = dist_right.value = 1000

        params += [working_dir, rupture_point, leak_profile, topo_layer,
                   x_res, y_res, dist_top, dist_bottom, dist_left, dist_right]

        # =====================================================================
        # Fluid settings section
        # =====================================================================

        ref_viscosity = arcpy.Parameter(
            category="Fluid settings",
            displayName="Reference dynamic viscosity (cP)", name="ref_viscosity",
            datatype="GPDouble", parameterType="Required", direction="Input")

        ref_temp = arcpy.Parameter(
            category="Fluid settings",
            displayName="Reference temperature (Celsius)", name="ref_temp",
            datatype="GPDouble", parameterType="Required", direction="Input")

        temp = arcpy.Parameter(
            category="Fluid settings",
            displayName="Ambient temperature (Celsius)", name="temp",
            datatype="GPDouble", parameterType="Required", direction="Input")

        density = arcpy.Parameter(
            category="Fluid settings",
            displayName="Density (kg/m^3)", name="density",
            datatype="GPDouble", parameterType="Required", direction="Input")


        params += [ref_viscosity, ref_temp, temp, density]

        # =====================================================================
        # Azure section
        # =====================================================================

        # Azure
        azure_batch_name = arcpy.Parameter(
            category="Azure Credential",
            displayName="Azure Batch account name", name="azure_batch_name",
            datatype="GPString", parameterType="Required", direction="Input")

        azure_batch_key = arcpy.Parameter(
            category="Azure Credential",
            displayName="Azure Batch account key", name="azure_batch_key",
            datatype="GPString", parameterType="Required", direction="Input")

        azure_batch_url = arcpy.Parameter(
            category="Azure Credential",
            displayName="Azure Batch account url", name="azure_batch_url",
            datatype="GPString", parameterType="Required", direction="Input")

        azure_storage_name = arcpy.Parameter(
            category="Azure Credential",
            displayName="Azure Storage account name", name="azure_storage_name",
            datatype="GPString", parameterType="Required", direction="Input")

        azure_storage_key = arcpy.Parameter(
            category="Azure Credential",
            displayName="Azure Storage account key", name="azure_storage_key",
            datatype="GPString", parameterType="Required", direction="Input")


        params += [azure_batch_name, azure_batch_key, azure_batch_url,
                   azure_storage_name, azure_storage_key]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        # update the default cell x size based on provided base topo
        if parameters[3].altered and not parameters[4].altered:
            parameters[4].value = arcpy.Describe(
                parameters[3].valueAsText).meanCellWidth

        # update the default cell y size based on x size
        if parameters[4].altered and not parameters[5].altered:
            parameters[5].value = parameters[4].value

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        leak_profile = numpy.array(parameters[2].value, dtype=numpy.float64)
        arcpy.AddMessage(type(leak_profile))
        arcpy.AddMessage(leak_profile)

        points = arcpy.da.FeatureClassToNumPyArray(
            parameters[1].valueAsText,
            ["SHAPE@X", "SHAPE@Y"],
            spatial_reference=arcpy.SpatialReference(3857))
        arcpy.AddMessage(type(points))
        arcpy.AddMessage(points)

        resolution = numpy.array(
            [parameters[4].value, parameters[5].value], dtype=numpy.float64)
        arcpy.AddMessage(type(resolution))
        arcpy.AddMessage(resolution)

        domain = numpy.array(
            [parameters[6].value, parameters[7].value,
             parameters[8].value, parameters[9].value],
            dtype=numpy.float64)
        arcpy.AddMessage(type(domain))
        arcpy.AddMessage(domain)

        azure = numpy.array(
            [parameters[-5].value, parameters[-4].value, parameters[-3].value,
             parameters[-2].value, parameters[-1].value],
            dtype=str)
        arcpy.AddMessage(type(azure))
        arcpy.AddMessage(azure)

        return
