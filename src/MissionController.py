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
import os
import sys
import time
import numpy
import datetime
import functools
import azure.batch.models
import azure.storage.blob
import azure.common
from .UserCredential import UserCredential
from .misc import reporthook


class MissionController(object):
    """MissionController"""

    def __init__(self, user_credential, mission_name,
                 n_comp_nodes, vm_type="STANDARD_H16"):
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

        # batch serice, pool, and nodes
        object.__setattr__(self, "batch_client", self.credential.create_batch_client())
        object.__setattr__(self, "pool", None)
        object.__setattr__(self, "nodes", None)

        # blob storage
        object.__setattr__(self, "blob_client", self.credential.create_blob_client())
        object.__setattr__(self, "container_list", numpy.empty(0, dtype=str))
        object.__setattr__(self, "container_token", {})
        object.__setattr__(self, "container_url", {})

        # job, i.e., task manager/scheduler
        object.__setattr__(self, "job_params", None)
        object.__setattr__(self, "job", None)

        object.__setattr__(self, "task_params", {})
        object.__setattr__(self, "tasks", {})

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

    def initialize(self):
        """initialize"""

        self.create_pool()
        self.create_job()

    def finalize(self):
        """finalize"""

        self.delete_job()
        self.delete_all_data()
        self.delete_pool()

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

    def delete_job(self):
        """delete_job"""

        self.batch_client.job.delete(self.job_name)

    def upload_dir(self, dir_path):
        """upload_dir

        Args:
            dir_path [in]: path to the directory
        """

        # get the base name and use it as container name
        dir_path = os.path.abspath(dir_path)
        dir_base_name = os.path.basename(dir_path)
        object.__setattr__(
            self, "container_list",
            numpy.append(self.container_list, [dir_base_name]))

        # create a container
        wait = True
        while wait:
            try:
                self.blob_client.create_container(
                    dir_base_name, fail_on_exist=True)
                wait = False
            except azure.common.AzureConflictHttpError as err:
                if err.error_code == "ContainerAlreadyExists":
                    print("\n    Container {} ".format(dir_base_name) +
                          "already exists. Skip.")
                    wait = False
                elif err.error_code == "ContainerBeingDeleted":
                    print("\n    Old container {} ".format(dir_base_name) +
                          "is being deleted. Will retry later in 10 sec")
                    time.sleep(10)
                else:
                    raise

        print("\n    Container {} ".format(dir_base_name) + "Created.")

        # get the SAS token
        self.container_token[dir_base_name] = \
            self.blob_client.generate_container_shared_access_signature(
                dir_base_name,
                permission=azure.storage.blob.ContainerPermissions(
                    True, True, True, True),
                start=datetime.datetime.utcnow(),
                expiry=datetime.datetime.utcnow()+datetime.timedelta(days=1)
            )

        # get the SAS url
        self.container_url[dir_base_name] = \
            self.blob_client.make_container_url(
                dir_base_name, sas_token=self.container_token[dir_base_name])

        # not sure why there's an extra key in the url
        self.container_url[dir_base_name] = \
            self.container_url[dir_base_name].replace("restype=container&", "")

        # upload files
        for dirpath, dirs, files in os.walk(dir_path):
            for f in files:

                file_path = os.path.join(os.path.abspath(dirpath), f)
                blob_name = os.path.relpath(file_path, os.path.dirname(dir_path))

                self.blob_client.create_blob_from_path(
                    dir_base_name, blob_name, file_path,
                    progress_callback=functools.partial(reporthook, "    Uploading"))
        print("\r    Uploading done.")

    def delete_all_data(self):
        """delete_all_data"""

        for container_name in self.container_list:
            deleted = self.blob_client.delete_container(
                container_name, fail_not_exist=True)

    def create_job(self):
        """create_job"""

        # job parameters
        object.__setattr__(
            self, "job_params",
            azure.batch.models.JobAddParameter(
                id=self.job_name,
                pool_info=azure.batch.models.PoolInformation(
                    pool_id=self.pool_name)))

        # add job
        try:
            self.batch_client.job.add(self.job_params)
        except azure.batch.models.BatchErrorException as err:
            if err.message.value.startswith("The specified job already exists."):
                print("\nJob already exists. Skip.")
            else:
                raise

        # get and assign job information/instance
        object.__setattr__(self, "job", self.batch_client.job.get(self.job_name))

    def add_task(self, case):
        """add_task

        Args:
            case [in]: the name of case directory
        """

        self.upload_dir(case)

        task_container_settings = azure.batch.models.TaskContainerSettings(
            image_name="barbagroup/landspill:applications",
            container_run_options="--rm " + \
                "--workdir /home/landspill/geoclaw-landspill-cases")

        input_data = [azure.batch.models.ResourceFile(
            storage_container_url=self.container_url[case])]

        output_data = [azure.batch.models.OutputFile(
            file_pattern="**/*",
            upload_options=azure.batch.models.OutputFileUploadOptions(
                upload_condition= \
                    azure.batch.models.OutputFileUploadCondition.task_completion),
            destination=azure.batch.models.OutputFileDestination(
                container= \
                    azure.batch.models.OutputFileBlobContainerDestination(
                        container_url=self.container_url[case])))]

        command = "/bin/bash -c \"" + \
            "cp -r $AZ_BATCH_TASK_WORKING_DIR/{} ./ && ".format(case) + \
            "python run.py {} && ".format(case) + \
            "python createnc.py {} && ".format(case) + \
            "cp -r ./{} $AZ_BATCH_TASK_WORKING_DIR".format(case) + \
            "\""
        print(command)

        self.task_params[case] = azure.batch.models.TaskAddParameter(
            id=case,
            command_line=command,
            container_settings=task_container_settings,
            resource_files=input_data,
            output_files=output_data)

        self.batch_client.task.add(self.job_name, self.task_params[case])
        self.tasks[case] = self.batch_client.task.get(self.job_name, case)

    def download_data(self, case):
        """download_data"""

        blob_list = self.blob_client.list_blobs(case)
        for b in blob_list:
            file_abs_path = os.path.abspath(b.name)

            if not os.path.isdir(os.path.dirname(file_abs_path)):
                os.makedirs(os.path.dirname(file_abs_path))

            self.blob_client.get_blob_to_path(
                container_name=case,
                blob_name=b.name,
                file_path=file_abs_path,
                progress_callback=functools.partial(
                    reporthook, "Downloading {}".format(b.name)))
        print()
