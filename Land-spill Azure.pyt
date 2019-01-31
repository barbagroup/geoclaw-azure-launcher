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
import os
import numpy
import helpers.arcgistools
import importlib
importlib.reload(helpers.arcgistools)


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

        # 0, basic: working directory
        working_dir = arcpy.Parameter(
            category="Basic", displayName="Working Directory", name="working_dir",
            datatype="DEWorkspace", parameterType="Required", direction="Input")

        working_dir.value = os.getcwd()

        # 1, basic: rupture point
        rupture_point = arcpy.Parameter(
            category="Basic", displayName="Rupture point", name="rupture_point",
            datatype="GPFeatureLayer", parameterType="Required", direction="Input")

        rupture_point.filter.list = ["Point"]

        # 2, basic: leak profile
        leak_profile = arcpy.Parameter(
            category="Basic", displayName="Leak profile", name="leak_profile",
            datatype="GPValueTable", parameterType="Required", direction="Input")

        leak_profile.columns = [
            ["GPDouble", "End time (sec)"], ["GPDouble", "Rate (m^3/sec)"]]
        leak_profile.value = [[1800.0, 0.5], [12600.0, 0.1]]

        # 3, basic: base topography
        topo_layer = arcpy.Parameter(
            category="Basic", displayName="Base topography", name="topo_layer",
            datatype="GPRasterLayer", parameterType="Required", direction="Input")

        # 4, basic: hydrological features
        hydro_layers = arcpy.Parameter(
            category="Basic", displayName="Hydrological features",
            name="hydro_layers", datatype="GPFeatureLayer",
            parameterType="Optional", direction="Input", multiValue=True)

        # 5, 6, basic: finest resolution
        x_res = arcpy.Parameter(
            category="Basic", displayName="X resolution (m)", name="x_res",
            datatype="GPDouble", parameterType="Required", direction="Input")

        y_res = arcpy.Parameter(
            category="Basic", displayName="Y resolution (m)", name="y_res",
            datatype="GPDouble", parameterType="Required", direction="Input")

        # 7, 8, 9, 10, basic: computational extent relative to point source
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

        params += [working_dir, rupture_point, leak_profile, topo_layer, hydro_layers,
                   x_res, y_res, dist_top, dist_bottom, dist_left, dist_right]

        # =====================================================================
        # Fluid settings section
        # =====================================================================

        # 11
        ref_viscosity = arcpy.Parameter(
            category="Fluid settings",
            displayName="Reference dynamic viscosity (cP)", name="ref_viscosity",
            datatype="GPDouble", parameterType="Required", direction="Input")
        ref_viscosity.value = 332.0

        # 12
        ref_temp = arcpy.Parameter(
            category="Fluid settings",
            displayName="Reference temperature (Celsius)", name="ref_temp",
            datatype="GPDouble", parameterType="Required", direction="Input")
        ref_temp.value = 15.0

        # 13
        temp = arcpy.Parameter(
            category="Fluid settings",
            displayName="Ambient temperature (Celsius)", name="temp",
            datatype="GPDouble", parameterType="Required", direction="Input")
        temp .value= 25.0

        # 14
        density = arcpy.Parameter(
            category="Fluid settings",
            displayName="Density (kg/m^3)", name="density",
            datatype="GPDouble", parameterType="Required", direction="Input")
        density.value= 9.266e2

        # 15
        evap_type = arcpy.Parameter(
            category="Fluid settings",
            displayName="Evaporation model", name="evap_type",
            datatype="GPString", parameterType="Required", direction="Input")
        evap_type.filter.type = "ValueList"
        evap_type.filter.list = ["None", "Fingas1996 Log Law", "Fingas1996 SQRT Law"]
        evap_type.value = "None"

        # 16
        evap_c1 = arcpy.Parameter(
            category="Fluid settings",
            displayName="Evaporation coefficients 1", name="evap_c1",
            datatype="GPDouble", parameterType="Optional", direction="Input",
            enabled=False)
        evap_c1.value = 0.0

        # 17
        evap_c2 = arcpy.Parameter(
            category="Fluid settings",
            displayName="Evaporation coefficients 2", name="evap_c2",
            datatype="GPDouble", parameterType="Optional", direction="Input",
            enabled=False)
        evap_c2.value = 0.0


        params += [ref_viscosity, ref_temp, temp, density, evap_type, evap_c1, evap_c2]

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

        azure_batch_name.value = azure_batch_key.value = azure_batch_url.value = "batch"
        azure_storage_name.value = azure_storage_key.value = "storage"


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
        if parameters[3].altered and not parameters[5].altered:
            parameters[5].value = arcpy.Describe(
                parameters[3].valueAsText).meanCellWidth

        # update the default cell y size based on x size
        if parameters[5].altered and not parameters[6].altered:
            parameters[6].value = parameters[5].value

        if parameters[15].value != "None":
            parameters[16].enabled = True
            parameters[17].enabled = True

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        importlib.reload(helpers.arcgistools)
        arcpy.env.parallelProcessingFactor="75%"

        working_dir = parameters[0].valueAsText.replace("\\", "\\\\")

        points = arcpy.da.FeatureClassToNumPyArray(
            parameters[1].valueAsText, ["SHAPE@X", "SHAPE@Y"],
            spatial_reference=arcpy.SpatialReference(3857))

        leak_profile = numpy.array(parameters[2].value, dtype=numpy.float64)

        base_topo = parameters[3].valueAsText

        hydro_layers = parameters[4].value

        resolution = numpy.array(
            [parameters[5].value, parameters[6].value], dtype=numpy.float64)

        domain = numpy.array(
            [parameters[7].value, parameters[8].value,
             parameters[9].value, parameters[10].value], dtype=numpy.float64)

        azure = numpy.array(
            [parameters[-5].value, parameters[-4].value, parameters[-3].value,
             parameters[-2].value, parameters[-1].value],
            dtype=str)

        paths = helpers.arcgistools.create_folders(working_dir, points)
        ascs = helpers.arcgistools.prepare_topo(base_topo, points, domain, paths, True)

        for i, point in enumerate(points):
            setrun = os.path.join(paths[i], "setrun.py")
            helpers.arcgistools.print_setrun(
                output=setrun,
                point=point,
                extent=domain,
                res=resolution,
                topo="topo.asc",
                ref_mu=parameters[11].value,
                ref_temp=parameters[12].value,
                amb_temp=parameters[13].value,
                density=parameters[14].value,
                NStages=leak_profile.shape[0],
                StageTimes=leak_profile[:, 0],
                StageRates=leak_profile[:, 1],
                evap_type=parameters[15].value,
                evap_coeffs=numpy.array([parameters[16].value, parameters[17].value]))

            helpers.arcgistools.print_roughness(
                os.path.join(paths[i], "roughness.txt"),
                point, domain, 0.1)

        return
