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
from .user_credential import UserCredential
from .mission_info import MissionInfo
from .mission_controller import MissionController
from .mission_monitor import MissionMonitor


class Mission:
    """ class represeting a batch of simulation tasks."""

    def __init__(self, user_credential, mission_name, n_nodes_max,
                 tasks, output=sys.stdout, log=True, vm_type="STANDARD_H8",
                 wd="."):
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

        # working directory
        self.wd = os.path.normpath(os.path.abspath(wd))

        # mission controller
        self.controller = MissionController(self.credential, self.info, self.wd)

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
            logfile = os.path.join(self.wd, "{}.log".format(mission_name))
            if os.path.isfile(logfile):
                try:
                    os.remove(logfile)
                except PermissionError:
                    pass

            logging.basicConfig(
                filename=logfile, level=logging.DEBUG,
                format="[%(asctime)s][%(levelname)s][%(filename)s] %(message)s\n")
        else:
            logging.basicConfig(filename=os.devnull)

    def __del__(self):
        """__del__"""

        if self.close_output:
            self.output.close()

        try:
            logger = logging.getLogger()
            logger.handlers[0].close()
            logger.removeHandler(logger.handlers[0])
        except:
            pass

    def __str__(self):
        """__str__"""
        pass

    def _log_info(self, msg, *args):
        """A helper function for logging and printing info."""

        logging.info(msg, *args)

        msg = msg.replace("%s", "{}")
        print(msg.format(*args), file=self.output)

    def start(self, ignore_local_nonexist=True,
              ignore_azure_exist=True, resizing=False):
        """Start the mission."""

        self._log_info("Starting mission %s.", self.info.name)

        self._log_info("Creating/Updating the pool")
        self.controller.create_pool()

        if resizing:
            self._log_info("Resizing the pool")
            self.controller.resize_pool(min(self.max_nodes, len(self.info.tasks)))

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
                    print("Task {} completed. Downloading.".format(task), file=self.output)
                    self.controller.download_dir(task)
                    print("Downloading done.", file=self.output)

                if state == "failed" and task not in self.controller.downloaded:
                    print("Task {} failed. Downloading.".format(task), file=self.output)
                    self.controller.download_dir(task)
                    print("Downloading done.", file=self.output)

            unfinished = task_statistic[0] - task_statistic[2] - task_statistic[3]

            if unfinished == 0:
                break

            if resizing and self.info.n_nodes != min(unfinished, self.max_nodes):
                print("\nResizing the pool.", file=self.output)
                self.controller.resize_pool(min(unfinished, self.max_nodes))

            time.sleep(cycle_time)

    def adapt_size(self):
        """Automatically resize the pool."""

        task_statistic = self.monitor.report_job_task_overview()
        unfinished = task_statistic[0] - task_statistic[2] - task_statistic[3]
        self.controller.resize_pool(min(unfinished, self.max_nodes))

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

    def get_monitor_string(self):
        """Get a string for outputing."""

        import datetime
        s = "\n{}\n".format(str(datetime.datetime.now().replace(microsecond=0)))

        # pool status and node status
        s += "\n\n"
        s += "Pool (cluster) name: {}\n".format(self.info.pool_name)
        s += "Pool status: {0[0]} and {0[1]}\n".format(self.monitor.report_pool_status())

        node_list = self.monitor.report_all_node_status()

        if len(node_list) > 0:
            s += "Node status:\n"

        for node, stat in node_list.items():
            s += "\t{}: {}\n".format(node, stat)

        # job & task status
        s += "\n\n"
        s += "Job (task scheduler) name: {}\n".format(self.info.job_name)
        s += "Job status: {}\n".format(self.monitor.report_job_status())

        task_list = self.monitor.report_all_task_status()

        if len(task_list) > 0:
            s += "Task status:\n"

        for task, stat in task_list.items():
            s += "\t{}: {}\n".format(task, stat)

        # storage container status
        s += "\n\n"
        s += "Storage Blob container name: {}\n".format(self.info.container_name)
        s += "Container status: {}\n".format(self.monitor.report_storage_container_status())

        dir_list = self.monitor.report_storage_container_dirs()

        if len(dir_list) > 0:
            s += "Directories in the container:\n"

        for d, info in dir_list.items():
            s += "\t {}: {}, {}\n".format(d, info[0], info[1])

        return s
