#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
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
Write GeoClaw setrun.py
"""
import os
import numpy

template = \
"########################################################################################################################" + "\n" + \
"# Copyright © 2019-2020 Pi-Yueh Chuang and Lorena A. Barba" + "\n" + \
"# All Rights Reserved." + "\n" + \
"#" + "\n" + \
"# Contributors: Pi-Yueh Chuang <pychuang@gwu.edu>" + "\n" + \
"#" + "\n" + \
"# Licensed under the BSD-3-Clause License (the \"License\")." + "\n" + \
"# You may not use this file except in compliance with the License." + "\n" + \
"# You may obtain a copy of the License at: https://opensource.org/licenses/BSD-3-Clause" + "\n" + \
"#" + "\n" + \
"# BSD-3-Clause License:" + "\n" + \
"#" + "\n" + \
"# Redistribution and use in source and binary forms, with or without modification, are permitted provided" + "\n" + \
"# that the following conditions are met:" + "\n" + \
"#" + "\n" + \
"# 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the" + "\n" + \
"#    following disclaimer." + "\n" + \
"#" + "\n" + \
"# 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the" + "\n" + \
"#    following disclaimer in the documentation and/or other materials provided with the distribution." + "\n" + \
"#" + "\n" + \
"# 3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or" + "\n" + \
"#    promote products derived from this software without specific prior written permission." + "\n" + \
"#" + "\n" + \
"# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS \"AS IS\" AND ANY EXPRESS OR IMPLIED WARRANTIES," + "\n" + \
"# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE" + "\n" + \
"# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT," + "\n" + \
"# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE" + "\n" + \
"# GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY" + "\n" + \
"# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN" + "\n" + \
"# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE." + "\n" + \
"########################################################################################################################" + "\n" + \
"from __future__ import absolute_import" + "\n" + \
"from __future__ import print_function" + "\n" + \
"import os" + "\n" + \
"import numpy" + "\n" + \
"def setrun(claw_pkg='geoclaw'):" + "\n" + \
"    from clawpack.clawutil import data" + "\n" + \
"    assert claw_pkg.lower() == 'geoclaw',  'Expected claw_pkg = geoclaw'" + "\n" + \
"    num_dim = 2" + "\n" + \
"    rundata = data.ClawRunData(claw_pkg, num_dim)" + "\n" + \
"    rundata = setgeo(rundata)" + "\n" + \
"    rundata = setamr(rundata)" + "\n" + \
"    clawdata = rundata.clawdata" + "\n" + \
"    clawdata.num_dim = num_dim" + "\n" + \
"    clawdata.lower[0] = {point[0]}-{extent[2]}" + "\n" + \
"    clawdata.upper[0] = {point[0]}+{extent[3]}" + "\n" + \
"    clawdata.lower[1] = {point[1]}-{extent[1]}" + "\n" + \
"    clawdata.upper[1] = {point[1]}+{extent[0]}" + "\n" + \
"    clawdata.num_cells[0] = {NCells[0]:d}" + "\n" + \
"    clawdata.num_cells[1] = {NCells[1]:d}" + "\n" + \
"    clawdata.num_eqn = 3" + "\n" + \
"    clawdata.num_aux = 2" + "\n" + \
"    clawdata.capa_index = 0" + "\n" + \
"    clawdata.t0 = 0.0" + "\n" + \
"    clawdata.restart = False" + "\n" + \
"    clawdata.restart_file = 'fort.chk00006'" + "\n" + \
"    clawdata.output_style = 2" + "\n" + \
"    clawdata.output_times = list(numpy.arange(0, {end_time}+1, {output_time}))" + "\n" + \
"    clawdata.output_format = 'binary'" + "\n" + \
"    clawdata.output_q_components = 'all'" + "\n" + \
"    clawdata.output_aux_components = 'all'" + "\n" + \
"    clawdata.output_aux_onlyonce = True" + "\n" + \
"    clawdata.verbosity = 3" + "\n" + \
"    clawdata.dt_variable = 1" + "\n" + \
"    clawdata.dt_max = {dt_max}" + "\n" + \
"    clawdata.dt_initial = {dt_init}" + "\n" + \
"    clawdata.cfl_desired = {cfl_desired}" + "\n" + \
"    clawdata.cfl_max = {cfl_max}" + "\n" + \
"    clawdata.steps_max = 100000" + "\n" + \
"    clawdata.order = 2" + "\n" + \
"    clawdata.dimensional_split = 'unsplit'" + "\n" + \
"    clawdata.transverse_waves = 2" + "\n" + \
"    clawdata.num_waves = 3" + "\n" + \
"    clawdata.limiter = ['mc', 'mc', 'mc']" + "\n" + \
"    clawdata.use_fwaves = True" + "\n" + \
"    clawdata.source_split = 'godunov'" + "\n" + \
"    clawdata.num_ghost = 2" + "\n" + \
"    clawdata.bc_lower[0] = 1" + "\n" + \
"    clawdata.bc_upper[0] = 1" + "\n" + \
"    clawdata.bc_lower[1] = 1" + "\n" + \
"    clawdata.bc_upper[1] = 1" + "\n" + \
"    clawdata.checkpt_style = 0" + "\n" + \
"    return rundata" + "\n" + \
"def setamr(rundata):" + "\n" + \
"    try:" + "\n" + \
"        amrdata = rundata.amrdata" + "\n" + \
"    except:" + "\n" + \
"        print('*** Error, this rundata has no amrdata attribute')" + "\n" + \
"        raise AttributeError('Missing amrdata attribute')" + "\n" + \
"    amrdata.amr_levels_max = {amr_max}" + "\n" + \
"    amrdata.refinement_ratios_x = {refinement_ratio}" + "\n" + \
"    amrdata.refinement_ratios_y = {refinement_ratio}" + "\n" + \
"    amrdata.refinement_ratios_t = {refinement_ratio}" + "\n" + \
"    amrdata.aux_type = ['center', 'center']" + "\n" + \
"    amrdata.flag_richardson = False" + "\n" + \
"    amrdata.flag2refine = True" + "\n" + \
"    amrdata.regrid_interval = 1" + "\n" + \
"    amrdata.regrid_buffer_width  = 1" + "\n" + \
"    amrdata.clustering_cutoff = 0.80000" + "\n" + \
"    amrdata.verbosity_regrid = 0" + "\n" + \
"    amrdata.dprint = False" + "\n" + \
"    amrdata.eprint = False" + "\n" + \
"    amrdata.edebug = False" + "\n" + \
"    amrdata.gprint = False" + "\n" + \
"    amrdata.nprint = False" + "\n" + \
"    amrdata.pprint = False" + "\n" + \
"    amrdata.rprint = False" + "\n" + \
"    amrdata.sprint = False" + "\n" + \
"    amrdata.tprint = False" + "\n" + \
"    amrdata.uprint = False" + "\n" + \
"    regions = rundata.regiondata.regions" + "\n" + \
"    return rundata" + "\n" + \
"def setgeo(rundata):" + "\n" + \
"    try:" + "\n" + \
"        geo_data = rundata.geo_data" + "\n" + \
"    except:" + "\n" + \
"        print('*** Error, this rundata has no geo_data attribute')" + "\n" + \
"        raise AttributeError('Missing geo_data attribute')" + "\n" + \
"    geo_data.gravity = 9.81" + "\n" + \
"    geo_data.coordinate_system = 1" + "\n" + \
"    geo_data.earth_radius = 6367.5e3" + "\n" + \
"    geo_data.coriolis_forcing = False" + "\n" + \
"    geo_data.sea_level = 0.0" + "\n" + \
"    geo_data.dry_tolerance = 1.e-4" + "\n" + \
"    geo_data.friction_forcing = False" + "\n" + \
"    geo_data.manning_coefficient = 0.035" + "\n" + \
"    geo_data.friction_depth = 1.e6" + "\n" + \
"    geo_data.update_tol = geo_data.dry_tolerance" + "\n" + \
"    geo_data.refine_tol = 0.0" + "\n" + \
"    refinement_data = rundata.refinement_data" + "\n" + \
"    refinement_data.wave_tolerance = 1.e-5" + "\n" + \
"    refinement_data.speed_tolerance = [1e-8]" + "\n" + \
"    refinement_data.deep_depth = 1e2" + "\n" + \
"    refinement_data.max_level_deep = 3" + "\n" + \
"    refinement_data.variable_dt_refinement_ratios = True" + "\n" + \
"    topo_data = rundata.topo_data" + "\n" + \
"    topo_data.topofiles.append([3, 1, 5, 0., 1.e10, \"topo.asc\"])" + "\n" + \
"    dtopo_data = rundata.dtopo_data" + "\n" + \
"    rundata.qinit_data.qinit_type = 0" + "\n" + \
"    rundata.qinit_data.qinitfiles = []" + "\n" + \
"    fixedgrids = rundata.fixed_grid_data" + "\n" + \
"    from clawpack.geoclaw.data import LandSpillData" + "\n" + \
"    rundata.add_data(LandSpillData(), 'landspill_data')" + "\n" + \
"    landspill = rundata.landspill_data" + "\n" + \
"    landspill.ref_mu = {ref_mu}" + "\n" + \
"    landspill.ref_temperature = {ref_temp}" + "\n" + \
"    landspill.ambient_temperature = {amb_temp}" + "\n" + \
"    landspill.density = {density}" + "\n" + \
"    ptsources_data = landspill.point_sources" + "\n" + \
"    ptsources_data.n_point_sources = 1" + "\n" + \
"    ptsources_data.point_sources.append(" + "\n" + \
"        [[{point[0]}, {point[1]}], {NStages}, {StageTimes}, {StageRates}])" + "\n" + \
"    darcy_weisbach_data = landspill.darcy_weisbach_friction" + "\n" + \
"    darcy_weisbach_data.type = {friction_type}" + "\n" + \
"    darcy_weisbach_data.dry_tol = 1e-4" + "\n" + \
"    darcy_weisbach_data.friction_tol = 1e6" + "\n" + \
"    darcy_weisbach_data.default_roughness = {roughness}" + "\n" + \
"    darcy_weisbach_data.filename = 'roughness.txt'" + "\n" + \
"    hydro_feature_data = landspill.hydro_features" + "\n" + \
"    hydro_feature_data.files = {hydros}" + "\n" + \
"    evaporation_data = landspill.evaporation" + "\n" + \
"    evaporation_data.type = {evap_type}" + "\n" + \
"    evaporation_data.coefficients = {evap_coeffs}" + "\n" + \
"    return rundata" + "\n" + \
"if __name__ == '__main__':" + "\n" + \
"    import sys" + "\n" + \
"    rundata = setrun(*sys.argv[1:])" + "\n" + \
"    rundata.write()"

def write_setrun(
        aprx_file, out_dir, rupture_point_layer, rupture_point_path,
        point, extent, end_time, output_time,
        res, ref_mu, ref_temp, amb_temp,
        density, leak_profile, evap_type, evap_coeffs, n_hydros,
        friction_type, roughness, dt_init, dt_max, cfl_desired,
        cfl_max, amr_max, refinement_ratio,
        apply_datetime_stamp, datetime_stamp, calendar_type,
        case_name_method, case_field_name):

    """Added parameters for CF datetime compliance and case name field - 6/28/2019 - G2 Integrated Solutions - JTT"""

    """Write setrun.py"""

    if not os.path.isdir(out_dir):
        raise FileNotFoundError("{} does not exist.".format(out_dir))

    NCells = [int((extent[3]+extent[2])/(4*res[0])+0.5),
              int((extent[1]+extent[0])/(4*res[1])+0.5)]

    # convert minutes to seconds
    end_time *= 60
    output_time *= 60

    if evap_type == "None":
        evap_type_num = 0
    elif evap_type == "Fingas1996 Log Law":
        evap_type_num = 1
    elif evap_type == "Fingas1996 SQRT Law":
        evap_type_num = 2
    else:
        raise RuntimeError

    if friction_type == "None":
        friction_type_num = 0
    elif friction_type == "Three-regime model":
        friction_type_num = 4
    else:
        raise RuntimeError

    hydro_strings = ["hydro_{}.asc".format(i) for i in range(n_hydros)]

    if dt_init == 0:
        dt_init = dt_max / (refinement_ratio**(amr_max-1))

    refinement_ratio_str = numpy.array2string(
        numpy.ones(amr_max-1, dtype=int)*refinement_ratio, separator=", ")

    data = template.format(
        point=point, extent=extent, NCells=NCells,
        end_time=end_time, output_time=output_time,
        ref_mu=ref_mu, ref_temp=ref_temp, amb_temp=amb_temp, density=density,
        NStages=leak_profile.shape[0],
        StageTimes=numpy.array2string(leak_profile[:, 0], separator=", "),
        StageRates=numpy.array2string(leak_profile[:, 1], separator=", "),
        evap_type=evap_type_num,
        evap_coeffs=numpy.array2string(evap_coeffs, separator=", "),
        hydros=hydro_strings,
        friction_type=friction_type_num,
        roughness=roughness,
        dt_init=dt_init, dt_max=dt_max,
        cfl_desired=cfl_desired, cfl_max=cfl_max,
        amr_max=amr_max, refinement_ratio=refinement_ratio_str)

    output = os.path.join(out_dir, "setrun.py")
    with open(output, "w") as f:
        f.write(data)

    return output, write_roughness(aprx_file, out_dir, rupture_point_layer, rupture_point_path,
                                   point, extent, roughness,
                                   apply_datetime_stamp, datetime_stamp, calendar_type,
                                   case_name_method, case_field_name)


def write_roughness(aprx_file, out_dir, rupture_point_layer, rupture_point_path, point, extent, value,
                    apply_datetime_stamp, datetime_stamp, calendar_type,
                    case_name_method, case_field_name):

    """Write roughness.txt."""

    temp = \
        "1 mx\n" + \
        "1 my\n" + \
        "{} xlower\n" + \
        "{} ylower\n" + \
        "{} cellsize\n" + \
        "{} nodatavalue\n\n" + \
        "{}"

    data = temp.format(
        point[0]-extent[2]-10, point[1]-extent[1]-10,
        extent[1]+extent[0]+20, -9999, value)

    output = os.path.join(out_dir, "roughness.txt")
    with open(output, "w") as f:
        f.write(data)

    return output, write_case_settings(aprx_file, out_dir, rupture_point_layer, rupture_point_path, point,
                                       apply_datetime_stamp, datetime_stamp, calendar_type,
                                       case_name_method, case_field_name)


def write_case_settings(aprx_file, out_dir, rupture_point_layer, rupture_point_path, point,
                        apply_datetime_stamp, datetime_stamp, calendar_type,
                        case_name_method, case_field_name):
    """
    Write the case settings file which is used to store case parameters that do not affect GeoClaw directly.
    Added to address NetCDF CF datetime stamp compliance and optional field-based case naming.
    6/28/2019 - G2 Integrated Solutions - JTT
    """

    file_template = \
        "ARCGIS_PROJECT={}\n" + \
        "RUPTURE_POINT_LAYER={}\n" + \
        "RUPTURE_POINT_PATH={}\n" + \
        "POINT_X={}\n" + \
        "POINT_Y={}\n" + \
        "APPLY_DATETIME_STAMP={}\n" + \
        "DATETIME_STAMP={}\n" + \
        "CALENDAR_TYPE={}\n" + \
        "CASE_NAME_METHOD={}\n" + \
        "CASE_FIELD_NAME={}\n" + \
        "CASE_NAME={}"

    file_data = file_template.format(
        aprx_file, rupture_point_layer, rupture_point_path, point[0], point[1],
        apply_datetime_stamp, datetime_stamp, calendar_type,
        case_name_method, case_field_name, os.path.basename(out_dir))

    output = os.path.join(out_dir, "case_settings.txt")
    with open(output, "w") as f:
        f.write(file_data)

    return output
