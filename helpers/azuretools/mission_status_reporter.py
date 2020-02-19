#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
########################################################################################################################
# Copyright © 2019-2020 Pi-Yueh Chuang and Lorena A. Barba
# All Rights Reserved.
#
# Contributors: Pi-Yueh Chuang <pychuang@gwu.edu>
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
An object to obtain status of resources of a mission.
"""
import datetime
import azure.batch


class MissionStatusReporter():
    """An object to obtain status of resources of a mission. """

    def __init__(self, credential=None):
        """Constructor."""

        # azure service clients
        self.batch_client = credential.create_batch_client()
        self.storage_client = credential.create_blob_client()
        self.table_client = credential.create_table_client()

    def get_pool_status(self, mission):
        """Get the current status of the pool.

        Args:
            mission [in]: an MissionInfo object.

        Return:
            Return type is of [str, str, dict], which represents pool status,
            the status of allocating computing nodes, and the numbers of nodes
            in each status. Possible values for the first string are: N/A,
            active, and deleting. Possible values for the second string are:
            N/A, steady, resizing, and stopping.

            For the returned dict, the keys are node status and the values are
            the number of nodes in this status. Possible values of statuses
            include: 'idle', 'rebooting', 'reimaging', 'running', 'unusable',
            'creating', 'starting', 'waiting_for_start_task', 'start_task_failed',
            'unknown', 'leaving_pool', 'offline', and 'preempted'
        """

        # initialize node status
        states = dict(
            idle=0, rebooting=0, reimaging=0, running=0, unusable=0, creating=0,
            starting=0, waiting_for_start_task=0, start_task_failed=0, unknown=0,
            leaving_pool=0, offline=0, preempted=0)

        # if the pool does not exist
        if not self.batch_client.pool.exists(pool_id=mission.pool_name):
            return "N/A", "N/A", states

        # get pool info
        the_pool = self.batch_client.pool.get(pool_id=mission.pool_name)
        state = the_pool.state.name
        allocation_state = the_pool.allocation_state.name

        # get the list of node at current time point
        # we check the existance of the pool again to avoid coincidence
        if self.batch_client.pool.exists(pool_id=mission.pool_name):
            node_list = self.batch_client.compute_node.list(
                pool_id=mission.pool_name)

            # calculate the number of nodes in each status
            for node in node_list:
                states[node.state.name] += 1
            node_list.reset()

        return state, allocation_state, states

    def get_pool_overview_string(self, mission):
        """Get a string for the status overview of the pool and nodes.

        Args:
            mission [in]: an MissionInfo object.

        Return:
            A string of format:

            Pool status: {}
            Allocation status: {}
            Node status: {} idle; {} running; {} unusable; {} other
        """

        # get statuses
        pool_status, allocation_status, node_status = self.get_pool_status(mission)

        s = "Pool status: {}\n".format(pool_status)
        s += "Allocation status: {}".format(allocation_status)

        if pool_status != "N/A":

            other = sum(node_status.values()) - node_status["idle"] - \
                node_status["running"] - node_status["unusable"]

            s += "\n"
            s += "Node status: "
            s += "{} idle; ".format(node_status["idle"])
            s += "{} running; ".format(node_status["running"])
            s += "{} unusable; ".format(node_status["unusable"])
            s += "{} other;".format(other)

        return s

    def get_job_status(self, mission):
        """Get the current status of the job (task scheduler) and tasks.

        Args:
            mission [in]: an MissionInfo object.

        Return:
            The type of return is a [str, dict], which represents the status of
            the job (i.e., the task scheduler) and the numbers of tasks in each
            status. Possible values for job status are: 'N/A', 'active',
            'completed', 'deleting', 'disabled', 'disabling', 'enabling', and
            'terminating'. For the return dict, the keys are: "active",
            "running", "succeeded", and "failed". The values of the dict are
            the numbers of tasks in those statuses.
        """

        # initialize task status
        status = dict(active=0, running=0, succeeded=0, failed=0)

        # get job status if it exists. Otherwise, return N/A
        try:
            the_job = self.batch_client.job.get(job_id=mission.job_name)

            # get counts of tasks in different statuses
            status_counts = self.batch_client.job.get_task_counts(mission.job_name)
        except azure.batch.models.BatchErrorException as err:
            if err.message.value.startswith("The specified job does not exist"):
                return "N/A", status
            # raise an exception for other kinds of errors
            raise

        # update the dictionary
        status["active"] = status_counts.active
        status["running"] = status_counts.running
        status["succeeded"] = status_counts.succeeded
        status["failed"] = status_counts.failed

        return the_job.state.name, status

    def get_job_overview_string(self, mission):
        """Get a string for the status overview of the job and tasks.

        Args:
            mission [in]: an MissionInfo object.

        Return:
            A string of format:

            Job status: {}
            Tasks status: {} active; {} running; {} succeeded; {} failed
        """

        # get statuses
        job_status, task_status = self.get_job_status(mission)

        s = "Job status: {}".format(job_status)

        if job_status != "N/A":
            s += "\n"
            s += "Tasks status: "
            s += "{} active; ".format(task_status["active"])
            s += "{} running; ".format(task_status["running"])
            s += "{} succeeded; ".format(task_status["succeeded"])
            s += "{} failed;".format(task_status["failed"])

        return s

    def get_storage_container_status(self, mission):
        """Get the status of a mission's storage container.

        Args:
            mission [in]: an MissionInfo object.

        Return:
            A string. Possible values: available and N/A.
        """

        if self.storage_client.exists(container_name=mission.container_name):
            return "available"

        # TODO: calculate space used in the container

        return "N/A"

    def get_storage_container_overview_string(self, mission):
        """Get a string for the status of the storage container.

        Args:
            mission [in]: an MissionInfo object.

        Return:
            A string of format: Storage container status: {}.
        """

        status = self.get_storage_container_status(mission)
        s = "Storage container status: {}".format(status)
        return s

    def get_overview_string(self, mission):
        """Get the string of an overview to all resources.

        Args:
            mission [in]: an MissionInfo object.

        Return:
            A string with format:

            Pool status: {}
            Allocation status: {}
            Node status: {} idle; {} running; {} unusable; {} other

            Job status: {}
            Tasks status: {} active; {} running; {} succeeded; {} failed

            Storage container status: {}.
        """

        s = self.get_pool_overview_string(mission) + "\n\n"
        s += self.get_job_overview_string(mission) + "\n\n"
        s += self.get_storage_container_overview_string(mission)

        return s

    def status_generator(self, mission):
        """A generator that can be used in a loop.

        Args:
            mission [in]: an MissionInfo object.

        Yield:
            [pool status, allocation status, node status, job status,
            task status, storage container status]
        """

        while True:
            status = {}

            status["timestamp"] = datetime.datetime.utcnow().replace(
                microsecond=0, tzinfo=datetime.timezone.utc).strftime(
                    "%a %b %d %H:%M:%S %Z %Y")

            status["pool_status"], status["allocation_status"], \
                status["node_status"] = self.get_pool_status(mission)

            status["job_status"], status["task_status"] = \
                self.get_job_status(mission)

            status["storage_status"] = \
                self.get_storage_container_status(mission)

            yield status
