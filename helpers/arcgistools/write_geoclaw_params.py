#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Pi-Yueh Chuang <pychuang@gwu.edu>
#
# Distributed under terms of the MIT license.
"""
Write GeoClaw setrun.py
"""
import numpy

template = \
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
"    clawdata.num_cells[1] = {NCells[0]:d}" + "\n" + \
"    clawdata.num_eqn = 3" + "\n" + \
"    clawdata.num_aux = 2" + "\n" + \
"    clawdata.capa_index = 0" + "\n" + \
"    clawdata.t0 = 0.0" + "\n" + \
"    clawdata.restart = False" + "\n" + \
"    clawdata.restart_file = 'fort.chk00006'" + "\n" + \
"    clawdata.output_style = 1" + "\n" + \
"    clawdata.num_output_times = 240" + "\n" + \
"    clawdata.tfinal = 28800" + "\n" + \
"    clawdata.output_t0 = True" + "\n" + \
"    clawdata.output_format = 'binary'" + "\n" + \
"    clawdata.output_q_components = 'all'" + "\n" + \
"    clawdata.output_aux_components = 'all'" + "\n" + \
"    clawdata.output_aux_onlyonce = True" + "\n" + \
"    clawdata.verbosity = 3" + "\n" + \
"    clawdata.dt_variable = 1" + "\n" + \
"    dx = (clawdata.upper[0] - clawdata.lower[0]) / clawdata.num_cells[0]" + "\n" + \
"    dy = (clawdata.upper[1] - clawdata.lower[1]) / clawdata.num_cells[1]" + "\n" + \
"    dx /= numpy.prod(rundata.amrdata.refinement_ratios_x[:rundata.amrdata.amr_levels_max])" + "\n" + \
"    dy /= numpy.prod(rundata.amrdata.refinement_ratios_y[:rundata.amrdata.amr_levels_max])" + "\n" + \
"    vrate = rundata.landspill_data.point_sources.point_sources[0][-1][0]" + "\n" + \
"    clawdata.dt_initial = 0.3 * dx * dy / vrate" + "\n" + \
"    clawdata.dt_max = 4.0" + "\n" + \
"    clawdata.cfl_desired = 0.9" + "\n" + \
"    clawdata.cfl_max = 0.95" + "\n" + \
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
"    amrdata.amr_levels_max = 2" + "\n" + \
"    amrdata.refinement_ratios_x = [4]" + "\n" + \
"    amrdata.refinement_ratios_y = [4]" + "\n" + \
"    amrdata.refinement_ratios_t = [4]" + "\n" + \
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
"    refinement_data = rundata.refinement_data" + "\n" + \
"    refinement_data.wave_tolerance = 1.e-5" + "\n" + \
"    refinement_data.speed_tolerance = [1e-8]" + "\n" + \
"    refinement_data.deep_depth = 1e2" + "\n" + \
"    refinement_data.max_level_deep = 3" + "\n" + \
"    refinement_data.variable_dt_refinement_ratios = True" + "\n" + \
"    topo_data = rundata.topo_data" + "\n" + \
"    topo_data.topofiles.append([3, 1, 5, 0., 1.e10, \"{topo}\"])" + "\n" + \
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
"    darcy_weisbach_data.type = 4" + "\n" + \
"    darcy_weisbach_data.dry_tol = 1e-4" + "\n" + \
"    darcy_weisbach_data.friction_tol = 1e6" + "\n" + \
"    darcy_weisbach_data.default_roughness = 0.1" + "\n" + \
"    darcy_weisbach_data.filename = 'roughness.txt'" + "\n" + \
"    evaporation_data = landspill.evaporation" + "\n" + \
"    evaporation_data.type = {evap_type}" + "\n" + \
"    evaporation_data.coefficients = {evap_coeffs}" + "\n" + \
"    return rundata" + "\n" + \
"if __name__ == '__main__':" + "\n" + \
"    import sys" + "\n" + \
"    rundata = setrun(*sys.argv[1:])" + "\n" + \
"    rundata.write()"

def print_setrun(
        output, point, extent, res, topo, ref_mu, ref_temp, amb_temp,
        density, NStages, StageTimes, StageRates, evap_type, evap_coeffs):
    """Print setrun.py"""

    NCells = [int((extent[3]+extent[2])/(4*res[0])+0.5),
              int((extent[1]+extent[0])/(4*res[1])+0.5)]

    if evap_type == "None":
        evap_type_num = 0
    elif evap_type == "Fingas1996 Log Law":
        evap_type_num = 1
    elif evap_type == "Fingas1996 SQRT Law":
        evap_type_num = 2
    else:
        raise RuntimeError

    data = template.format(
        point=point, extent=extent, NCells=NCells, topo=topo, ref_mu=ref_mu,
        ref_temp=ref_temp, amb_temp=amb_temp, density=density, NStages=NStages,
        StageTimes=numpy.array2string(StageTimes, separator=", "),
        StageRates=numpy.array2string(StageRates, separator=", "),
        evap_type=evap_type_num,
        evap_coeffs=numpy.array2string(evap_coeffs, separator=", "))

    with open(output, "w") as f:
        f.write(data)

def print_roughness(output, point, extent, value):
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
        point[0]-extent[2], point[1]-extent[1],
        extent[1]+extent[0], -9999, value)

    with open(output, "w") as f:
        f.write(data)
