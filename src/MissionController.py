#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Pi-Yueh Chuang <pychuang@gwu.edu>
#
# Distributed under terms of the MIT license.

"""
A top level controller of the whole mission.
"""
import sys
import time
import numpy
import azure.batch.models
from .UserCredential import UserCredential


class MissionController(object):
    """MissionController"""

    def __init__(self, user_credential, mission_name,
                 n_comp_nodes, vm_type="STANDARD_A1_V2"):
        """__init__

        Args:
            user_credential [in]: An instance of UserCredential.
            mission_name [in]: A str for the name of this mission.
            n_comp_nodes [in]: Total number of computing nodes requested.
            vm_type [optional]: The type of virtual machine. (default: STANDARD_A1_V2)
        """

        assert isinstance(user_credential, UserCredential), "Type error!"

        object.__setattr__(self, "credential", user_credential)
        object.__setattr__(self, "name", mission_name)
        object.__setattr__(self, "n_nodes", n_comp_nodes)
        object.__setattr__(self, "vm_type", vm_type)

        object.__setattr__(self, "pool_name", "{}-pool".format(self.name))
        object.__setattr__(self, "job_name", "{}-job".format(self.name))
        object.__setattr__(self, "std_out", "stdout.txt")

        object.__setattr__(self, "blob_client", self.credential.create_blob_client())
        object.__setattr__(self, "batch_client", self.credential.create_batch_client())

        object.__setattr__(self, "pool", None)
        object.__setattr__(self, "nodes", None)
        object.__setattr__(self, "job", None)
        object.__setattr__(self, "tasks", None)

    def __setattr__(self, name, value):
        """__setattr__

        Prohibit user from setting members explicitly.
        """

        raise AttributeError("Setting attributes is prohibitted")

    def __str__(self):
        """__str__"""

        s = "Name: {}\n".format(self.name) + \
            "Number of nodes: {}\n".format(self.n_nodes) + \
            "VM type: {}\n".format(self.vm_type)

        return s

    def get_pool(self):
        """get_pool

        Return:
            Pool instance.
        """

        return self.pool

    def get_node_list(self):
        """get_node_list"""

        return self.nodes

    def create_pool(self):
        """create_pool"""

        # if the batch client is not aware of this pool
        if not self.batch_client.pool.exists(pool_id=self.pool_name):

            # image
            image = azure.batch.models.ImageReference(
                publisher="microsoft-azure-batch",
                offer="ubuntu-server-container",
                sku="16-04-lts",
                version="latest")

            # prefetched Docker image
            container_conf = azure.batch.models.ContainerConfiguration(
                container_image_names=['barbagroup/landspill:applications'])

            # vm setting
            vm_conf = azure.batch.models.VirtualMachineConfiguration(
                image_reference=image,
                container_configuration=container_conf,
                node_agent_sku_id="batch.node.ubuntu 16.04")

            # start task configuration
            start_task = azure.batch.models.StartTask(
                command_line="/bin/bash -c echo $PWD && docker image list && echo $AZ_BATCH_NODE_ROOT_DIR",
                wait_for_success=True)

            # pool setting
            pool_conf = azure.batch.models.PoolAddParameter(
                id=self.pool_name,
                virtual_machine_configuration=vm_conf,
                vm_size=self.vm_type,
                target_dedicated_nodes=self.n_nodes,
                start_task=start_task)

            # create the pool
            self.batch_client.pool.add(pool_conf)

        # get and assign the pool instance
        object.__setattr__(self, "pool", self.batch_client.pool.get(self.pool_name))

        # monitor the creation process and make nodes are created successfully
        self.monitor_pool_creation()

    def monitor_pool_creation(self, time_out=900, output=sys.stdout):
        """monitor_pool_creation

        Args:
            time_out [optional]: time limit for when the creation will abort.
        """

        # aliases for shorter code
        pool_steady = azure.batch.models.AllocationState.steady
        node_idle = azure.batch.models.ComputeNodeState.idle

        # initialize timer and output line length
        T = 0
        prev_text_len = 0

        # monitor pool creation
        while self.pool.allocation_state is not pool_steady:

            # time out
            if T > time_out:
                print("\nERROR: POOL CREATION TIMEOUT. " +
                      "Deletion was hence issued. Now deleting.", file=sys.stderr)

                self.delete_pool()

                raise TimeoutError(
                    "\nPool creation timeout. Deletion was hence issued. " +
                    "But still, please check the status of the " +
                    "pool {} manually from Azure portal.".format(self.pool_name))

            # output creation status
            print("\r"+prev_text_len*" ", end='', file=output)
            text = 4 * " " + "Pool {} status: ".format(self.pool_name) + \
                "{} ".format(self.pool.allocation_state.name) + \
                "{}".format(int(T%5)*'.')
            print("\r"+text, end='', file=output)
            prev_text_len = len(text)
            sys.stdout.flush()
            T += 1
            time.sleep(1)

            # refresh the pool instance
            object.__setattr__(
                self, "pool", self.batch_client.pool.get(self.pool_name))

        # now the poll is ready, move stdout to next line
        text = 4 * " " + "Pool {} status: ".format(self.pool_name) + \
            "{} ".format(self.pool.allocation_state.name)
        print("\r"+prev_text_len*" ", end='', file=output)
        print("\r"+text, file=output)
        prev_text_len = len(text)
        sys.stdout.flush()

        # check node creations
        hold = True
        while hold:

            # time out
            if T > time_out:
                print("\nERROR: NODE CREATION TIMEOUT. " +
                      "Pool deletion was hence issued. Now deleting.", file=sys.stderr)

                self.delete_pool()

                raise TimeoutError(
                    "\nNode creation timeout. Pool deletion was hence issued. " +
                    "But still, please check the status of the " +
                    "pool {} manually from Azure portal.".format(self.pool_name))

            # get the node list instance
            object.__setattr__(
                self, "nodes", self.batch_client.compute_node.list(self.pool_name))

            # status of all nodes
            self.nodes.reset() # reset iterator
            node_ready = numpy.array([n.state is node_idle for n in self.nodes])

            # str for status
            self.nodes.reset() # reset iterator
            stats_str = numpy.array([n.state.name for n in self.nodes])

            if numpy.all(node_ready):
                hold = False
            else:
                text = 8 * ' ' + "Node status: " + \
                    "{} ".format(stats_str) + "{}".format(int(T%5)*'.')
                print("\r"+prev_text_len*" ", end='', file=output)
                print("\r"+text, end='', file=output)
                prev_text_len = len(text)
                sys.stdout.flush()
                T += 1
                time.sleep(1)

        # now all nodes are ready, move stdout to next line
        print("\r"+prev_text_len*" ", end='', file=output)
        print("\r        Node status: all ready", file=output)
        print("    Pool creation successed.", file=output)

    def monitor_pool_deletion(self, time_out=900, output=sys.stdout):
        """monitor_pool_deletion

        Args:
            time_out [optional]: time limit for when we should warn users to
                                 manually delete pool from portal.
        """

        # initialize timer and prev_text_len
        T = 0
        prev_text_len = 0

        # if the pool still exists
        while self.batch_client.pool.exists(pool_id=self.pool_name):

            # time out
            if T > time_out:
                raise TimeoutError(
                    "\nPool deletion timeout. Please check the status of the " +
                    "pool {} manually from Azure portal.".format(self.pool_name))

            # output deletion status
            print("\r"+prev_text_len*" ", end='', file=output)
            text = 4 * " " + "Pool {} status: ".format(self.pool_name) + \
                  "{} ".format(self.pool.allocation_state.name) + \
                  "{}".format(int(T%5)*'.')
            print("\r"+text, end='', file=output)
            prev_text_len = len(text)

            sys.stdout.flush()
            T += 1
            time.sleep(1)

        print("\n    Pool deletion successed.", file=output)

    def delete_pool(self):
        """delete_pool"""

        if self.batch_client.pool.exists(pool_id=self.pool_name):
            self.batch_client.pool.delete(self.pool_name)

        self.monitor_pool_deletion()
