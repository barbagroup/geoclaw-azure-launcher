#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Pi-Yueh Chuang <pychuang@gwu.edu>
#
# Distributed under terms of the MIT license.

"""
A class represeting a batch of simulations.
"""
import os
import sys
import time
import logging
import numpy
from helpers.azuretools import UserCredential
from helpers.azuretools import MissionInfo
from helpers.azuretools import MissionController
from helpers.azuretools import MissionMonitor


class Mission:
    """ class represeting a batch of simulation tasks."""

    def __init__(self, user_credential, mission_name, n_nodes_max,
                 tasks, output=sys.stdout, log=True, vm_type="STANDARD_H8"):
        """__init__

        Args:
            mission_name [in]: A str for the name of this mission.
            n_nodes_max [in]: Maximum number of computing nodes.
            tasks [in]: A list of task/case directory.
            output [optional]: output file. (default: stdout)
            log [optional]: A boolean whether to log events or not.
            vm_type [optional]: The type of virtual machine. (default: STANDARD_H8)
        """

        assert isinstance(user_credential, UserCredential), "Type error!"
        assert isinstance(mission_name, str), "Type error!"
        assert isinstance(n_nodes_max, (int, numpy.int_)), "Type error!"
        assert isinstance(tasks, (list, numpy.ndarray)), "Type error!"
        assert isinstance(vm_type, str), "Type error!"

        # Azure credential
        self.credential = user_credential

        # initialize mission information
        self.info = MissionInfo(
            mission_name, min(n_nodes_max, len(tasks)), tasks, vm_type)

        # backup the value of n_node_max
        self.max_nodes = n_nodes_max

        # mission controller
        self.controller = MissionController(self.credential, self.info)

        # mission monitor
        self.monitor = MissionMonitor(self.credential, self.info)

        # output file
        if isinstance(output, str):
            self.output = open(output, "w")
            self.close_output = True
        else:
            self.output = output
            self.close_output = False

        # logging
        if log:
            if os.path.isfile("{}.log".format(mission_name)):
                os.remove("{}.log".format(mission_name))
            logging.basicConfig(
                filename="{}.log".format(mission_name), level=logging.DEBUG,
                format="[%(asctime)s][%(levelname)s][%(filename)s] %(message)s\n")
        else:
            logging.basicConfig(filename=os.devnull)

    def __del__(self):
        """__del__"""

        if self.close_output:
            self.output.close()

    def __str__(self):
        """__str__"""
        pass

    def _log_info(self, msg, *args):
        """A helper function for logging and printing info."""

        logging.info(msg, *args)

        msg = msg.replace("%s", "{}")
        print(msg.format(*args), file=self.output)

    def start(self, ignore_local_nonexist=True, ignore_azure_exist=True):
        """Start the mission."""

        self._log_info("Starting mission %s.", self.info.name)

        self._log_info("Creating/Updating the pool")
        self.controller.create_pool()

        self._log_info("Creating/Updating the job")
        self.controller.create_job()

        self._log_info("Creating/Updating the container")
        self.controller.create_storage_container()

        for task in self.info.tasks:
            self.add_task(task, ignore_local_nonexist, ignore_azure_exist)

        self._log_info("Mission %s started.", self.info.name)

    def monitor_wait_download(self, cycle_time=10, resizing=True, download=True):
        """Monitor progress and wait until all tasks done."""

        while True:

            task_states = self.monitor.report_all_task_status()
            task_statistic = self.monitor.report_job_task_overview()
            print(self.monitor.report_mission(), file=self.output)

            for task, state in task_states.items():

                if state == "completed" and task not in self.controller.downloaded:
                    print("Taks {} completed. Downloading.".format(task), file=self.output)
                    self.controller.download_dir(task)
                    print("Downloading done.", file=self.output)

                if state == "failed" and task not in self.controller.downloaded:
                    print("Taks {} failed. Downloading.".format(task), file=self.output)
                    self.controller.download_dir(task)
                    print("Downloading done.", file=self.output)

            unfinished = task_statistic[0] - task_statistic[2] - task_statistic[3]

            if unfinished == 0:
                break

            if resizing and self.info.n_nodes != min(unfinished, self.max_nodes):
                print("\nResizing the pool.", file=self.output)
                self.info.n_nodes = min(self.max_nodes, unfinished)
                self.controller.create_pool()

            time.sleep(cycle_time)

    def clear_resources(self):
        """Delete everything on Azure."""

        print("Delete storagr container.", file=self.output)
        self.controller.delete_storage_container()
        print("Delete job.", file=self.output)
        self.controller.delete_job()
        print("Delete pool.", file=self.output)
        self.controller.delete_pool()

        logging.info("Mission %s completed.", self.info.name)

    def add_task(self, task, ignore_local_nonexist=True, ignore_azure_exist=True):
        """Add additional task to the task scheduler."""

        task_real_name = os.path.basename(os.path.abspath(task))
        task_status = self.monitor.report_task_status(task_real_name)

        # handling cases that the folder does not exist locally
        if not os.path.isdir(os.path.abspath(task)):
            if ignore_local_nonexist:
                self._log_info(
                    "Case folder %s not found. Skip.", os.path.abspath(task))
                return "Local folder not found, Skip"
            else:
                logging.error("Case folder %s not found.", os.path.abspath(task))
                raise FileNotFoundError(
                    "Case folder not found: {}".format(os.path.abspath(task)))

        # local caase folder exists but also exist on Azure
        if task_status != "N/A":
            if ignore_azure_exist:
                self._log_info("Case %s exists on Azure. Skip.", task)
                self.info.add_task(task, True)
                return "Task already exists on Azure. Skip"
            else:
                logging.error("Case %s exists on Azure.", task)
                raise FileExistsError(
                    "Case already exists on Azure: {}".format(task))
        # local case folder exists and does not exist on Azure
        else:
            self._log_info("Adding/Updating task %s", task)
            self.controller.add_task(task, ignore_azure_exist)
            self.info.add_task(task)

        return "Done"
