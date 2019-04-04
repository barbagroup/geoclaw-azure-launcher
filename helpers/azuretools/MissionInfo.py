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
import os
import logging
import pickle
import datetime


class MissionInfo():
    """A class holding information of a mission."""

    def __init__(self, mission_name, n_nodes_max, wd=".",
                 vm_type="STANDARD_H8", read_task_list=True):
        """__init__

        Args:
            mission_name [in]: A str for the name of this mission.
            n_nodes_max [in]: Total number of computing nodes requested.
            wd [in]: working directory. (default: current directory)
            vm_type [optional]: The type of virtual machine. (default: STANDARD_H8)
            read_task_list [optional]: Whether to read task list file or not.
        """

        # logger
        self.logger = logging.getLogger("AzureMission")
        self.logger.debug("Creating a MissionInfo instance.")

        assert isinstance(mission_name, str), "Type error!"
        assert isinstance(n_nodes_max, int), "Type error!"
        assert isinstance(wd, str), "Type error!"
        assert isinstance(vm_type, str), "Type error!"

        # other properties
        self.name = mission_name # the name of this mission
        self.n_max_nodes = n_nodes_max # the number of computing nodes
        self.wd = os.path.normpath(os.path.abspath(wd))
        self.vm_type = vm_type # the type of virtual machines

        self.pool_name = "{}-pool".format(self.name) # pool/cluster name
        self.job_name = "{}-job".format(self.name) # task schduler name
        self.container_name = "{}-container".format(self.name) # storage container name

        # we use one container for one mission, and we initialize the info here
        self.container_token = None
        self.container_url = None

        self.tasks = {}
        self.task_tracker_file = os.path.join(
            self.wd, "{}_task_list.dat".format(self.name))

        if read_task_list:
            self.read_task_list()

        self.logger.info("Done creating a MissionInfo instance.")

    def __str__(self):
        """__str__"""

        s = "Name: {}\n".format(self.name) + \
            "Max. number of nodes: {}\n".format(self.n_max_nodes) + \
            "VM type: {}\n".format(self.vm_type) + \
            "Pool name: {}\n".format(self.pool_name) + \
            "Job (task scheduler) name: {}\n".format(self.job_name) + \
            "Storage container name: {}\n".format(self.container_name) + \
            "Current number of tasks: {}\n".format(len(self.tasks)) + \
            "Task tracker file name: {}\n".format(self.task_tracker_file)

        return s

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
                self.logger.error("%s already exists in MissionInfo. Error!", case_name)
                raise RuntimeError("{} already exists in MissionInfo.".format(case_name))
            else:
                self.logger.debug("%s already exists in MissionInfo. Ignored.", case_name)
        else:
            case_path = os.path.abspath(case_path)
            self.tasks[case_name] = {
                "path": case_path, "parent_path": os.path.dirname(case_path),
                "uploaded": False, "downloaded": False,
                "completed": False, "succeeded": False,
                "last_modified": datetime.datetime.utcnow().replace(
                    tzinfo=datetime.timezone.utc)}

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

        self.logger.debug("Removing a task %s to MissionInfo.", case_name)

        try:
            del self.tasks[case_name]
        except KeyError:
            if not ignore:
                self.logger.error("%s doesn't exists in MissionInfo. Error!", case_name)
                raise RuntimeError("{} doesn't exists in MissionInfo.".format(case_name))
            else:
                self.logger.debug("%s doesn't exists in MissionInfo. Ignored.", case_name)

        self.logger.info("Done removing task %s to MissionInfo.", case)

    def write_task_list(self):
        """Backup task list to a file."""

        self.logger.debug("Writing task list to file %s.", self.task_tracker_file)

        current_utc = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

        with open(self.task_tracker_file, "wb") as f:
            f.write(pickle.dumps([current_utc, self.tasks]))

        self.logger.info("Done writing task list to file %s.", self.task_tracker_file)

    def read_task_list(self):
        """Read task list from a file."""

        self.logger.debug("Reading task list from file %s.", self.task_tracker_file)

        current_utc = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

        with open(self.task_tracker_file, "wb") as f:
            _, self.tasks = pickle.loads(f.read())

        self.logger.info("Done reading task list from file %s.", self.task_tracker_file)
