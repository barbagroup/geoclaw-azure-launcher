#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Pi-Yueh Chuang <pychuang@gwu.edu>
#
# Distributed under terms of the BSD 3-Clause license.

"""
Definition of MissionInfo.
"""
import os
import logging
import pickle
import datetime


class MissionInfo():
    """A class holding information of a mission."""

    def __init__(self, mission_name="", n_nodes_max=0, wd=".",
                 vm_type="STANDARD_H8", node_type="dedicated"):
        """Constructor.

        Args:
            mission_name [in]: A str for the name of this mission.
            n_nodes_max [in]: Total number of computing nodes requested.
            wd [in]: working directory. (default: current directory)
            vm_type [in]: The type of virtual machine. (default: STANDARD_H8)
            node_type [in]: Either "dedicated" (default) or "low-priority".
        """

        # logger
        self.logger = logging.getLogger("AzureMission")
        self.logger.debug("Creating a MissionInfo instance.")

        self.setup(mission_name, n_nodes_max, wd, vm_type, node_type)

        self.logger.info("Done creating a MissionInfo instance.")

    def __str__(self):
        """__str__"""

        s = "Name: {}\n".format(self.name) + \
            "VM type: {}\n".format(self.vm_type) + \
            "Pool name: {}\n".format(self.pool_name) + \
            "Job (task scheduler) name: {}\n".format(self.job_name) + \
            "Storage container name: {}\n".format(self.container_name) + \
            "Storage table name: {}\n".format(self.table_name) + \
            "Current number of tasks: {}\n".format(len(self.tasks)) + \
            "Max. number of nodes: {}\n".format(self.n_max_nodes) + \
            "Auto-scaling formula: {}\n".format(self.auto_scaling_formula) + \
            "Node type: {}\n".format(self.node_type) + \
            "Task tracker file name: {}\n".format(self.backup_file)

        return s

    def setup(self, mission_name="", n_nodes_max=0, wd=".",
              vm_type="STANDARD_H8", node_type="dedicated"):
        """Setup the information of a mission.

        Args:
            mission_name [in]: A str for the name of this mission.
            n_nodes_max [in]: Total number of computing nodes requested.
            wd [in]: working directory. (default: current directory)
            vm_type [in]: The type of virtual machine. (default: STANDARD_H8)
            node_type [in]: Either "dedicated" (default) or "low-priority".
        """

        self.logger.debug("Setting up a MissionInfo instance.")

        assert isinstance(mission_name, str), "Type error!"
        assert isinstance(n_nodes_max, int), "Type error!"
        assert isinstance(wd, str), "Type error!"
        assert isinstance(vm_type, str), "Type error!"

        # other properties
        self.name = mission_name # the name of this mission
        self.n_max_nodes = n_nodes_max # the number of computing nodes
        self.wd = os.path.abspath(wd)
        self.vm_type = vm_type # the type of virtual machines
        self.node_type = node_type # using dedicated or low-priority nodes

        self.pool_name = "{}-pool".format(self.name) # pool/cluster name
        self.job_name = "{}-job".format(self.name) # task schduler name
        self.container_name = "{}-container".format(self.name) # storage container name
        self.table_name = "TABLE" + ''.join(e for e in self.name if e.isalnum())

        # we use one container for one mission, and we initialize the info here
        self.container_token = None
        self.container_url = None

        self.tasks = {}
        self.backup_file = os.path.join(self.wd, "{}_backup_file.dat".format(self.name))

        # a formula for auto-scaling of the pool
        if self.node_type == "dedicated":
            self.auto_scaling_formula = \
                "$NodeDeallocationOption=taskcompletion;\n" + \
                "sampleCounts=$PendingTasks.Count();\n" + \
                "calculated=min({}, $PendingTasks.GetSample(1));\n".format(self.n_max_nodes) + \
                "$TargetLowPriorityNodes=0;\n" + \
                "$TargetDedicatedNodes=(sampleCounts>0)?calculated:{};".format(self.n_max_nodes)

        elif self.node_type == "low-priority":
            self.auto_scaling_formula = \
                "$NodeDeallocationOption=taskcompletion;\n" + \
                "sampleCounts=$PendingTasks.Count();\n" + \
                "calculated=min({}, $PendingTasks.GetSample(1));\n".format(self.n_max_nodes) + \
                "$TargetLowPriorityNodes=(sampleCounts>0)?calculated:{};\n".format(self.n_max_nodes) + \
                "$TargetDedicatedNodes=0;"
        else:
            raise ValueError("node_type should be either dedicated or low-priority")


        self.logger.info("Done setting up a MissionInfo instance.")

    def add_task(self, case_name, case_path, ignore=True):
        """Add a task to the mission's task list.

        Add a task to the mission's task list. Note: this does not submit the
        task to Azure's task queue. It's just add the task to this information
        holder.

        If there's already a task with the same name and ignore is False, an
        exception will be raised.

        Args:
            case_name [in]: the name of the case.
            case_path [in]: the path to the case.
            ignore [optional]: whether to ignore if the task exists in the list
        """

        self.logger.debug("Adding task %s to MissionInfo.", case_name)

        if case_name in self.tasks:
            if not ignore:
                self.logger.error("%s already exists. Error!", case_name)
                raise RuntimeError("{} already exists.".format(case_name))
            else:
                self.logger.debug("%s already exists. Ignored.", case_name)
        else:
            case_path = os.path.abspath(case_path)
            self.tasks[case_name] = {
                "path": case_path, "parent_path": os.path.dirname(case_path),
                "completed": False, "succeeded": False}

        self.logger.info("Done adding task %s to MissionInfo.", case_name)

    def remove_task(self, case_name, ignore=True):
        """Remove a task from the mission's task list.

        Remove a task from the mission's task list. Note: this does not remove
        the task from Azure's task queue. It's just remove the task from this
        information holder.

        If there's not a task with the name in the list and ignore is False, an
        exception will be raised.

        Args:
            case [in]: the name of the case.
            ignore [optional]: whether to ignore if the task doesn't exist in the list
        """

        self.logger.debug("Removing a task %s from MissionInfo.", case_name)

        try:
            del self.tasks[case_name]
        except KeyError:
            if not ignore:
                self.logger.error("%s doesn't exists. Error!", case_name)
                raise RuntimeError("{} doesn't exists.".format(case_name))
            else:
                self.logger.debug("%s doesn't exists. Ignored.", case_name)

        self.logger.info("Done removing task %s from MissionInfo.", case_name)

    def write_mission_info(self):
        """Backup this MissionInfo instance to a file.

        Return:
            The UTC time stamp at when the backup is done.
        """

        self.logger.debug("Writing a MissionInfo to file %s.", self.backup_file)

        current_utc = datetime.datetime.utcnow().replace(
            tzinfo=datetime.timezone.utc)

        with open(self.backup_file, "wb") as f:
            f.write(pickle.dumps([
                current_utc,
                self.name,
                self.n_max_nodes,
                self.auto_scaling_formula,
                self.node_type,
                self.wd,
                self.vm_type,
                self.pool_name,
                self.job_name,
                self.container_name,
                self.table_name,
                self.container_token,
                self.container_url,
                self.tasks,
                self.backup_file
            ]))

        self.logger.info("Done writing the MissionInfo to file %s.", self.backup_file)

        return current_utc

    def read_mission_info(self, filename):
        """Read a MissionInfo instance from a file.

        Args:
            filename [in]: the file where the backup file is located.

        Return:
            The UTC time stamp at when the backup is done.
        """

        self.logger.debug("Reading a MissionInfo from file %s.", self.backup_file)

        with open(filename, "rb") as f:
            data_list = pickle.loads(f.read())

        # assign to each member from data_list
        timestamp, self.name, self.n_max_nodes, self.auto_scaling_formula, \
            self.node_type, self.wd, self.vm_type, \
            self.pool_name, self.job_name, self.container_name, self.table_name, \
            self.container_token, self.container_url, self.tasks, \
            self.backup_file = data_list

        self.logger.info("Done reading the MissionInfo from file %s.", self.backup_file)

        return timestamp
