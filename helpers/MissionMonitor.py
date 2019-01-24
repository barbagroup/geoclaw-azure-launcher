#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Pi-Yueh Chuang <pychuang@gwu.edu>
#
# Distributed under terms of the MIT license.

"""
A class to monitor the status/progress of a mission.
"""
import datetime
import azure.batch
import azure.storage.blob
from helpers import UserCredential
from helpers import MissionInfo


class MissionMonitor():
    """MissionMonitor"""

    def __init__(self, user_credential, mission_info):
        """__init__"""

        assert isinstance(user_credential, UserCredential), "Type error!"
        assert isinstance(mission_info, MissionInfo), "Type error!"

        # alias/pointer to the UserCredential object
        self.credential = user_credential

        # alias/pointer to mission info
        self.info = mission_info

        # Batch service client
        self.batch_client = self.credential.create_batch_client()

        # Storage service client
        self.storage_client = self.credential.create_blob_client()

    def report_pool_status(self):
        """Report the current status of the pool.

        Return:
            Return type is of [str, str]. Possible values for the first string
            are: not_exist, active, and deleting. Possible values for the second
            string are: N/A, steady, resizing, and stopping.
        """

        if not self.batch_client.pool.exists(pool_id=self.info.pool_name):
            return "not_exist", "N/A"

        # get pool info
        the_pool = self.batch_client.pool.get(pool_id=self.info.pool_name)
        state = the_pool.state.name
        allocation_state = the_pool.allocation_state.name

        return state, allocation_state

    def report_all_node_status(self):
        """Report the status of all nodes.

        Return:
            A dictionary in which the keys are node names and the values are
            states of the node. Possible values of states include: 'idle',
            'rebooting', 'reimaging', 'running', 'unusable', 'creating',
            'starting', 'waitingForStartTask', 'startTaskFailed', 'unknown',
            'leavingPool', 'offline', and 'preempted'
        """

        node_list = self.batch_client.compute_node.list(
            pool_id=self.info.pool_name)

        states = {}
        for node in node_list:
            states[node.id] = node.state.name
        node_list.reset()

        return states

    def report_node_overview(self):
        """Report an overview of ths status of the nodes.

        Return:
            A list of integers with a length of 5, which means:
                [total, running, idle, error, other]
        """

        node_states = list(self.report_all_node_status().values())

        total = len(node_states)
        running = node_states.count("running")
        idle = node_states.count("idle")
        error = node_states.count("unusable") + node_states.count("startTaskFailed")
        other = total - running - idle - error

        return total, running, idle, error, other

    def report_job_status(self):
        """Report the current status of the job (task scheduler).

        Return:
            The type of return is a str. Possible values are: active, completed,
            deleting, disabled, disabling, enabling, and terminating.
        """

        try:
            the_job = self.batch_client.job.get(job_id=self.info.job_name)
        except azure.batch.models.BatchErrorException as err:
            if err.message.value.startswith("The specified job does not exist"):
                return "not_exist"
            else:
                raise

        return the_job.state.name

    def report_task_status(self, task_name):
        """Report the status of a single task.

        Return:
            The return type is a str. Possible values are: active, preparing,
            running, failed, and completed.
        """

        try:
            the_task = self.batch_client.task.get(
                job_id=self.info.job_name, task_id=task_name)
        except azure.batch.models.BatchErrorException as err:
            if err.message.value.startswith("The specified job does not exist"):
                return "not_exist"
            if err.message.value.startswith("The specified task does not exist"):
                return "not_exist"
            else:
                raise

        if the_task.state is azure.batch.models.TaskState.completed:
            if the_task.execution_info.failure_info is not None:
                return "failed"

        return the_task.state.name

    def report_all_task_status(self):
        """Report the status of all tasks in the misson job.

        Return:
            A dictionary with keys to be the case names and values to be the
            states.
        """

        try:
            task_list = self.batch_client.task.list(job_id=self.info.job_name)
        except azure.batch.models.BatchErrorException as err:
            if err.message.value.startswith("The specified job does not exist"):
                return {}
            else:
                raise

        task_states = {}
        for task in task_list:

            task_states[task.id] = task.state.name

            # if the task completed but failed, modifued the status
            if task.state is azure.batch.models.TaskState.completed:
                if task.execution_info.failure_info is not None:
                    task_states[task.id] = "failed"

        task_list.reset()

        return task_states

    def report_job_task_overview(self):
        """Report an overview of tasks.

        Return:
            A list of integers with a length of 4. The format is:
                [total tasks, running tasks, completed tasks, failed tasks]
        """

        task_states = list(self.report_all_task_status().values())

        total = len(task_states)
        running = task_states.count("running")
        completed = task_states.count("completed")
        failed = task_states.count("failed")

        return total, running, completed, failed

    def report_storage_container_status(self):
        """Report the status of the mission storage container.

        Return:
            A string. Possible values: available and not_exist.
        """

        if self.storage_client.exists(container_name=self.info.container_name):
            return "available"

        return "not_exist"

    def report_storage_container_dirs(self):
        """Report info of the top-level directories in the mission container.

        Return:
            A dictionary reporting folder name, size (MB), and the last modified
            time for the folder. In other words:
                {folder name: [size, last modified time]}
        """

        if not self.storage_client.exists(container_name=self.info.container_name):
            return {}

        blob_list = self.storage_client.list_blobs(
            container_name=self.info.container_name,
            num_results=50000, delimiter="/")

        dirs = {}
        for blob in blob_list:
            if not blob.name.endswith("/"):
                continue
            dirs[blob.name[:-1]] = [None, None]

        for key in dirs.keys():

            last_modified_time = datetime.datetime(
                datetime.MINYEAR, 1, 1, tzinfo=datetime.timezone.utc)

            size = 0

            dir_blob_list = self.storage_client.list_blobs(
                container_name=self.info.container_name,
                num_results=50000,
                prefix="{}/".format(key))

            for blob in dir_blob_list:
                size += blob.properties.content_length
                modified_time = blob.properties.last_modified

                if blob.properties.last_modified > last_modified_time:
                    last_modified_time = blob.properties.last_modified

            dirs[key] = [round(size/1024/1024, 1), last_modified_time]

        return dirs

    def report_storage_container_dirs_overview(self):
        """Report an overview regarding directories in the container.

        Return:
            [number of dirs, total size (in MB), last_modified]
        """

        dirs = self.report_storage_container_dirs()

        n_dirs = len(dirs)
        total_size = 0
        last_modified = datetime.datetime(
            datetime.MINYEAR, 1, 1, tzinfo=datetime.timezone.utc)

        for value in dirs.values():
            total_size += value[0]
            if value[1] > last_modified:
                last_modified = value[1]

        if last_modified == datetime.datetime(
                datetime.MINYEAR, 1, 1, tzinfo=datetime.timezone.utc):
            last_modified = "N/A"

        return n_dirs, total_size, last_modified

    def report_mission(self):
        """Report the status of the whole mission.

        Return:
            A string for printing out on stdout.
        """

        s = "Report time (UTC): {}\n".format(
            datetime.datetime.utcnow().replace(
                tzinfo=datetime.timezone.utc, microsecond=0))

        s += "Pool status: {0[0]} and {0[1]}\n".format(self.report_pool_status())

        node_info = self.report_node_overview()
        s += "Node overview: " + \
            "{0[0]} total, {0[1]} running, ".format(node_info) + \
            "{0[2]} idle, {0[3]} error, {0[4]} other\n".format(node_info)

        s += "Job status: {}\n".format(self.report_job_status())

        task_info = self.report_job_task_overview()
        s += "Task overview: " + \
            "{0[0]} total, {0[1]} running, ".format(task_info) +\
            "{0[2]} completed, {0[3]} failed\n".format(task_info)

        s += "Storage container status: {}\n".format(
            self.report_storage_container_status())

        container_info = self.report_storage_container_dirs_overview()
        s += "Storage container overview: " + \
            "{0[0]} dirs, size {0[1]} MB, ".format(container_info) + \
            "last modified at {0[2]}\n".format(container_info)

        return s

