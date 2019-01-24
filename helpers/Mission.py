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
from helpers import UserCredential
from helpers import MissionInfo
from helpers import MissionController
from helpers import MissionMonitor


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

    def start(self):
        """Start the mission."""

        logging.info("Starting mission %s.", self.info.name)

        print("Creating/Updating the pool", file=self.output)
        self.controller.create_pool()
        print("Creating/Updating the job", file=self.output)
        self.controller.create_job()
        print("Creating/Updating the container", file=self.output)
        self.controller.create_storage_container()

        for task in self.info.tasks:
            task_real_name = os.path.basename(os.path.abspath(task))
            task_status = self.monitor.report_task_status(task_real_name)

            if task_status == "N/A":
                print("Adding/Updating task {}".format(task), file=self.output)
                self.controller.add_task(task)
            else:
                print("Task {} exist. Skip.".format(task), file=self.output)

        logging.info("Mission %s started.", self.info.name)

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

            unfinished = task_statistic[0] - task_statistic[2]

            if unfinished == 0:
                break

            if resizing and unfinished < self.info.n_nodes:
                print("\nResizing the pool.", file=self.output)
                self.info.n_nodes = unfinished
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
