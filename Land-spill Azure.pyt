#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
# vim:ft=python
# vim:ff=unix
########################################################################################################################
# Copyright © 2019-2020 Pi-Yueh Chuang, Lorena A. Barba, and G2 Integrated Solutions, LLC.
# All Rights Reserved.
#
# Contributors: Pi-Yueh Chuang <pychuang@gwu.edu>
#               J. Tracy Thorleifson <tracy.thorleifson@g2-is.com>
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
ArcGIS Pro Python toolbox.
"""
import os
import sys
import importlib
import logging
import arcpy
import numpy
import helpers.arcgistools
import helpers.azuretools
import datetime
import re
import json
import requests
importlib.reload(helpers.azuretools)
logging.basicConfig(filename=os.devnull)


class Toolbox(object):
    """Definition of the toolbox."""

    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""

        self.label = "Land-spill Azure"
        self.alias = "landspill"

        # List of tool classes associated with this toolbox
        self.tools = [PrepareGeoClawCases, CreateAzureCredentialFile,
                      RunCasesOnAzure, DownloadCasesFromAzure,
                      DeleteAzureResources, MonitorAzureResources]

class PrepareGeoClawCases(object):
    """Prepare case folders, configurations, and input files for GeoClaw."""

    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Create GeoClaw Cases"
        self.description = \
            "Prepare case folders, configurations, and input files for GeoClaw."

        self.canRunInBackground = False # no effect in ArcGIS Pro

    def getParameterInfo(self):
        """Define parameter definitions"""

        params = []

        # =====================================================================
        # Basic section
        # =====================================================================

        # 0, basic: working directory
        working_dir = arcpy.Parameter(
            category="Basic", displayName="Working directory", name="working_dir",
            datatype="DEWorkspace", parameterType="Required", direction="Input")

        working_dir.value = arcpy.env.scratchFolder

        # 1, basic: rupture point
        rupture_point = arcpy.Parameter(
            category="Basic", displayName="Rupture point layer", name="rupture_point",
            datatype="GPFeatureLayer", parameterType="Required", direction="Input")

        rupture_point.filter.list = ["Point"]

        # 2, basic: leak profile
        leak_profile = arcpy.Parameter(
            category="Basic", displayName="Leak profile", name="leak_profile",
            datatype="GPValueTable", parameterType="Required", direction="Input")

        leak_profile.columns = [
            ["GPDouble", "End time (sec)"], ["GPDouble", "Rate (m^3/sec)"]]
        leak_profile.value = [[1800.0, 0.5], [12600.0, 0.1]]

        # 3, simulation time
        sim_time = arcpy.Parameter(
            category="Basic", displayName="Simulation time (minutes)", name="sim_time",
            datatype="GPLong", parameterType="Required", direction="Input")

        sim_time.value = 480

        # 4, output time
        output_time = arcpy.Parameter(
            category="Basic", displayName="Output result every how many minutes",
            name="output_time", datatype="GPLong", parameterType="Required",
            direction="Input")

        output_time.value = 2

        # 5, how will the topo file be provided
        topo_type = arcpy.Parameter(
            category="Basic",
            displayName="Topography file type", name="topo_type",
            datatype="GPString", parameterType="Required", direction="Input")
        topo_type.filter.type = "ValueList"
        topo_type.filter.list = ["Get from 3DEP map server", "Local raster layer"]
        topo_type.value = "Get from 3DEP map server"

        # 6, basic: base topography
        topo_layer = arcpy.Parameter(
            category="Basic", displayName="Base topography", name="topo_layer",
            datatype="GPRasterLayer", parameterType="Optional",
            direction="Input", enabled=False)

        # 7, how will the hydro files be provided
        hydro_type = arcpy.Parameter(
            category="Basic",
            displayName="Hydrological file type", name="hydro_type",
            datatype="GPString", parameterType="Required", direction="Input")
        hydro_type.filter.type = "ValueList"
        hydro_type.filter.list = ["Get from NHD feature server", "Local feature layers"]
        hydro_type.value = "Get from NHD feature server"

        # 8, basic: hydrological features
        hydro_layers = arcpy.Parameter(
            category="Basic", displayName="Hydrological features",
            name="hydro_layers", datatype="GPFeatureLayer",
            parameterType="Optional", direction="Input", multiValue=True,
            enabled=False)

        # 9, auto-adjust resolution based on input topo raster (for future enhancement; not currently used)
        auto_res = arcpy.Parameter(
            category="Basic",
            displayName="Use the cell size in the topography raster file as " +
                        "the finest computational grid resolution",
            name="auto_res",
            datatype="GPBoolean", parameterType="Required", direction="Input",
            enabled=False)
        auto_res.value = False

        # 10, 11, basic: finest resolution
        x_res = arcpy.Parameter(
            category="Basic", displayName="X resolution (m)", name="x_res",
            datatype="GPDouble", parameterType="Required", direction="Input",
            enabled=True)

        y_res = arcpy.Parameter(
            category="Basic", displayName="Y resolution (m)", name="y_res",
            datatype="GPDouble", parameterType="Required", direction="Input",
            enabled=True)

        x_res.value = y_res.value = 1.0

        # 12, 13, 14, 15, basic: computational extent relative to point source
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

        # Parameters 16 - 20 added for NetCDF CF compliance, and to facilitate more flexible case naming.
        # 2019/06/28 - G2 Integrated Solutions - JTT
        # 16, basic: Choose whether to apply a datetime stamp to NetCDF output
        apply_datetime_stamp = arcpy.Parameter(
            category="Basic",
            displayName="Apply a datetime stamp to the NetCDF simulation output",
            name="apply_datetime_stamp",
            datatype="GPBoolean", parameterType="Optional", direction="Input")
        apply_datetime_stamp.value = False

        # 17, basic: Simulation datetime stamp
        simulation_datetime = arcpy.Parameter(
            category="Basic",
            displayName="Simulation datetime stamp", name="simulation_datetime",
            datatype="GPDate", parameterType="Optional", direction="Input",
            enabled=False)
        simulation_datetime.value = datetime.datetime.now()

        # 18, basic: Simulation datetime stamp NetCDF CF calendar enumeration
        calendar_type = arcpy.Parameter(
            category="Basic",
            displayName="NetCDF CF calendar type", name="calendar_type",
            datatype="GPString", parameterType="Optional", direction="Input")
        calendar_type.filter.type = "ValueList"
        calendar_type.filter.list = ["Standard", "Proleptic Gregorian", "No Leap", "All Leap", "360 Day", "Julian", "None"]
        calendar_type.value = "Standard"

        # 19, basic: Case naming method
        case_name_method = arcpy.Parameter(
            category="Basic",
            displayName="Case naming method", name="case_name_method",
            datatype="GPString", parameterType="Optional", direction="Input")
        case_name_method.filter.type = "ValueList"
        case_name_method.filter.list = ["Rupture point easting and northing", "Rupture point field value"]
        case_name_method.value = "Rupture point easting and northing"

        # 20, basic: Case name field
        case_name_field = arcpy.Parameter(
            category="Basic",
            displayName="Case name field", name="case_name_field",
            datatype="Field", parameterType="Optional", direction="Input",
            enabled=False)
        case_name_field.filter.list = ['Text']
        case_name_field.parameterDependencies = [rupture_point.name]

        params += [working_dir, rupture_point, leak_profile,
                   sim_time, output_time,
                   topo_type, topo_layer, hydro_type, hydro_layers,
                   auto_res, x_res, y_res,
                   dist_top, dist_bottom, dist_left, dist_right,
                   apply_datetime_stamp, simulation_datetime, calendar_type,
                   case_name_method, case_name_field]

        # =====================================================================
        # Fluid settings section
        # =====================================================================

        # 21
        ref_viscosity = arcpy.Parameter(
            category="Fluid settings",
            displayName="Reference dynamic viscosity (cP)", name="ref_viscosity",
            datatype="GPDouble", parameterType="Required", direction="Input")
        ref_viscosity.value = 332.0

        # 22
        ref_temp = arcpy.Parameter(
            category="Fluid settings",
            displayName="Reference temperature (Celsius)", name="ref_temp",
            datatype="GPDouble", parameterType="Required", direction="Input")
        ref_temp.value = 15.0

        # 23
        temp = arcpy.Parameter(
            category="Fluid settings",
            displayName="Ambient temperature (Celsius)", name="temp",
            datatype="GPDouble", parameterType="Required", direction="Input")
        temp.value= 25.0

        # 24
        density = arcpy.Parameter(
            category="Fluid settings",
            displayName="Density (kg/m^3)", name="density",
            datatype="GPDouble", parameterType="Required", direction="Input")
        density.value= 9.266e2

        # 25
        evap_type = arcpy.Parameter(
            category="Fluid settings",
            displayName="Evaporation model", name="evap_type",
            datatype="GPString", parameterType="Required", direction="Input")
        evap_type.filter.type = "ValueList"
        evap_type.filter.list = ["None", "Fingas1996 Log Law", "Fingas1996 SQRT Law"]
        evap_type.value = "Fingas1996 Log Law"

        # 26
        evap_c1 = arcpy.Parameter(
            category="Fluid settings",
            displayName="Evaporation coefficients 1", name="evap_c1",
            datatype="GPDouble", parameterType="Optional", direction="Input")
        evap_c1.value = 1.38

        # 27
        evap_c2 = arcpy.Parameter(
            category="Fluid settings",
            displayName="Evaporation coefficients 2", name="evap_c2",
            datatype="GPDouble", parameterType="Optional", direction="Input")
        evap_c2.value = 0.045


        params += [ref_viscosity, ref_temp, temp, density, evap_type, evap_c1, evap_c2]

        # =====================================================================
        # Darcy-Weisbach section
        # =====================================================================

        # 28
        friction_type = arcpy.Parameter(
            category="Darcy-Weisbach friction settings",
            displayName="Darcy-Weisbach model", name="friction_type",
            datatype="GPString", parameterType="Required", direction="Input")
        friction_type.filter.type = "ValueList"
        friction_type.filter.list = ["None", "Three-regime model"]
        friction_type.value = "Three-regime model"

        # 29
        roughness =  arcpy.Parameter(
            category="Darcy-Weisbach friction settings",
            displayName="Surface roughness", name="roughness",
            datatype="GPDouble", parameterType="Optional", direction="Input")
        roughness.value = 0.1

        params += [friction_type, roughness]

        # =====================================================================
        # Misc
        # =====================================================================

        # 30
        ignore = arcpy.Parameter(
            category="Misc",
            displayName="Skip setup if a case folder already exists",
            name="ignore",
            datatype="GPBoolean", parameterType="Required", direction="Input")
        ignore.value = True

        params += [ignore]

        # =====================================================================
        # Advanced numerical parameters
        # =====================================================================

        # 31
        dt_init = arcpy.Parameter(
            category="Advanced numerical parameters",
            displayName="Initial time-step size (second). Use 0 for auto-setting.",
            name="dt_init",
            datatype="GPDouble", parameterType="Required", direction="Input")
        dt_init.value = 0

        # 32
        dt_max = arcpy.Parameter(
            category="Advanced numerical parameters",
            displayName="Maximum time-step size (second)",
            name="dt_max",
            datatype="GPDouble", parameterType="Required", direction="Input")
        dt_max.value = 4.0

        # 33
        cfl_desired = arcpy.Parameter(
            category="Advanced numerical parameters",
            displayName="Desired CFL number",
            name="cfl_desired",
            datatype="GPDouble", parameterType="Required", direction="Input")
        cfl_desired.value = 0.9

        # 34
        cfl_max = arcpy.Parameter(
            category="Advanced numerical parameters",
            displayName="Maximum allowed CFL number",
            name="cfl_max",
            datatype="GPDouble", parameterType="Required", direction="Input")
        cfl_max.value = 0.95

        # 35
        amr_max = arcpy.Parameter(
            category="Advanced numerical parameters",
            displayName="Total AMR levels",
            name="amr_max",
            datatype="GPLong", parameterType="Required", direction="Input")
        amr_max.filter.type = "ValueList"
        amr_max.filter.list = list(range(1, 11))
        amr_max.value = 2

        # 36
        refinement_ratio = arcpy.Parameter(
            category="Advanced numerical parameters",
            displayName="AMR refinement ratio",
            name="refinement_ratio",
            datatype="GPLong", parameterType="Required", direction="Input")
        refinement_ratio.value = 4

        params += [dt_init, dt_max, cfl_desired, cfl_max, amr_max, refinement_ratio]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        # if using local raster layer
        parameters[6].enabled = (parameters[5].value == "Local raster layer")

        # if using local feature layers
        parameters[8].enabled = (parameters[7].value == "Local feature layers")

        # option for auto setting of resolution
        if parameters[6].enabled:
            parameters[9].enabled = True
        else:
            parameters[9].enabled = False
            parameters[9].value = False

        # x and y resolution
        parameters[10].enabled = not parameters[9].value
        parameters[11].enabled = not parameters[9].value

        # NetCDF CF compliance parameters - 2019/06/28 - G2 Integrated Solutions, LLC - JTT
        if parameters[16].value:
            if parameters[17].value is None:
                parameters[17].value = value = datetime.datetime.today()
            parameters[17].enabled = True
            if parameters[18].value is None:
                parameters[18].value = "Standard"
            parameters[18].enabled = True
        else:
            parameters[17].enabled = False
            parameters[17].value = None
            parameters[18].enabled = False
            parameters[18].value = None

        # If using field-based case naming - 2019/06/28 - G2 Integrated Solutions, LLC - JTT
        # (Bear in mind the user can type in *anything* in both the rupture point layer and dependent field parameters,
        # so validation must be *thorough*.)
        if parameters[19].value == "Rupture point field value":
            if parameters[1].value is None:                                     # If the rupture point layer is blank,
                parameters[20].value = None                                     # unset the dependent field parameter.
            elif not arcpy.Exists(parameters[1].value):                         # If the layer is nonsense (does not exist),
                parameters[20].value = None                                     # unset the dependent field parameter.
            elif not arcpy.Describe(parameters[1].value).shapeType == "Point":  # If not a *point* layer,
                parameters[20].value = None                                     # unset the dependent field parameter.
            elif parameters[20].value is None:                                  # It's a point layer; if the field is unset,
                string_field_names = [fld.name for fld in
                                      arcpy.Describe(parameters[1].value).fields
                                      if fld.type == "String"]
                if string_field_names:                                          # and if there is at least one string field,
                    parameters[20].value = string_field_names[0]                # set the field to the first string field,
                else:
                    parameters[20].value = None                                 # else, unset the dependent field parameter.
            elif not parameters[20].value is None:                              # It's a point layer; the field *is* set,
                string_field_names = [fld.name for fld in
                                      arcpy.Describe(parameters[1].value).fields
                                      if fld.type == "String"]
                if string_field_names:                                          # and if there is at least one string field,
                    if not parameters[20].value in string_field_names:          # check if the field is in the fields list;
                        parameters[20].value = string_field_names[0]            # if not, reset to to first string field,
                    else:
                        parameters[20].value = None                             # else, unset the dependent field parameter.
        else:  # parameters[19].value == "Rupture point easting and northing"
            parameters[20].value = None

        parameters[20].enabled = (parameters[19].value == "Rupture point field value")

        # Evaporation Fingas coefficient
        parameters[26].enabled = not parameters[25].value == "None"
        parameters[27].enabled = not parameters[25].value == "None"

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        if parameters[6].enabled and parameters[6].value is None:
            parameters[6].setErrorMessage("Require a topography raster layer")

        if parameters[31].value < 0:
            parameters[31].setErrorMessage("Time-step can not be negative")

        if parameters[32].value <= 0:
            parameters[32].setErrorMessage("Time-step can not be zero or negative")

        if parameters[33].value <= 0:
            parameters[33].setErrorMessage("CFL can not be zero or negative")

        if parameters[34].value <= 0:
            parameters[34].setErrorMessage("CFL can not be zero or negative")

        if parameters[33].value > 1.0:
            parameters[33].setErrorMessage("CFL can not exceed 1.0")

        if parameters[34].value > 1.0:
            parameters[34].setErrorMessage("CFL can not exceed 1.0")

        if parameters[36].value < 2:
            parameters[36].setErrorMessage("Refinement ratio can not be less than 2")

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        importlib.reload(helpers.arcgistools)
        arcpy.env.parallelProcessingFactor="75%"

        # 0:, path of the working directory
        working_dir = parameters[0].valueAsText.replace("\\", "\\\\")

        # 1: xy coordinates of rupture locations (Npoints x 2 if no case name field, else Npoints x 3)
        rupture_point_layer = parameters[1].valueAsText
        rupture_point_path = arcpy.Describe(parameters[1].valueAsText).catalogPath
        if parameters[19].value == "Rupture point easting and northing":
            points = arcpy.da.FeatureClassToNumPyArray(
                rupture_point_layer, ["SHAPE@X", "SHAPE@Y"],
                spatial_reference=arcpy.SpatialReference(3857))
        else:
            points = arcpy.da.FeatureClassToNumPyArray(
                rupture_point_layer, ["SHAPE@X", "SHAPE@Y", str(parameters[20].value)],
                spatial_reference=arcpy.SpatialReference(3857))

        # 2: profile of leak rate (Nstages x 2)
        leak_profile = numpy.array(parameters[2].value, dtype=numpy.float64)

        # 3, 4: output control
        sim_time = parameters[3].value
        output_time = parameters[4].value

        # 5, 6: base topography file
        if parameters[5].value == "Local raster layer":
            base_topo = parameters[6].valueAsText
        else:
            base_topo = None

        # 7, 8: hydrological feature layers (1D array with size Nfeatures)
        if parameters[7].value == "Local feature layers":
            if parameters[8].value is None:
                hydro_layers = []
            else:
                hydro_layers = \
                    [parameters[8].value.getRow(i).strip("' ")
                     for i in range(parameters[8].value.rowCount)]

        # 9, 10, 11: finest resolution in x & y direction
        if parameters[9].value: # auto-setting
            resolution = numpy.ones(2, dtype=numpy.float64) * \
                arcpy.Describe(base_topo).meanCellWidth
        else:
            resolution = numpy.array(
                [parameters[10].value, parameters[11].value], dtype=numpy.float64)

        # 12-15: computational domain extent (relative to rupture points)
        domain = numpy.array(
            [parameters[12].value, parameters[13].value,
             parameters[14].value, parameters[15].value], dtype=numpy.float64)

        # Parameters 16 - 20 added for NetCDF CF compliance, and to facilitate more flexible case naming.
        # 2019/06/28 - G2 Integrated Solutions - JTT
        apply_datetime_stamp = parameters[16].value
        datetime_stamp = parameters[17].value
        calendar_type = parameters[18].value
        case_name_method = parameters[19].value  # Either "Rupture point easting and northing"
                                                 # or "Rupture point field value"
        case_field_name = parameters[20].value

        # 21-27: fluid properties
        ref_mu=parameters[21].value
        ref_temp=parameters[22].value
        amb_temp=parameters[23].value
        density=parameters[24].value
        evap_type=parameters[25].value
        evap_coeffs=numpy.array([parameters[26].value, parameters[27].value])

        # 28, 29: friction
        friction_type = parameters[28].value
        roughness = parameters[29].value

        # 30: misc
        ignore = parameters[30].value

        # 31-36: advanced numerical parameters
        dt_init = parameters[31].value
        dt_max = parameters[32].value
        cfl_desired = parameters[33].value
        cfl_max = parameters[34].value
        amr_max = parameters[35].value
        refinement_ratio = parameters[36].value

        # Loop through each point to create each case and submit to Azure
        for i, point in enumerate(points):

            # Adjust message text based on case naming method - 2019/06/28 - G2 Integrated Solutions - JTT
            if case_name_method == "Rupture point easting and northing":
                point_msg_txt = "point {}".format(point)
            else:  # case_name_method == "Rupture point field value"
                point_msg_txt = "point {}={}".format(case_field_name, point[2])

            # create case folder
            arcpy.AddMessage("Creating case folder for " + point_msg_txt)
            case_path = helpers.arcgistools.create_single_folder(
                working_dir, point, case_name_method, ignore)

            # create topography ASCII file
            if base_topo is not None:
                arcpy.AddMessage("Creating topo input for " + point_msg_txt)
                topo = helpers.arcgistools.prepare_single_topo(
                    base_topo, point, domain, case_path, ignore)

            # create ASCII rasters for hydrological files
            # TO DO: Enhance to use Landscape Layers NHD tile feature layer when available from Esri
            if parameters[7].value == "Local feature layers":
                arcpy.AddMessage("Creating hydro input for " + point_msg_txt)
                hydros = helpers.arcgistools.prepare_single_point_hydros(
                    hydro_layers, point, domain, min(resolution), case_path, ignore)
            else:
                hydros = ["hydro_0.asc"]

            # create setrun.py, roughness, and case settings files
            # Modified to write case setting file in addition to setrun and roughness files.
            # 6/28/2019 - G2 Integrated Solutions - JTT
            aprx_file = arcpy.mp.ArcGISProject("CURRENT").filePath
            arcpy.AddMessage("Creating GeoClaw config for " + point_msg_txt)
            setrun, (roughness_file, case_settings_file) = helpers.arcgistools.write_setrun(
                aprx_file=aprx_file, out_dir=case_path, rupture_point_layer=rupture_point_layer,
                rupture_point_path=rupture_point_path,
                point=point, extent=domain, res=resolution,
                end_time=sim_time, output_time=output_time,
                ref_mu=ref_mu, ref_temp=ref_temp, amb_temp=amb_temp,
                density=density, leak_profile=leak_profile,
                evap_type=evap_type, evap_coeffs=evap_coeffs,
                n_hydros = len(hydros),
                friction_type=friction_type, roughness=roughness,
                dt_init=dt_init, dt_max=dt_max,
                cfl_desired=cfl_desired, cfl_max=cfl_max,
                amr_max=amr_max, refinement_ratio=refinement_ratio,
                apply_datetime_stamp=apply_datetime_stamp,
                datetime_stamp=datetime_stamp, calendar_type=calendar_type,
                case_name_method=case_name_method, case_field_name=case_field_name)

            arcpy.AddMessage("Done preparing " + point_msg_txt)

        return

class CreateAzureCredentialFile(object):
    """Create an encrpyted Azure credential file."""

    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Create Encrypted Azure Credential File"
        self.description = "Create an encrpyted Azure credential file."
        self.canRunInBackground = False # no effect in ArcGIS Pro

    def getParameterInfo(self):
        """Define parameter definitions"""

        # 0, working directory
        working_dir = arcpy.Parameter(
            displayName="Working directory", name="working_dir",
            datatype="DEWorkspace", parameterType="Required", direction="Input")

        working_dir.value = arcpy.env.scratchFolder

        # 1, output file name
        output_file = arcpy.Parameter(
            displayName="Output credential file name", name="output_file",
            datatype="GPString", parameterType="Required", direction="Input")

        output_file.value = "azure_cred.bin"

        # 2: Batch account name
        azure_batch_name = arcpy.Parameter(
            displayName="Azure Batch account name", name="azure_batch_name",
            datatype="GPString", parameterType="Required", direction="Input")

        # 3: Batch account key
        azure_batch_key = arcpy.Parameter(
            displayName="Azure Batch account key", name="azure_batch_key",
            datatype="GPString", parameterType="Required", direction="Input")

        # 4: Batch account URL
        azure_batch_URL = arcpy.Parameter(
            displayName="Azure Batch account URL", name="azure_batch_URL",
            datatype="GPString", parameterType="Required", direction="Input")

        # 5: Storage account name
        azure_storage_name = arcpy.Parameter(
            displayName="Azure Storage account name", name="azure_storage_name",
            datatype="GPString", parameterType="Required", direction="Input")

        # 6: Storage account key
        azure_storage_key = arcpy.Parameter(
            displayName="Azure Storage account key", name="azure_storage_key",
            datatype="GPString", parameterType="Required", direction="Input")

        # 7: Encryption passcode
        passcode = arcpy.Parameter(
            displayName="Passcode", name="passcode",
            datatype="GPStringHidden", parameterType="Required", direction="Input")

        # 8: Encryption passcode confirm
        confirm_passcode = arcpy.Parameter(
            displayName="Confirm passcode", name="confirm_passcode",
            datatype="GPStringHidden", parameterType="Required", direction="Input")

        params = [working_dir, output_file,
                  azure_batch_name, azure_batch_key, azure_batch_URL,
                  azure_storage_name, azure_storage_key,
                  passcode, confirm_passcode]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        if parameters[7].value != parameters[8].value:
            parameters[8].setErrorMessage("Passcode does not match.")

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        # path of the working directory
        working_dir = parameters[0].valueAsText.replace("\\", "\\\\")

        # output file name
        output = parameters[1].value

        # azure credential
        credential = helpers.azuretools.UserCredential(
            parameters[2].value, parameters[3].value, parameters[4].value,
            parameters[5].value, parameters[6].value)

        # passcode
        passcode = parameters[7].value

        # write the file
        credential.write_encrypted(passcode, os.path.join(working_dir, output))

        return

class RunCasesOnAzure(object):
    """Submit and run cases on Azure."""

    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Run Cases on Azure"
        self.description =  "Submit and run cases on Azure."
        self.canRunInBackground = False # no effect in ArcGIS Pro

    def getParameterInfo(self):
        """Define parameter definitions"""

        params = []

        # 0: working directory
        working_dir = arcpy.Parameter(
            displayName="Working directory", name="working_dir",
            datatype="DEWorkspace", parameterType="Required", direction="Input")

        working_dir.value = arcpy.env.scratchFolder

        # 1: rupture point
        rupture_point = arcpy.Parameter(
            displayName="Rupture point layer", name="rupture_point",
            datatype="GPFeatureLayer", parameterType="Required", direction="Input")

        rupture_point.filter.list = ["Point"]

        # Parameters 2 and 3 added to facilitate more flexible case naming.
        # 2019/06/28 - G2 Integrated Solutions - JTT
        # 2: Case naming method
        case_name_method = arcpy.Parameter(
            displayName="Case naming method", name="case_name_method",
            datatype="GPString", parameterType="Optional", direction="Input")
        case_name_method.filter.type = "ValueList"
        case_name_method.filter.list = ["Rupture point easting and northing", "Rupture point field value"]
        case_name_method.value = "Rupture point easting and northing"

        # 3: Case name field
        case_name_field = arcpy.Parameter(
            displayName="Case name field", name="case_name_field",
            datatype="Field", parameterType="Optional", direction="Input",
            enabled=False)
        case_name_field.filter.list = ['Text']
        case_name_field.parameterDependencies = [rupture_point.name]

        # 4: maximum number of computing nodes
        max_nodes = arcpy.Parameter(
            displayName="Maximum number of computing nodes", name="max_nodes",
            datatype="GPLong", parameterType="Required", direction="Input")

        max_nodes.value = 2

        # 5: vm type
        vm_type = arcpy.Parameter(
            displayName="Computing node type", name="vm_type",
            datatype="GPString", parameterType="Required", direction="Input")

        vm_type.filter.type = "ValueList"
        vm_type.filter.list = ["STANDARD_A1_V2", "STANDARD_H8", "STANDARD_H16"]
        vm_type.value = "STANDARD_H8"

        # 6: credential type
        cred_type = arcpy.Parameter(
            displayName="Azure credential", name="cred_type",
            datatype="GPString", parameterType="Required", direction="Input")

        cred_type.filter.type = "ValueList"
        cred_type.filter.list = ["Encrypted file", "Manual input"]
        cred_type.value = "Encrypted file"

        # 7: encrypted credential file
        cred_file = arcpy.Parameter(
            displayName="Encrypted credential file", name="cred_file",
            datatype="DEFile", parameterType="Optional", direction="Input",
            enabled=True)

        cred_file.value = os.path.join(arcpy.env.scratchFolder, "azure_cred.bin")

        # 8: passcode
        passcode = arcpy.Parameter(
            displayName="Passcode for the credential file", name="passcode",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=True)

        # 9: Batch account name
        azure_batch_name = arcpy.Parameter(
            displayName="Azure Batch account name", name="azure_batch_name",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 10: Batch account key
        azure_batch_key = arcpy.Parameter(
            displayName="Azure Batch account key", name="azure_batch_key",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 11: Batch account URL
        azure_batch_URL = arcpy.Parameter(
            displayName="Azure Batch account URL", name="azure_batch_URL",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 12: Storage account name
        azure_storage_name = arcpy.Parameter(
            displayName="Azure Storage account name", name="azure_storage_name",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 13: Storage account key
        azure_storage_key = arcpy.Parameter(
            displayName="Azure Storage account key", name="azure_storage_key",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 14: Azure pool Docker image
        # 6/28/2019 - G2 Integrated Solutions - JTT - Added to facilitate the use of different Docker images on Azure.
        azure_pool_docker_image = arcpy.Parameter(
            displayName="Azure pool Docker image", name="azure_pool_docker_image",
            datatype="GPString", parameterType="Required",
            direction="Input", enabled=True)

        azure_pool_docker_image.value = "g2integratedsolutions/landspill:g2bionic1_1"

        params += [working_dir, rupture_point,
                   case_name_method, case_name_field,
                   max_nodes, vm_type,
                   cred_type, cred_file, passcode,
                   azure_batch_name, azure_batch_key, azure_batch_URL,
                   azure_storage_name, azure_storage_key, azure_pool_docker_image]

        # =====================================================================
        # Misc
        # =====================================================================

        # 15: Skip a case if its case folder doesn't exist locally
        ignore_local_nonexist = arcpy.Parameter(
            displayName="Skip submitting/running a case if its case folder " + \
                        "doesn't exist on local machine",
            name="ignore_local_nonexist",
            datatype="GPBoolean", parameterType="Required", direction="Input")
        ignore_local_nonexist.value = False

        # 16: Skip a case if its case folder already exist on Azure
        ignore_azure_exist = arcpy.Parameter(
            displayName="Do not re-submit a case if it already " + \
                        "exists on Azure",
            name="ignore_azure_exist",
            datatype="GPBoolean", parameterType="Required", direction="Input")
        ignore_azure_exist.value = True

        params += [ignore_local_nonexist, ignore_azure_exist]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        # If using field-based case naming - 2019/06/28 - G2 Integrated Solutions, LLC - JTT
        # (Bear in mind the user can type in *anything* in both the rupture point layer and dependent field parameters,
        # so validation must be *thorough*.)
        if parameters[2].value == "Rupture point field value":
            if parameters[1].value is None:                                     # If the rupture point layer is blank,
                parameters[3].value = None                                      # unset the dependent field parameter.
            elif not arcpy.Exists(parameters[1].value):                         # If the layer is nonsense (does not exist),
                parameters[3].value = None                                      # unset the dependent field parameter.
            elif not arcpy.Describe(parameters[1].value).shapeType == "Point":  # If not a *point* layer,
                parameters[3].value = None                                      # unset the dependent field parameter.
            elif parameters[3].value is None:                                   # It's a point layer; if the field is unset,
                string_field_names = [fld.name for fld in
                                      arcpy.Describe(parameters[1].value).fields
                                      if fld.type == "String"]
                if string_field_names:                                          # and if there is at least one string field,
                    parameters[3].value = string_field_names[0]                 # set the field to the first string field,
                else:
                    parameters[3].value = None                                  # else, unset the dependent field parameter.
            elif not parameters[3].value is None:                               # It's a point layer; the field *is* set,
                string_field_names = [fld.name for fld in
                                      arcpy.Describe(parameters[1].value).fields
                                      if fld.type == "String"]
                if string_field_names:                                          # and if there is at least one string field,
                    if not parameters[3].value in string_field_names:           # check if the field is in the fields list;
                        parameters[3].value = string_field_names[0]             # if not, reset to to first string field,
                    else:
                        parameters[3].value = None                              # else, unset the dependent field parameter.
        else:  # parameters[2].value == "Rupture point easting and northing"
            parameters[3].value = None

        parameters[3].enabled = (parameters[2].value == "Rupture point field value")

        parameters[7].enabled = (parameters[6].value == "Encrypted file")
        parameters[8].enabled = (parameters[6].value == "Encrypted file")

        if parameters[7].enabled:
            if parameters[7] is None:
                parameters[7].value = os.path.join(arcpy.env.scratchFolder, "azure_cred.bin")
        else:
            parameters[7].value = None

        for i in range(9, 14):
            parameters[i].enabled = (not parameters[7].enabled)

        if parameters[14].value is None:
            parameters[14].value = "g2integratedsolutions/landspill:g2bionic1_1"

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        if parameters[6].value == "Encrypted file":
            if parameters[7].value is None:
                parameters[7].setErrorMessage("A credential file is required.")

            if parameters[8].value is None:
                parameters[8].setErrorMessage("A passcode is required.")
        else:
            for i in range(9, 13):
                if parameters[i].value is None:
                    parameters[i].setErrorMessage("Cannot be empty.")

        # Check to make sure the specified Docker image is valid.
        # 2019/06/28 - G2 Integrated Solutions, LLC - JTT

        if len(parameters[14].value.split(":")) != 2:
            parameters[14].setErrorMessage("Invalid Docker image name. Image name must be of the form: "
                                           "<organization>/<repository>:<tag>")
        else:  # Docker image form appears valid.
            try:
                repo = parameters[14].value.split(":")[0]
                image_tag = parameters[14].value.split(":")[1]
                docker_url = "https://registry.hub.docker.com/v2/repositories/{}/tags/?page=1".format(repo)
                request = requests.get(docker_url)  # If there's a connectivity issue, the request will fail with a
                                                    # ConnectionError.
                if request.status_code == 200:  # The Docker repository is found. Yay!
                    result = json.loads(request.text)
                    image_tags = []
                    for i in range(len(result["results"])):
                        image_tags.append(result["results"][i]["name"])

                    if not image_tag in image_tags:  # The repository is valid, but the image tag is not found.
                        parameters[14].setErrorMessage("The specified image tag was not found in the specified "
                                                       "repository. Please specify an image tag that exists in "
                                                       "the specified repository.")

                else:  # The specified repository is not found
                    parameters[14].setErrorMessage("The specified Docker organization/repository combination "
                                                   "was not found on Docker Hub. Please specify a publicly available "
                                                   "Docker organization/repository combination that exists on "
                                                   "Docker Hub.")

            except requests.exceptions.ConnectionError:  # connection failed; assume no internet connectivity
                parameters[14].setErrorMessage("Unable to connect to Docker Hub. There appears to be a problem with "
                                               "internet connectivity. Please close the tool, check "
                                               "internet connectivity, and try again.")

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        # path of the working directory
        working_dir = parameters[0].valueAsText.replace("\\", "\\\\")

        # 1: xy coordinates of rupture locations (Npoints x 2 if no case name field, else Npoints x 3)
        if parameters[2].value == "Rupture point easting and northing":
            points = arcpy.da.FeatureClassToNumPyArray(
                parameters[1].valueAsText, ["SHAPE@X", "SHAPE@Y"],
                spatial_reference=arcpy.SpatialReference(3857))
        else:  # Case field is specified; add values for case field (parameter 3) to the points numpy array
            points = arcpy.da.FeatureClassToNumPyArray(
                parameters[1].valueAsText, ["SHAPE@X", "SHAPE@Y", str(parameters[3].value)],
                spatial_reference=arcpy.SpatialReference(3857))

        # Parameter 2 (and 3) added to facilitate more flexible case naming.
        # 2019/06/28 - G2 Integrated Solutions - JTT
        case_name_method = parameters[2].value  # Either "Rupture point easting and northing"
                                                # or "Rupture point field value"

        # azure credential
        max_nodes = parameters[4].value
        vm_type = parameters[5].value

        # azure pool docker image
        # 2019/06/28 - G2 Integrated Solutions - JTT
        azure_pool_docker_image = parameters[14].value

        # skip a case if its case folder doesn't exist locally
        ignore_local_nonexist = parameters[15].value

        # skip a case if its case folder already exist on Azure
        ignore_azure_exist = parameters[16].value

        # Azure credential
        if parameters[6].value == "Encrypted file":
            credential = helpers.azuretools.UserCredential()
            credential.read_encrypted(
                parameters[8].valueAsText, parameters[7].valueAsText)
        else:
            credential = helpers.azuretools.UserCredential(
                parameters[9].value, parameters[10].value, parameters[11].value,
                parameters[12].value, parameters[13].value)

        # initialize an Azure mission
        mission = helpers.azuretools.Mission()

        backup = os.path.join(working_dir, "landspill-azure_backup_file.dat")
        if os.path.isfile(backup):
            mission.init_info_from_file(backup)
        else:
            mission.init_info("landspill-azure", max_nodes, working_dir,
                vm_type, node_type="dedicated", pool_image=azure_pool_docker_image)

        mission.setup_communication(cred=credential)
        try:
            mission.create_resources()
        except ValueError:
            arcpy.AddError("{}: {}".format(sys.exc_info()[0], sys.exc_info()[1]))
        finally:
            if sys.exc_info()[0] is not None:
                arcpy.AddError("{}: {}: {}".format(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]))
            return

        # loop through each point to add case to Azure task scheduler
        for i, point in enumerate(points):
            if case_name_method == "Rupture point easting and northing":
                x = "{}{}".format(numpy.abs(point[0]), "E" if point[0] >= 0 else "W")
                y = "{}{}".format(numpy.abs(point[1]), "N" if point[1] >= 0 else "S")
                x = x.replace(".", "_")
                y = y.replace(".", "_")
                casename = "{}{}".format(x, y)
            else:  # case_name_method == "Rupture point field value"
                casename = re.sub("[^a-zA-Z0-9]", "_", point[2])

            casedir = os.path.join(working_dir, casename)

            if not os.path.isdir(casedir):
                if ignore_local_nonexist:
                    continue
                else:
                    raise FileNotFoundError("Can not find case folder {}".format(casedir))

            arcpy.AddMessage("Adding case {}".format(casename))
            mission.add_task(casename, casedir, ignore_azure_exist)
            arcpy.AddMessage("Done adding case {}".format(casename))

        # write a backup file to local machine
        mission.write_info_to_file()

        return

class DownloadCasesFromAzure(object):
    """Download cases on Azure."""

    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Download Cases from Azure"
        self.description =  "Download cases from Azure."
        self.canRunInBackground = False # no effect in ArcGIS Pro

    def getParameterInfo(self):
        """Define parameter definitions"""

        params = []

        # 0: working directory
        working_dir = arcpy.Parameter(
            displayName="Working directory", name="working_dir",
            datatype="DEWorkspace", parameterType="Required", direction="Input")

        working_dir.value = arcpy.env.scratchFolder

        # 1: rupture point
        rupture_point = arcpy.Parameter(
            displayName="Rupture point layer", name="rupture_point",
            datatype="GPFeatureLayer", parameterType="Required", direction="Input")

        rupture_point.filter.list = ["Point"]

        # Parameters 2 and 3 added to facilitate more flexible case naming.
        # 2019/06/28 - G2 Integrated Solutions - JTT
        # 2: Case naming method
        case_name_method = arcpy.Parameter(
            displayName="Case naming method", name="case_name_method",
            datatype="GPString", parameterType="Optional", direction="Input")
        case_name_method.filter.type = "ValueList"
        case_name_method.filter.list = ["Rupture point easting and northing", "Rupture point field value"]
        case_name_method.value = "Rupture point easting and northing"

        # 3: Case name field
        case_name_field = arcpy.Parameter(
            displayName="Case name field", name="case_name_field",
            datatype="Field", parameterType="Optional", direction="Input",
            enabled=False)
        case_name_field.filter.list = ['Text']
        case_name_field.parameterDependencies = [rupture_point.name]

        # 4: credential type
        cred_type = arcpy.Parameter(
            displayName="Azure credential", name="cred_type",
            datatype="GPString", parameterType="Required", direction="Input")

        cred_type.filter.type = "ValueList"
        cred_type.filter.list = ["Encrypted file", "Manual input"]
        cred_type.value = "Encrypted file"

        # 5: encrypted credential file
        cred_file = arcpy.Parameter(
            displayName="Encrypted credential file", name="cred_file",
            datatype="DEFile", parameterType="Optional", direction="Input",
            enabled=True)

        cred_file.value = os.path.join(arcpy.env.scratchFolder, "azure_cred.bin")

        # 6: passcode
        passcode = arcpy.Parameter(
            displayName="Passcode for the credential file", name="passcode",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=True)

        # 7: Batch account name
        azure_batch_name = arcpy.Parameter(
            displayName="Azure Batch account name", name="azure_batch_name",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 8: Batch account key
        azure_batch_key = arcpy.Parameter(
            displayName="Azure Batch account key", name="azure_batch_key",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 9: Batch account URL
        azure_batch_URL = arcpy.Parameter(
            displayName="Azure Batch account URL", name="azure_batch_URL",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 10: Storage account name
        azure_storage_name = arcpy.Parameter(
            displayName="Azure Storage account name", name="azure_storage_name",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 11: Storage account key
        azure_storage_key = arcpy.Parameter(
            displayName="Azure Storage account key", name="azure_storage_key",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        params += [working_dir, rupture_point,
                   case_name_method, case_name_field,
                   cred_type, cred_file, passcode,
                   azure_batch_name, azure_batch_key, azure_batch_URL,
                   azure_storage_name, azure_storage_key]

        # =====================================================================
        # Misc
        # =====================================================================

        # 12: Skip a case if its case folder already exist on Azure
        sync_mode = arcpy.Parameter(
            displayName="Use synchronization mode",
            name="sync_mode",
            datatype="GPBoolean", parameterType="Required", direction="Input")
        sync_mode.value = True

        # 13: whether to ignore raw GeoClaw result data
        ignore_raw = arcpy.Parameter(
            displayName="Whether to ignore GeoClaw raw data",
            name="ignore_raw",
            datatype="GPBoolean", parameterType="Required", direction="Input")
        ignore_raw.value = True

        # 14: whether to ignore topography & hydro rasters
        ignore_asc = arcpy.Parameter(
            displayName=\
                "Whether to ignore topography and hydrological rasters used by GeoClaw",
            name="ignore_asc",
            datatype="GPBoolean", parameterType="Required", direction="Input")
        ignore_asc.value = True

        # 15: if case not in the record, raise an error or ignore error
        ignore_noexist = arcpy.Parameter(
            displayName=\
                "Ignore if a case is not found in the record",
            name="ignore_noexist",
            datatype="GPBoolean", parameterType="Required", direction="Input")
        ignore_noexist.value = False

        params += [sync_mode, ignore_raw, ignore_asc, ignore_noexist]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        # If using field-based case naming - 2019/06/28 - G2 Integrated Solutions, LLC - JTT
        # (Bear in mind the user can type in *anything* in both the rupture point layer and dependent field parameters,
        # so validation must be *thorough*.)
        if parameters[2].value == "Rupture point field value":
            if parameters[1].value is None:                                     # If the rupture point layer is blank,
                parameters[3].value = None                                      # unset the dependent field parameter.
            elif not arcpy.Exists(parameters[1].value):                         # If the layer is nonsense (does not exist),
                parameters[3].value = None                                      # unset the dependent field parameter.
            elif not arcpy.Describe(parameters[1].value).shapeType == "Point":  # If not a *point* layer,
                parameters[3].value = None                                      # unset the dependent field parameter.
            elif parameters[3].value is None:                                   # It's a point layer; if the field is unset,
                string_field_names = [fld.name for fld in
                                      arcpy.Describe(parameters[1].value).fields
                                      if fld.type == "String"]
                if string_field_names:                                          # and if there is at least one string field,
                    parameters[3].value = string_field_names[0]                 # set the field to the first string field,
                else:
                    parameters[3].value = None                                  # else, unset the dependent field parameter.
            elif not parameters[3].value is None:                               # It's a point layer; the field *is* set,
                string_field_names = [fld.name for fld in
                                      arcpy.Describe(parameters[1].value).fields
                                      if fld.type == "String"]
                if string_field_names:                                          # and if there is at least one string field,
                    if not parameters[3].value in string_field_names:           # check if the field is in the fields list;
                        parameters[3].value = string_field_names[0]             # if not, reset to to first string field,
                    else:
                        parameters[3].value = None                              # else, unset the dependent field parameter.
        else:  # parameters[2].value == "Rupture point easting and northing"
            parameters[3].value = None

        parameters[3].enabled = (parameters[2].value == "Rupture point field value")

        parameters[5].enabled = (parameters[4].value == "Encrypted file")
        parameters[6].enabled = (parameters[4].value == "Encrypted file")

        if parameters[5].enabled:
            parameters[5].value = os.path.join(arcpy.env.scratchFolder, "azure_cred.bin")
        else:
            parameters[5].value = None

        for i in range(7, 12):
            parameters[i].enabled = (not parameters[5].enabled)

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        if parameters[4].value == "Encrypted file":
            if parameters[5].value is None:
                parameters[5].setErrorMessage("Require a credential file.")

            if parameters[6].value is None:
                parameters[6].setErrorMessage("Require passcode.")
        else:
            for i in range(7, 12):
                if parameters[i].value is None:
                    parameters[i].setErrorMessage("Cannot be empty.")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        # path of the working directory
        working_dir = parameters[0].valueAsText.replace("\\", "\\\\")

        # xy coordinates of rupture locations (Npoints x 2 if no case name field, else Npoints x 3)
        if parameters[2].value == "Rupture point easting and northing":
            points = arcpy.da.FeatureClassToNumPyArray(
                parameters[1].valueAsText, ["SHAPE@X", "SHAPE@Y"],
                spatial_reference=arcpy.SpatialReference(3857))
        else:  # Case field is specified; add values for case field (parameter 3) to the points numpy array
            points = arcpy.da.FeatureClassToNumPyArray(
                parameters[1].valueAsText, ["SHAPE@X", "SHAPE@Y", str(parameters[3].value)],
                spatial_reference=arcpy.SpatialReference(3857))

        # Parameter 2 (and 3) added to facilitate more flexible case naming.
        # 2019/06/28 - G2 Integrated Solutions - JTT
        case_name_method = parameters[2].value  # Either "Rupture point easting and northing"
                                                # or "Rupture point field value"

        # skip if a case is already downloaded
        sync_mode = parameters[12].value

        # whether to ignore raw data
        ignore_raw = parameters[13].value

        # whether to ignore topography & hydrologic rasters used by GeoClaw
        ignore_raster = parameters[14].value

        # if a case not found in the record, whether to ignore the error
        ignore_nonexist = parameters[15].value

        # Azure credential
        if parameters[4].value == "Encrypted file":
            credential = helpers.azuretools.UserCredential()
            credential.read_encrypted(
                parameters[6].valueAsText, parameters[5].valueAsText)
        else:
            credential = helpers.azuretools.UserCredential(
                parameters[7].value, parameters[8].value, parameters[9].value,
                parameters[10].value, parameters[11].value)

        # initialize an Azure mission
        mission = helpers.azuretools.Mission()

        backup = os.path.join(working_dir, "landspill-azure_backup_file.dat")
        if os.path.isfile(backup):
            mission.init_info_from_file(backup)
        else:
            max_nodes = 0
            vm_type = "STANDARD_H8"
            node_type = "dedicated"
            mission.init_info("landspill-azure", max_nodes, working_dir,
                vm_type, node_type)

        mission.setup_communication(cred=credential)

        # loop through each point to add case to Azure task scheduler
        for i, point in enumerate(points):

            if case_name_method == "Rupture point easting and northing":
                x = "{}{}".format(numpy.abs(point[0]), "E" if point[0] >= 0 else "W")
                y = "{}{}".format(numpy.abs(point[1]), "N" if point[1] >= 0 else "S")
                x = x.replace(".", "_")
                y = y.replace(".", "_")
                case = "{}{}".format(x, y)
            else:  # case_name_method == "Rupture point field value"
                case = re.sub("[^a-zA-Z0-9]", "_", point[2])

            arcpy.AddMessage("Downloading case {}".format(case))
            mission.download_case(case, sync_mode, ignore_raw, True,
                ignore_raster, ignore_nonexist)
            arcpy.AddMessage("Done downloading case {}".format(case))

        return

class DeleteAzureResources(object):
    """Delete resources on Azure."""

    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Delete Azure Resources"
        self.description =  "Delete resources on Azure."
        self.canRunInBackground = False # no effect in ArcGIS Pro

    def getParameterInfo(self):
        """Define parameter definitions"""

        params = []

        # 0, basic: working directory
        working_dir = arcpy.Parameter(
            displayName="Working directory", name="working_dir",
            datatype="DEWorkspace", parameterType="Required", direction="Input")
        working_dir.value = arcpy.env.scratchFolder

        # 1: Delete Batch pool, i.e., cluster
        delete_pool = arcpy.Parameter(
            displayName="Delete pool (cluster)",
            name="delete_pool",
            datatype="GPBoolean", parameterType="Required", direction="Input")
        delete_pool.value = True

        # 2: Delete Batch job, i.e., task scheduler
        delete_job = arcpy.Parameter(
            displayName="Delete job (task scheduler)",
            name="delete_job",
            datatype="GPBoolean", parameterType="Required", direction="Input")
        delete_job.value = True

        # 3: Delete Storage container
        delete_container = arcpy.Parameter(
            displayName="Delete storage container",
            name="delete_container",
            datatype="GPBoolean", parameterType="Required", direction="Input")
        delete_container.value = False

        params += [working_dir, delete_pool, delete_job, delete_container]


        # 4: credential type
        cred_type = arcpy.Parameter(
            displayName="Azure credential", name="cred_type",
            datatype="GPString", parameterType="Required", direction="Input")

        cred_type.filter.type = "ValueList"
        cred_type.filter.list = ["Encrypted file", "Manual input"]
        cred_type.value = "Encrypted file"

        # 5: encrypted credential file
        cred_file = arcpy.Parameter(
            displayName="Encrypted credential file", name="cred_file",
            datatype="DEFile", parameterType="Optional", direction="Input",
            enabled=True)

        cred_file.value = os.path.join(arcpy.env.scratchFolder, "azure_cred.bin")

        # 6: passcode
        passcode = arcpy.Parameter(
            displayName="Passcode for the credential file", name="passcode",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=True)

        # 7: Batch account name
        azure_batch_name = arcpy.Parameter(
            displayName="Azure Batch account name", name="azure_batch_name",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 8: Batch account key
        azure_batch_key = arcpy.Parameter(
            displayName="Azure Batch account key", name="azure_batch_key",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 9: Batch account URL
        azure_batch_URL = arcpy.Parameter(
            displayName="Azure Batch account URL", name="azure_batch_URL",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 10: Storage account name
        azure_storage_name = arcpy.Parameter(
            displayName="Azure Storage account name", name="azure_storage_name",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 11: Storage account key
        azure_storage_key = arcpy.Parameter(
            displayName="Azure Storage account key", name="azure_storage_key",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        params += [cred_type, cred_file, passcode,
                   azure_batch_name, azure_batch_key, azure_batch_URL,
                   azure_storage_name, azure_storage_key]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        parameters[5].enabled = (parameters[4].value == "Encrypted file")
        parameters[6].enabled = (parameters[4].value == "Encrypted file")

        if parameters[5].enabled:
            parameters[5].value = os.path.join(arcpy.env.scratchFolder, "azure_cred.bin")
        else:
            parameters[5].value = None

        for i in range(7, 12):
            parameters[i].enabled = (not parameters[4].enabled)

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        if parameters[4].value == "Encrypted file":
            if parameters[5].value is None:
                parameters[5].setErrorMessage("Require a credential file.")

            if parameters[6].value is None:
                parameters[6].setErrorMessage("Require passcode.")
        else:
            for i in range(7, 12):
                if parameters[i].value is None:
                    parameters[i].setErrorMessage("Cannot be empty.")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        # path of the working directory
        working_dir = parameters[0].valueAsText.replace("\\", "\\\\")

        # whether to delete the pool
        delete_pool = parameters[1].value

        # whether to delete the job
        delete_job = parameters[2].value

        # whether to delete storage container
        delete_container = parameters[3].value

        # Azure credential
        if parameters[4].value == "Encrypted file":
            credential = helpers.azuretools.UserCredential()
            credential.read_encrypted(
                parameters[6].valueAsText, parameters[5].valueAsText)
        else:
            credential = helpers.azuretools.UserCredential(
                parameters[7].value, parameters[8].value, parameters[9].value,
                parameters[10].value, parameters[11].value)

        # initialize an Azure mission
        mission = helpers.azuretools.Mission()

        backup = os.path.join(working_dir, "landspill-azure_backup_file.dat")
        if os.path.isfile(backup):
            mission.init_info_from_file(backup)
        else:
            mission.init_info("landspill-azure", wd=working_dir)

        mission.setup_communication(cred=credential)

        # clear resources
        mission.clear_resources(delete_pool, delete_job, delete_container)

        return

class MonitorAzureResources(object):
    """Monitor resources on Azure."""

    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Monitor Azure Resources"
        self.description =  "Monitor resources on Azure."
        self.canRunInBackground = False # no effect in ArcGIS Pro

    def getParameterInfo(self):
        """Define parameter definitions"""

        params = []

        # 0, basic: working directory
        working_dir = arcpy.Parameter(
            displayName="Working directory", name="working_dir",
            datatype="DEWorkspace", parameterType="Required", direction="Input")

        working_dir.value = arcpy.env.scratchFolder

        # 1: credential type
        cred_type = arcpy.Parameter(
            displayName="Azure credential", name="cred_type",
            datatype="GPString", parameterType="Required", direction="Input")

        cred_type.filter.type = "ValueList"
        cred_type.filter.list = ["Encrypted file", "Manual input"]
        cred_type.value = "Encrypted file"

        # 2: encrypted credential file
        cred_file = arcpy.Parameter(
            displayName="Encrypted credential file", name="cred_file",
            datatype="DEFile", parameterType="Optional", direction="Input",
            enabled=True)

        cred_file.value = os.path.join(arcpy.env.scratchFolder, "azure_cred.bin")

        # 3: passcode
        passcode = arcpy.Parameter(
            displayName="Passcode for the credential file", name="passcode",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=True)

        # 4: Batch account name
        azure_batch_name = arcpy.Parameter(
            displayName="Azure Batch account name", name="azure_batch_name",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 5: Batch account key
        azure_batch_key = arcpy.Parameter(
            displayName="Azure Batch account key", name="azure_batch_key",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 6: Batch account URL
        azure_batch_URL = arcpy.Parameter(
            displayName="Azure Batch account URL", name="azure_batch_URL",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 7: Storage account name
        azure_storage_name = arcpy.Parameter(
            displayName="Azure Storage account name", name="azure_storage_name",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 8: Storage account key
        azure_storage_key = arcpy.Parameter(
            displayName="Azure Storage account key", name="azure_storage_key",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        params += [working_dir, cred_type, cred_file, passcode,
                   azure_batch_name, azure_batch_key, azure_batch_URL,
                   azure_storage_name, azure_storage_key]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        parameters[2].enabled = (parameters[1].value == "Encrypted file")
        parameters[3].enabled = (parameters[1].value == "Encrypted file")

        if parameters[2].enabled:
            parameters[2].value = os.path.join(arcpy.env.scratchFolder, "azure_cred.bin")
        else:
            parameters[2].value = None

        for i in range(4, 9):
            parameters[i].enabled = (not parameters[2].enabled)

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        if parameters[1].value == "Encrypted file":
            if parameters[2].value is None:
                parameters[2].setErrorMessage("Require a credential file.")

            if parameters[3].value is None:
                parameters[3].setErrorMessage("Require passcode.")
        else:
            for i in range(4, 9):
                if parameters[i].value is None:
                    parameters[i].setErrorMessage("Cannot be empty.")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        # path of the working directory
        working_dir = parameters[0].valueAsText.replace("\\", "\\\\")

        # Azure credential
        if parameters[1].value == "Encrypted file":
            credential = helpers.azuretools.UserCredential()
            credential.read_encrypted(
                parameters[3].valueAsText, parameters[2].valueAsText)
        else:
            credential = helpers.azuretools.UserCredential(
                parameters[4].value, parameters[5].value, parameters[6].value,
                parameters[7].value, parameters[8].value)

        # initialize an Azure mission
        mission = helpers.azuretools.Mission()

        backup = os.path.join(working_dir, "landspill-azure_backup_file.dat")
        if os.path.isfile(backup):
            mission.init_info_from_file(backup)
        else:
            mission.init_info("landspill-azure", wd=working_dir)

        mission.setup_communication(cred=credential)

        # get graphical monitor
        mission.get_graphical_monitor(parameters[2].valueAsText, parameters[3].valueAsText)

        return
