#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Pi-Yueh Chuang <pychuang@gwu.edu>
#
# Distributed under terms of the MIT license.

"""
Definition of MissionInfo.
"""
import datetime
import numpy


class MissionInfo():
    """A class holding information of a mission."""

    def __init__(self, mission_name, n_comp_nodes, tasks,
                 vm_type="STANDARD_H8"):
        """__init__

        Args:
            mission_name [in]: A str for the name of this mission.
            n_comp_nodes [in]: Total number of computing nodes requested.
            log_file[optional]: the destination of output message (default: stdout)
            vm_type [optional]: The type of virtual machine. (default: STANDARD_H8)
        """

        assert isinstance(mission_name, str), "Type error!"
        assert isinstance(n_comp_nodes, (int, numpy.int_)), "Type error!"
        assert isinstance(tasks, (list, numpy.ndarray)), "Type error!"
        assert isinstance(vm_type, str), "Type error!"

        self.name = mission_name # the name of this mission
        self.n_nodes = n_comp_nodes # the number of computing nodes
        self.vm_type = vm_type # the type of virtual machines
        self.tasks = numpy.array(tasks, dtype=str) # the list of cases

        self.pool_name = "{}-pool".format(self.name) # pool/cluster name
        self.job_name = "{}-job".format(self.name) # task schduler name
        self.container_name = "{}-container".format(self.name) # storage container name

        self.time_stamp = datetime.datetime.utcnow().replace(
            microsecond=0, tzinfo=datetime.timezone.utc)

    def __str__(self):
        """__str__"""

        s = "Name: {}\n".format(self.name) + \
            "Number of nodes: {}\n".format(self.n_nodes) + \
            "VM type: {}\n".format(self.vm_type) + \
            "Tasks :{}\n".format(self.tasks) + \
            "Pool name: {}\n".format(self.pool_name) + \
            "Job (task scheduler) name: {}\n".format(self.job_name) + \
            "Storage container name: {}\n".format(self.container_name) + \
            "Time stamp: {}\n".format(self.time_stamp)

        return s

    def add_task(self, case):
        """Add a task to the mission's task list.

        Add a task to the mission's task list. Note: this does not submit the
        task to Azure's task queue. It's just add the task to this information
        holder.

        If there's already a task with the same name, an exception is raised.

        Args:
            case [in]: the name of case directory
        """

        if case in self.tasks:
            raise RuntimeError("The case already exists in the task list.")

        self.tasks = numpy.append(self.tasks, case)

    def remove_task(self, case):
        """Remove a task from the mission's task list.

        Remove a task from the mission's task list. Note: this does not remove
        the task from Azure's task queue. It's just remove the task from this
        information holder.

        If there's already a task with the same name, nothing will happen.

        Args:
            case [in]: the name of case directory
        """

        self.tasks = numpy.delete(self.tasks, numpy.where(self.tasks == case))
