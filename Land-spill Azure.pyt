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
import helpers.azuretools
import importlib
importlib.reload(helpers.arcgistools)


class Toolbox(object):
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
        self.label = "CreateGeoClawCases"
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
            category="Basic", displayName="Working Directory", name="working_dir",
            datatype="DEWorkspace", parameterType="Required", direction="Input")

        working_dir.value = arcpy.env.scratchFolder

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

        # 9, auto-adjust resolution based on input topo raster
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

        params += [working_dir, rupture_point, leak_profile,
                   sim_time, output_time,
                   topo_type, topo_layer, hydro_type, hydro_layers,
                   auto_res, x_res, y_res,
                   dist_top, dist_bottom, dist_left, dist_right]

        # =====================================================================
        # Fluid settings section
        # =====================================================================

        # 16
        ref_viscosity = arcpy.Parameter(
            category="Fluid settings",
            displayName="Reference dynamic viscosity (cP)", name="ref_viscosity",
            datatype="GPDouble", parameterType="Required", direction="Input")
        ref_viscosity.value = 332.0

        # 17
        ref_temp = arcpy.Parameter(
            category="Fluid settings",
            displayName="Reference temperature (Celsius)", name="ref_temp",
            datatype="GPDouble", parameterType="Required", direction="Input")
        ref_temp.value = 15.0

        # 18
        temp = arcpy.Parameter(
            category="Fluid settings",
            displayName="Ambient temperature (Celsius)", name="temp",
            datatype="GPDouble", parameterType="Required", direction="Input")
        temp.value= 25.0

        # 19
        density = arcpy.Parameter(
            category="Fluid settings",
            displayName="Density (kg/m^3)", name="density",
            datatype="GPDouble", parameterType="Required", direction="Input")
        density.value= 9.266e2

        # 20
        evap_type = arcpy.Parameter(
            category="Fluid settings",
            displayName="Evaporation model", name="evap_type",
            datatype="GPString", parameterType="Required", direction="Input")
        evap_type.filter.type = "ValueList"
        evap_type.filter.list = ["None", "Fingas1996 Log Law", "Fingas1996 SQRT Law"]
        evap_type.value = "Fingas1996 Log Law"

        # 21
        evap_c1 = arcpy.Parameter(
            category="Fluid settings",
            displayName="Evaporation coefficients 1", name="evap_c1",
            datatype="GPDouble", parameterType="Optional", direction="Input")
        evap_c1.value = 1.38

        # 22
        evap_c2 = arcpy.Parameter(
            category="Fluid settings",
            displayName="Evaporation coefficients 2", name="evap_c2",
            datatype="GPDouble", parameterType="Optional", direction="Input")
        evap_c2.value = 0.045


        params += [ref_viscosity, ref_temp, temp, density, evap_type, evap_c1, evap_c2]

        # =====================================================================
        # Darcy-Weisbach section
        # =====================================================================

        # 23
        friction_type = arcpy.Parameter(
            category="Darcy-Weisbach friction settings",
            displayName="Darcy-Weisbach model", name="friction_type",
            datatype="GPString", parameterType="Required", direction="Input")
        friction_type.filter.type = "ValueList"
        friction_type.filter.list = ["None", "Three-regime model"]
        friction_type.value = "Three-regime model"

        # 24
        roughness =  arcpy.Parameter(
            category="Darcy-Weisbach friction settings",
            displayName="Surface roughness", name="roughness",
            datatype="GPDouble", parameterType="Optional", direction="Input")
        roughness.value = 0.1

        params += [friction_type, roughness]

        # =====================================================================
        # Misc
        # =====================================================================

        # 25
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

        # 26
        dt_init = arcpy.Parameter(
            category="Advanced numerical parameters",
            displayName="Initial time-step size (second). Use 0 for auto-setting.",
            name="dt_init",
            datatype="GPDouble", parameterType="Required", direction="Input")
        dt_init.value = 0

        # 27
        dt_max = arcpy.Parameter(
            category="Advanced numerical parameters",
            displayName="Maximum time-step size (second)",
            name="dt_max",
            datatype="GPDouble", parameterType="Required", direction="Input")
        dt_max.value = 4.0

        # 28
        cfl_desired = arcpy.Parameter(
            category="Advanced numerical parameters",
            displayName="Desired CFL number",
            name="cfl_desired",
            datatype="GPDouble", parameterType="Required", direction="Input")
        cfl_desired.value = 0.9

        # 29
        cfl_max = arcpy.Parameter(
            category="Advanced numerical parameters",
            displayName="Maximum allowed CFL number",
            name="cfl_max",
            datatype="GPDouble", parameterType="Required", direction="Input")
        cfl_max.value = 0.95

        # 30
        amr_max = arcpy.Parameter(
            category="Advanced numerical parameters",
            displayName="Total AMR levels",
            name="amr_max",
            datatype="GPLong", parameterType="Required", direction="Input")
        amr_max.filter.type = "ValueList"
        amr_max.filter.list = list(range(1, 11))
        amr_max.value = 2

        # 31
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
        parameters[4].enabled = (parameters[3].value == "Local raster layer")

        # if using local feature layers
        parameters[6].enabled = (parameters[5].value == "Local feature layers")

        # option for auto setting of resolution
        if parameters[4].enabled:
            parameters[7].enabled = True
        else:
            parameters[7].enabled = False
            parameters[7].value = False

        # x and 7 resolution
        parameters[8].enabled = not parameters[7].value
        parameters[9].enabled = not parameters[7].value

        # Evaporation Fingas coefficient
        parameters[19].enabled = not parameters[18].value == "None"
        parameters[20].enabled = not parameters[18].value == "None"

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        if parameters[4].enabled and parameters[4].value is None:
            parameters[4].setErrorMessage("Require a topography raster layer")

        if parameters[24].value < 0:
            parameters[24].setErrorMessage("Time-step can not be negative")

        if parameters[25].value <= 0:
            parameters[25].setErrorMessage("Time-step can not be zero or negative")

        if parameters[26].value <= 0:
            parameters[26].setErrorMessage("CFL can not be zero or negative")

        if parameters[27].value <= 0:
            parameters[27].setErrorMessage("CFL can not be zero or negative")

        if parameters[26].value > 1.0:
            parameters[26].setErrorMessage("CFL can not exceed 1.0")

        if parameters[27].value > 1.0:
            parameters[27].setErrorMessage("CFL can not exceed 1.0")

        if parameters[29].value < 2:
            parameters[29].setErrorMessage("CFL can not be less than 2")

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        importlib.reload(helpers.arcgistools)
        arcpy.env.parallelProcessingFactor="75%"

        # 0:, path of the working directory
        working_dir = parameters[0].valueAsText.replace("\\", "\\\\")

        # 1: xy coordinates of rupture locations (Npoints x 2)
        points = arcpy.da.FeatureClassToNumPyArray(
            parameters[1].valueAsText, ["SHAPE@X", "SHAPE@Y"],
            spatial_reference=arcpy.SpatialReference(3857))

        # 2: profile of leak rate (Nstages x 2)
        leak_profile = numpy.array(parameters[2].value, dtype=numpy.float64)

        # 3, 4: base topography file
        if parameters[3].value == "Local raster layer":
            base_topo = parameters[4].valueAsText
        else:
            base_topo = None

        # 5, 6: hydrological feature layers (1D array with size Nfeatures)
        if parameters[5].value == "Local feature layers":
            if parameters[6].value is None:
                hydro_layers = []
            else:
                hydro_layers = \
                    [parameters[6].value.getRow(i).strip("' ")
                     for i in range(parameters[4].value.rowCount)]

        # 7, 8, 9: finest resolution in x & y direction
        if parameters[7].value: # auto-setting
            resolution = numpy.ones(2, dtype=numpy.float64) * \
                arcpy.Describe(base_topo).meanCellWidth
        else:
            resolution = numpy.array(
                [parameters[8].value, parameters[9].value], dtype=numpy.float64)

        # 10-13: computational domain extent (relative to rupture points)
        domain = numpy.array(
            [parameters[10].value, parameters[11].value,
             parameters[12].value, parameters[13].value], dtype=numpy.float64)

        # 14-20: fluid properties
        ref_mu=parameters[14].value
        ref_temp=parameters[15].value
        amb_temp=parameters[16].value
        density=parameters[17].value
        evap_type=parameters[18].value
        evap_coeffs=numpy.array([parameters[19].value, parameters[20].value])

        # 21, 22: friction
        friction_type = parameters[21].value
        roughness = parameters[22].value

        # 23: misc
        ignore = parameters[23].value

        # 24-29: advanced numerical parameters
        dt_init = parameters[24].value
        dt_max = parameters[25].value
        cfl_desired = parameters[26].value
        cfl_max = parameters[27].value
        amr_max = parameters[28].value
        refinement_ratio = parameters[29].value

        # loop through each point to create each case and submit to Azure
        for i, point in enumerate(points):

            # create case folder
            arcpy.AddMessage("Creating case folder for point {}".format(point))
            case_path = helpers.arcgistools.create_single_folder(
                working_dir, point, ignore)

            # create topography ASCII file
            if base_topo is not None:
                arcpy.AddMessage("Creating topo input for point {}".format(point))
                topo = helpers.arcgistools.prepare_single_topo(
                    base_topo, point, domain, case_path, ignore)

            # create ASCII rasters for hydorlogical files
            if parameters[5].value == "Local feature layers":
                arcpy.AddMessage("Creating hydro input for point {}".format(point))
                hydros = helpers.arcgistools.prepare_single_point_hydros(
                    hydro_layers, point, domain, min(resolution), case_path, ignore)
            else:
                hydros = ["hydro_0.asc"]

            # create setrun.py and roughness
            arcpy.AddMessage("Creating GeoClaw config for point {}".format(point))
            setrun, roughness_file = helpers.arcgistools.write_setrun(
                out_dir=case_path, point=point, extent=domain, res=resolution,
                ref_mu=ref_mu, ref_temp=ref_temp, amb_temp=amb_temp,
                density=density, leak_profile=leak_profile,
                evap_type=evap_type, evap_coeffs=evap_coeffs,
                n_hydros = len(hydros),
                friction_type=friction_type, roughness=roughness,
                dt_init=dt_init, dt_max=dt_max,
                cfl_desired=cfl_desired, cfl_max=cfl_max,
                amr_max=amr_max, refinement_ratio=refinement_ratio)

            arcpy.AddMessage("Done preparing point {}".format(point))

        return

class CreateAzureCredentialFile(object):
    """Create an encrpyted Azure credential file."""

    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "NewEncrpytedAzureCredential"
        self.description = "Create an encrpyted Azure credential file."
        self.canRunInBackground = False # no effect in ArcGIS Pro

    def getParameterInfo(self):
        """Define parameter definitions"""

        # 0, working directory
        working_dir = arcpy.Parameter(
            displayName="Working Directory", name="working_dir",
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
            datatype="GPStringHidden", parameterType="Required", direction="Input")

        # 3: Batch account key
        azure_batch_key = arcpy.Parameter(
            displayName="Azure Batch account key", name="azure_batch_key",
            datatype="GPStringHidden", parameterType="Required", direction="Input")

        # 4: Batch account URL
        azure_batch_URL = arcpy.Parameter(
            displayName="Azure Batch account URL", name="azure_batch_URL",
            datatype="GPStringHidden", parameterType="Required", direction="Input")

        # 5: Storage account name
        azure_storage_name = arcpy.Parameter(
            displayName="Azure Storage account name", name="azure_storage_name",
            datatype="GPStringHidden", parameterType="Required", direction="Input")

        # 6: Storage account key
        azure_storage_key = arcpy.Parameter(
            displayName="Azure Storage account key", name="azure_storage_key",
            datatype="GPStringHidden", parameterType="Required", direction="Input")

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
        self.label = "RunCasesOnAzure"
        self.description =  "Submit and run cases on Azure."
        self.canRunInBackground = False # no effect in ArcGIS Pro

    def getParameterInfo(self):
        """Define parameter definitions"""

        params = []

        # 0, basic: working directory
        working_dir = arcpy.Parameter(
            displayName="Working Directory", name="working_dir",
            datatype="DEWorkspace", parameterType="Required", direction="Input")

        working_dir.value = arcpy.env.scratchFolder

        # 1, basic: rupture point
        rupture_point = arcpy.Parameter(
            displayName="Rupture point", name="rupture_point",
            datatype="GPFeatureLayer", parameterType="Required", direction="Input")

        rupture_point.filter.list = ["Point"]

        # 2: maximum number of computing nodes
        max_nodes = arcpy.Parameter(
            displayName="Maximum number of computing nodes", name="max_nodes",
            datatype="GPLong", parameterType="Required", direction="Input")

        max_nodes.value = 2

        # 3: vm type
        vm_type = arcpy.Parameter(
            displayName="Computing node type", name="vm_type",
            datatype="GPString", parameterType="Required", direction="Input")

        vm_type.filter.type = "ValueList"
        vm_type.filter.list = ["STANDARD_A1_V2", "STANDARD_H8", "STANDARD_H16"]
        vm_type.value = "STANDARD_H8"

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

        params += [working_dir, rupture_point, max_nodes, vm_type,
                   cred_type, cred_file, passcode,
                   azure_batch_name, azure_batch_key, azure_batch_URL,
                   azure_storage_name, azure_storage_key]

        # =====================================================================
        # Misc
        # =====================================================================

        # 12: Skip a case if its case folder doesn't exist locally
        ignore_local_nonexist = arcpy.Parameter(
            displayName="Skip submitting/running a case if its case folder " + \
                        "doesn't exist on local machine",
            name="ignore_local_nonexist",
            datatype="GPBoolean", parameterType="Required", direction="Input")
        ignore_local_nonexist.value = False

        # 13: Skip a case if its case folder already exist on Azure
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

        # xy coordinates of rupture locations (Npoints x 2)
        points = arcpy.da.FeatureClassToNumPyArray(
            parameters[1].valueAsText, ["SHAPE@X", "SHAPE@Y"],
            spatial_reference=arcpy.SpatialReference(3857))

        # azure credential
        max_nodes = parameters[2].value
        vm_type = parameters[3].value

        # skip a case if its case folder doesn't exist locally
        ignore_local_nonexist = parameters[12].value

        # skip a case if its case folder already exist on Azure
        ignore_azure_exist = parameters[13].value

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
        mission = helpers.azuretools.Mission(
            credential, "landspill-azure", max_nodes, [],
            output=os.devnull, vm_type=vm_type, wd=arcpy.env.scratchFolder)

        # start mission (creating pool, storage, scheduler)
        mission.start(ignore_local_nonexist, ignore_azure_exist, False)

        # loop through each point to add case to Azure task scheduler
        for i, point in enumerate(points):

            x = "{}{}".format(numpy.abs(point[0]), "E" if point[0] >= 0 else "W")
            y = "{}{}".format(numpy.abs(point[1]), "N" if point[1] >= 0 else "S")
            x = x.replace(".", "_")
            y = y.replace(".", "_")
            case = os.path.join(working_dir, "{}{}".format(x, y))

            arcpy.AddMessage("Adding case {}".format(case))
            result = mission.add_task(case, ignore_local_nonexist, ignore_azure_exist)
            arcpy.AddMessage(result)

            if i == (max_nodes - 1):
                mission.adapt_size()

        if points.shape[0] < max_nodes:
            mission.adapt_size()

        return

class DownloadCasesFromAzure(object):
    """Download cases on Azure."""

    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "DownloadCasesFromAzure"
        self.description =  "Download cases from Azure."
        self.canRunInBackground = False # no effect in ArcGIS Pro

    def getParameterInfo(self):
        """Define parameter definitions"""

        params = []

        # 0, basic: working directory
        working_dir = arcpy.Parameter(
            displayName="Working Directory", name="working_dir",
            datatype="DEWorkspace", parameterType="Required", direction="Input")

        working_dir.value = arcpy.env.scratchFolder

        # 1, basic: rupture point
        rupture_point = arcpy.Parameter(
            displayName="Rupture point", name="rupture_point",
            datatype="GPFeatureLayer", parameterType="Required", direction="Input")

        rupture_point.filter.list = ["Point"]

        # 2: credential type
        cred_type = arcpy.Parameter(
            displayName="Azure credential", name="cred_type",
            datatype="GPString", parameterType="Required", direction="Input")

        cred_type.filter.type = "ValueList"
        cred_type.filter.list = ["Encrypted file", "Manual input"]
        cred_type.value = "Encrypted file"

        # 3: encrypted credential file
        cred_file = arcpy.Parameter(
            displayName="Encrypted credential file", name="cred_file",
            datatype="DEFile", parameterType="Optional", direction="Input",
            enabled=True)

        cred_file.value = os.path.join(arcpy.env.scratchFolder, "azure_cred.bin")

        # 4: passcode
        passcode = arcpy.Parameter(
            displayName="Passcode for the credential file", name="passcode",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=True)

        # 5: Batch account name
        azure_batch_name = arcpy.Parameter(
            displayName="Azure Batch account name", name="azure_batch_name",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 6: Batch account key
        azure_batch_key = arcpy.Parameter(
            displayName="Azure Batch account key", name="azure_batch_key",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 7: Batch account URL
        azure_batch_URL = arcpy.Parameter(
            displayName="Azure Batch account URL", name="azure_batch_URL",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 8: Storage account name
        azure_storage_name = arcpy.Parameter(
            displayName="Azure Storage account name", name="azure_storage_name",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 9: Storage account key
        azure_storage_key = arcpy.Parameter(
            displayName="Azure Storage account key", name="azure_storage_key",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        params += [working_dir, rupture_point,
                   cred_type, cred_file, passcode,
                   azure_batch_name, azure_batch_key, azure_batch_URL,
                   azure_storage_name, azure_storage_key]

        # =====================================================================
        # Misc
        # =====================================================================

        # 10: Skip a case if its case folder doesn't exist locally
        ignore_nonexist = arcpy.Parameter(
            displayName="Skip if a case is not found on Azure",
            name="ignore_nonexist",
            datatype="GPBoolean", parameterType="Required", direction="Input")
        ignore_nonexist.value = True

        # 11: Skip a case if its case folder already exist on Azure
        ignore_downloaded = arcpy.Parameter(
            displayName="Skip if a case is already downloaded",
            name="ignore_downloaded",
            datatype="GPBoolean", parameterType="Required", direction="Input")
        ignore_downloaded.value = True

        # 12: Also download raw GeoClaw result data
        download_raw = arcpy.Parameter(
            displayName="Also download GeoClaw raw data",
            name="download_raw",
            datatype="GPBoolean", parameterType="Required", direction="Input")
        download_raw.value = False

        # 13: Also download topography & hydro rasters
        download_asc = arcpy.Parameter(
            displayName=\
                "Also download topography and hydrological rasters used by GeoClaw",
            name="download_asc",
            datatype="GPBoolean", parameterType="Required", direction="Input")
        download_asc.value = False

        params += [ignore_nonexist, ignore_downloaded, download_raw, download_asc]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        parameters[3].enabled = (parameters[2].value == "Encrypted file")
        parameters[4].enabled = (parameters[2].value == "Encrypted file")

        if parameters[3].enabled:
            parameters[3].value = os.path.join(arcpy.env.scratchFolder, "azure_cred.bin")
        else:
            parameters[3].value = None

        for i in range(5, 10):
            parameters[i].enabled = (not parameters[3].enabled)

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        if parameters[2].value == "Encrypted file":
            if parameters[3].value is None:
                parameters[3].setErrorMessage("Require a credential file.")

            if parameters[4].value is None:
                parameters[4].setErrorMessage("Require passcode.")
        else:
            for i in range(5, 10):
                if parameters[i].value is None:
                    parameters[i].setErrorMessage("Cannot be empty.")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        # path of the working directory
        working_dir = parameters[0].valueAsText.replace("\\", "\\\\")

        # xy coordinates of rupture locations (Npoints x 2)
        points = arcpy.da.FeatureClassToNumPyArray(
            parameters[1].valueAsText, ["SHAPE@X", "SHAPE@Y"],
            spatial_reference=arcpy.SpatialReference(3857))

        # skip if a case is not found on Azure
        ignore_nonexist = parameters[10].value

        # skip if a case is already downloaded
        ignore_downloaded = parameters[11].value

        # also download raw data
        download_raw = parameters[12].value

        # also download topography & hydrologic rasters used by GeoClaw
        download_asc = parameters[13].value

        # Azure credential
        if parameters[2].value == "Encrypted file":
            credential = helpers.azuretools.UserCredential()
            credential.read_encrypted(
                parameters[4].valueAsText, parameters[3].valueAsText)
        else:
            credential = helpers.azuretools.UserCredential(
                parameters[5].value, parameters[6].value, parameters[7].value,
                parameters[8].value, parameters[9].value)

        # initialize an Azure mission
        mission = helpers.azuretools.Mission(
            credential, "landspill-azure", 0, [], output=os.devnull,
            wd=arcpy.env.scratchFolder)

        # get container information
        mission.controller.create_storage_container()

        # loop through each point to add case to Azure task scheduler
        for i, point in enumerate(points):

            x = "{}{}".format(numpy.abs(point[0]), "E" if point[0]>=0 else "W")
            y = "{}{}".format(numpy.abs(point[1]), "N" if point[1]>=0 else "S")
            x = x.replace(".", "_")
            y = y.replace(".", "_")
            case = os.path.join(working_dir, "{}{}".format(x, y))

            arcpy.AddMessage("Downloading case {}".format(case))
            result = mission.controller.download_dir(
                case, download_raw, download_asc,
                ignore_downloaded, ignore_nonexist)
            arcpy.AddMessage(result)

        return

class DeleteAzureResources(object):
    """Delete resources on Azure."""

    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "DeleteAzureResources"
        self.description =  "Delete resources on Azure."
        self.canRunInBackground = False # no effect in ArcGIS Pro

    def getParameterInfo(self):
        """Define parameter definitions"""

        params = []

        # 0: Delete Batch pool, i.e., cluster
        delete_pool = arcpy.Parameter(
            displayName="Delete pool (cluster)",
            name="delete_pool",
            datatype="GPBoolean", parameterType="Required", direction="Input")
        delete_pool.value = True

        # 1: Delete Batch job, i.e., task scheduler
        delete_job = arcpy.Parameter(
            displayName="Delete job (task scheduler)",
            name="delete_job",
            datatype="GPBoolean", parameterType="Required", direction="Input")
        delete_job.value = True

        # 2: Delete Storage container
        delete_container = arcpy.Parameter(
            displayName="Delete storage container",
            name="delete_container",
            datatype="GPBoolean", parameterType="Required", direction="Input")
        delete_container.value = False

        params += [delete_pool, delete_job, delete_container]


        # 3: credential type
        cred_type = arcpy.Parameter(
            displayName="Azure credential", name="cred_type",
            datatype="GPString", parameterType="Required", direction="Input")

        cred_type.filter.type = "ValueList"
        cred_type.filter.list = ["Encrypted file", "Manual input"]
        cred_type.value = "Encrypted file"

        # 4: encrypted credential file
        cred_file = arcpy.Parameter(
            displayName="Encrypted credential file", name="cred_file",
            datatype="DEFile", parameterType="Optional", direction="Input",
            enabled=True)

        cred_file.value = os.path.join(arcpy.env.scratchFolder, "azure_cred.bin")

        # 5: passcode
        passcode = arcpy.Parameter(
            displayName="Passcode for the credential file", name="passcode",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=True)

        # 6: Batch account name
        azure_batch_name = arcpy.Parameter(
            displayName="Azure Batch account name", name="azure_batch_name",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 7: Batch account key
        azure_batch_key = arcpy.Parameter(
            displayName="Azure Batch account key", name="azure_batch_key",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 8: Batch account URL
        azure_batch_URL = arcpy.Parameter(
            displayName="Azure Batch account URL", name="azure_batch_URL",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 9: Storage account name
        azure_storage_name = arcpy.Parameter(
            displayName="Azure Storage account name", name="azure_storage_name",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 10: Storage account key
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

        parameters[4].enabled = (parameters[3].value == "Encrypted file")
        parameters[5].enabled = (parameters[3].value == "Encrypted file")

        if parameters[4].enabled:
            parameters[4].value = os.path.join(arcpy.env.scratchFolder, "azure_cred.bin")
        else:
            parameters[4].value = None

        for i in range(6, 11):
            parameters[i].enabled = (not parameters[4].enabled)

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        if parameters[3].value == "Encrypted file":
            if parameters[4].value is None:
                parameters[4].setErrorMessage("Require a credential file.")

            if parameters[5].value is None:
                parameters[5].setErrorMessage("Require passcode.")
        else:
            for i in range(6, 11):
                if parameters[i].value is None:
                    parameters[i].setErrorMessage("Cannot be empty.")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # skip if a case is not found on Azure
        delete_pool = parameters[0].value

        # skip if a case is already downloaded
        delete_job = parameters[1].value

        # also download raw data
        delete_container = parameters[2].value

        # Azure credential
        if parameters[3].value == "Encrypted file":
            credential = helpers.azuretools.UserCredential()
            credential.read_encrypted(
                parameters[5].valueAsText, parameters[4].valueAsText)
        else:
            credential = helpers.azuretools.UserCredential(
                parameters[6].value, parameters[7].value, parameters[8].value,
                parameters[9].value, parameters[10].value)

        # initialize an Azure mission
        mission = helpers.azuretools.Mission(
            credential, "landspill-azure", 0, [], output=os.devnull,
            wd=arcpy.env.scratchFolder)

        if delete_pool:
            mission.controller.delete_pool()

        if delete_job:
            mission.controller.delete_job()

        if delete_container:
            mission.controller.delete_storage_container()

        return

class MonitorAzureResources(object):
    """Monitor resources on Azure."""

    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "MonitorAzureResources"
        self.description =  "Monitor resources on Azure."
        self.canRunInBackground = False # no effect in ArcGIS Pro

    def getParameterInfo(self):
        """Define parameter definitions"""

        params = []

        # 0: credential type
        cred_type = arcpy.Parameter(
            displayName="Azure credential", name="cred_type",
            datatype="GPString", parameterType="Required", direction="Input")

        cred_type.filter.type = "ValueList"
        cred_type.filter.list = ["Encrypted file", "Manual input"]
        cred_type.value = "Encrypted file"

        # 1: encrypted credential file
        cred_file = arcpy.Parameter(
            displayName="Encrypted credential file", name="cred_file",
            datatype="DEFile", parameterType="Optional", direction="Input",
            enabled=True)

        cred_file.value = os.path.join(arcpy.env.scratchFolder, "azure_cred.bin")

        # 2: passcode
        passcode = arcpy.Parameter(
            displayName="Passcode for the credential file", name="passcode",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=True)

        # 3: Batch account name
        azure_batch_name = arcpy.Parameter(
            displayName="Azure Batch account name", name="azure_batch_name",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 4: Batch account key
        azure_batch_key = arcpy.Parameter(
            displayName="Azure Batch account key", name="azure_batch_key",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 5: Batch account URL
        azure_batch_URL = arcpy.Parameter(
            displayName="Azure Batch account URL", name="azure_batch_URL",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 6: Storage account name
        azure_storage_name = arcpy.Parameter(
            displayName="Azure Storage account name", name="azure_storage_name",
            datatype="GPStringHidden", parameterType="Optional",
            direction="Input", enabled=False)

        # 7: Storage account key
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

        parameters[1].enabled = (parameters[0].value == "Encrypted file")
        parameters[2].enabled = (parameters[0].value == "Encrypted file")

        if parameters[1].enabled:
            parameters[1].value = os.path.join(arcpy.env.scratchFolder, "azure_cred.bin")
        else:
            parameters[1].value = None

        for i in range(3, 8):
            parameters[i].enabled = (not parameters[1].enabled)

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        if parameters[0].value == "Encrypted file":
            if parameters[1].value is None:
                parameters[1].setErrorMessage("Require a credential file.")

            if parameters[2].value is None:
                parameters[2].setErrorMessage("Require passcode.")
        else:
            for i in range(3, 8):
                if parameters[i].value is None:
                    parameters[i].setErrorMessage("Cannot be empty.")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        import tkinter
        import datetime
        import time

        # Azure credential
        if parameters[0].value == "Encrypted file":
            credential = helpers.azuretools.UserCredential()
            credential.read_encrypted(
                parameters[2].valueAsText, parameters[1].valueAsText)
        else:
            credential = helpers.azuretools.UserCredential(
                parameters[3].value, parameters[4].value, parameters[5].value,
                parameters[6].value, parameters[7].value)

        # initialize an Azure mission
        self.mission = helpers.azuretools.Mission(
            credential, "landspill-azure", 0, [], output=os.devnull,
            wd=arcpy.env.scratchFolder)

        # initialize tkinter windows
        self.root = tkinter.Tk()
        self.window = helpers.arcgistools.AzureMonitorWindow(self.root)

        # start monitor
        self.window.after(0, self._recursive_callback)
        self.window.mainloop()

        return

    def _recursive_callback(self):
        """A private function used by GUI to update monitor."""
        info = self.mission.get_monitor_string()
        self.window.update_text(info)
        self.window.after(10000, self._recursive_callback)
