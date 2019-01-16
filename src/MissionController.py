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
from .UserCredential import UserCredential
import azure.batch.models


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

    def create_pool(self):
        """create_pool"""

        # if the pool already on Azure
        if self.batch_client.pool.exists(pool_id=self.pool_name):
            pass # should check is pool is ready

        # otherwise
        else:
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

            # pool setting
            pool_conf = azure.batch.models.PoolAddParameter(
                id=self.pool_name,
                virtual_machine_configuration=vm_conf,
                vm_size=self.vm_type,
                target_dedicated_nodes=self.n_nodes)

            # create the pool
            self.batch_client.pool.add(pool_conf)

        # monitor the creation process and make nodes are created successfully
        self.monitor_pool_creation()

        # get the pool instance
        self.pool = self.batch_client.pool.get(self.pool_name)
        print(self.pool)

    def get_pool(self):
        """get_pool

        Return:
            Pool instance.
        """

        return self.pool

    def monitor_pool_creation(self, time_out=600):
        """monitor_pool_creation

        Args:
            time_out [optional]: time limit for when the creation will abort.
        """

        pass

    def monitor_pool_deletion(self, time_out=600):
        """monitor_pool_deletion

        Args:
            time_out [optional]: time limit for when we should warn users to
                                 manually delete pool from portal.
        """

        pass

    def delete_pool(self):
        """delete_pool"""

        self.batch_client.pool.delete(self.pool_name)

        self.monitor_pool_deletion()
