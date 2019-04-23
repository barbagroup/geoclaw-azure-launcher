#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Pi-Yueh Chuang <pychuang@gwu.edu>
#
# Distributed under terms of the BSD 3-Clause license.

"""
A controller for the mission (i.e., object that can issue commands to Azure).
"""
import os
import time
import datetime
import logging
import base64
import azure.batch.models
import azure.storage.blob
import azure.common
from .user_credential import UserCredential
from .mission_info import MissionInfo
from .misc import path_ignored


class MissionController():
    """MissionController"""

    def __init__(self, credential):
        """__init__

        Args:
            credential [in]: An instance of UserCredential.
        """

        # logger
        self.logger = logging.getLogger("AzureMission")
        self.logger.debug("Creating a MissionController instance.")

        assert isinstance(credential, UserCredential), "Type error!"

        # Batch and Storage service clients
        self.batch_client = credential.create_batch_client()
        self.storage_client = credential.create_blob_client()
        self.table_client = credential.create_table_client()

        self.logger.info("Done creating a MissionController instance.")

    def create_storage_container(self, mission):
        """Create a blob container for a mission.

        Args:
            mission [in]: an MissionInfo object.
        """

        self.logger.debug("Creating container %s", mission.container_name)

        assert isinstance(mission, MissionInfo), "Type error!"

        # alias to mission.container_name
        container_name = mission.container_name

        # a sub-function that retries to create container
        def retry_creation():
            created = False
            counter = 0
            while not created:
                counter += 1
                if counter > 120:
                    self.logger.error("Creating container %s timeout.", container_name)
                    raise RuntimeError(
                        "The container %s has been undergoing deletion for "
                        "over 600 seconds. Please manually check the status.")

                self.logger.debug("%s is being deleted. Retrying.", container_name)

                time.sleep(5)
                created = self.storage_client.create_container(
                    container_name=container_name, fail_on_exist=False)

        try:
            # create a container
            self.storage_client.create_container(
                container_name=container_name, fail_on_exist=True)

        # if something wrong when creating the container
        except azure.common.AzureConflictHttpError as err:

            # if the container already exists on Azure Storage
            if err.error_code == "ContainerAlreadyExists":
                self.logger.debug("%s already exists. Skip.", container_name)

            # if the container exists but is being deleted
            elif err.error_code == "ContainerBeingDeleted":
                retry_creation()

            else:
                raise

        self.logger.info("Done creating container %s", container_name)

        # create an auxiliary storage table to store syncronization metadata
        self.logger.debug("Creating aux table for %s", mission.container_name)
        self.table_client.create_table(mission.table_name)
        self.logger.info("Done creating aux table for %s", mission.container_name)

    def delete_storage_container(self, mission):
        """Delete the storage container of a mission.

        Args:
            mission [in]: an MissionInfo object.
        """

        self.logger.debug("Deleting container %s", mission.container_name)

        assert isinstance(mission, MissionInfo), "Type error!"

        try:
            self.storage_client.delete_container(
                container_name=mission.container_name, fail_not_exist=True)
        except azure.common.AzureMissingResourceHttpError as err:
            if err.error_code == "ContainerNotFound":
                self.logger.debug("Container does not exist. SKIP deletion.")
            else:
                raise

        self.logger.info(
            "Deletion command issued to container %s.", mission.container_name)

        # delete the auxiliary storage table
        self.logger.debug("Deleting aux table for %s", mission.container_name)
        self.table_client.delete_table(mission.table_name)
        self.logger.info("Done deleting aux table for %s", mission.container_name)

    def get_storage_container_access_tokens(self, mission):
        """Get container URL and SAS token.

        Args:
            mission [in]: an MissionInfo object.
        """

        self.logger.debug("Requesting container SAS tokens.")

        assert isinstance(mission, MissionInfo), "Type error!"

        # use current time as the sharing start time
        current_utc_time = \
            datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

        # get the SAS token
        mission.container_token = \
            self.storage_client.generate_container_shared_access_signature(
                container_name=mission.container_name,
                permission=azure.storage.blob.ContainerPermissions(
                    True, True, True, True),
                start=current_utc_time,
                expiry=current_utc_time+datetime.timedelta(days=30))

        # get the SAS url
        mission.container_url = self.storage_client.make_container_url(
            container_name=mission.container_name,
            sas_token=mission.container_token)

        # not sure why there's an extra key in the url. Need to remove it.
        mission.container_url = \
            mission.container_url.replace("restype=container&", "")

        self.logger.info("Container SAS tokens obtained.")

    def create_pool(self, mission):
        """Create a pool on Azure based on the mission info.

        Args:
            mission [in]: an MissionInfo object.
        """

        self.logger.debug("Creating pool %s", mission.pool_name)

        assert isinstance(mission, MissionInfo), "Type error!"

        # if the pool already exists (it does not mean it's ready)
        if self.batch_client.pool.exists(pool_id=mission.pool_name):
            self.logger.info(
                "Pool %s already exists. Skip creation.", mission.pool_name)
            return

        # if the batch client is not aware of this pool
        self.logger.debug("Issuing command to create pool %s.", mission.pool_name)

        # image
        image = azure.batch.models.ImageReference(
            publisher="microsoft-azure-batch",
            offer="ubuntu-server-container",
            sku="16-04-lts",
            version="latest")

        # prefetched Docker image
        container_conf = azure.batch.models.ContainerConfiguration(
            container_image_names=['barbagroup/landspill:bionic'])

        # vm setting
        vm_conf = azure.batch.models.VirtualMachineConfiguration(
            image_reference=image,
            container_configuration=container_conf,
            node_agent_sku_id="batch.node.ubuntu 16.04")

        # task scheduling setting
        task_scheduling_conf = azure.batch.models.TaskSchedulingPolicy(
            node_fill_type="spread")

        # pool setting
        pool_conf = azure.batch.models.PoolAddParameter(
            id=mission.pool_name,
            display_name=mission.pool_name,
            vm_size=mission.vm_type,
            virtual_machine_configuration=vm_conf,
            enable_auto_scale=True,
            auto_scale_formula=mission.auto_scaling_formula,
            auto_scale_evaluation_interval=datetime.timedelta(minutes=5),
            enable_inter_node_communication=False,
            max_tasks_per_node=1,
            task_scheduling_policy=task_scheduling_conf)

        # create the pool
        self.batch_client.pool.add(pool_conf)

        self.logger.info("Creation command issued.")

    def resize_pool(self, mission, n_nodes):
        """Manually resize the pool.

        Currently this function is not working because we use auto-scaling.
        Manual resizing is not allowed when auto-scaling is enabled. So using
        this function will raise an error coming from Azure.

        Args:
            mission [in]: an MissionInfo object.
            n_nodes [in]: target number of nodes.
        """

        self.logger.debug("Resizing pool %s", mission.pool_name)

        assert isinstance(mission, MissionInfo), "Type error!"

        # if the pool already exists (it does not mean it's ready)
        if not self.batch_client.pool.exists(pool_id=mission.pool_name):
            self.logger.error("Pool %s not exist.", mission.pool_name)
            raise RuntimeError("Pool {} not exist.".format(mission.pool_name))

        # get the number of nodes in the pool on Azure
        pool_info = self.batch_client.pool.get(mission.pool_name)

        self.logger.debug("Issuing a command to resize pool %s.", mission.pool_name)

        # an alias for shorter code
        pool_resizing = azure.batch.models.AllocationState.resizing
        pool_steady = azure.batch.models.AllocationState.steady

        # if the pool is under resizing, stop the resizing first
        if pool_info.allocation_state is pool_resizing:
            self.batch_client.pool.stop_resize(mission.pool_name)

            while pool_info.allocation_state is not pool_steady:
                time.sleep(2) # wait for 2 seconds
                # get updated information of the pool
                pool_info = self.batch_client.pool.get(mission.pool_name)

        # calculate actual nodes that are going to be allocated
        dln = tln = 0
        if mission.node_type == "dedicate":
            dln = min(n_nodes, mission.n_max_nodes)
        else:
            tln = min(n_nodes, mission.n_max_nodes)

        # now resizing
        self.batch_client.pool.resize(
            pool_id=mission.pool_name,
            pool_resize_parameter=azure.batch.models.PoolResizeParameter(
                target_dedicated_nodes=dln,
                target_low_priority_nodes=tln,
                node_deallocation_option="requeue"))

        self.logger.info("Issued a command to resize pool %s.", mission.pool_name)

    def delete_pool(self, mission):
        """Delete a pool on Azure based on the content set in self.

        Args:
            mission [in]: an MissionInfo object.
        """

        self.logger.debug("Deleting pool %s", mission.pool_name)

        assert isinstance(mission, MissionInfo), "Type error!"

        # if the pool exists, issue a delete command
        if self.batch_client.pool.exists(pool_id=mission.pool_name):
            self.batch_client.pool.delete(mission.pool_name)
            self.logger.info("Deletion command issued to pool %s.", mission.pool_name)
        else:
            self.logger.info(
                "Pool %s not exist. Skip deletion.", mission.pool_name)

    def create_job(self, mission):
        """Create a job (i.e. task scheduler) for this mission.

        Args:
            mission [in]: an MissionInfo object.
        """

        self.logger.debug("Creating job %s", mission.job_name)

        assert isinstance(mission, MissionInfo), "Type error!"

        # job parameters
        job_params = azure.batch.models.JobAddParameter(
            id=mission.job_name,
            display_name=mission.name,
            pool_info=azure.batch.models.PoolInformation(
                pool_id=mission.pool_name))

        # add job
        try:
            self.batch_client.job.add(job_params)
            self.logger.info("Issued a command to create job %s", mission.job_name)
        except azure.batch.models.BatchErrorException as err:
            if err.message.value.startswith("The specified job already exists."):
                self.logger.info("Job already exists. SKIP creation.")
            else:
                raise

    def delete_job(self, mission):
        """Delete a job (i.e. task scheduler).

        Args:
            mission [in]: an MissionInfo object.
        """

        self.logger.debug("Deleting job %s", mission.job_name)

        assert isinstance(mission, MissionInfo), "Type error!"

        try:
            self.batch_client.job.delete(mission.job_name)
            self.logger.info("Issued a command to delete job %s", mission.job_name)
        except azure.batch.models.BatchErrorException as err:
            if err.message.value.startswith("The specified job does not exist."):
                self.logger.info("Job does not exist. SKIP deletion.")
            else:
                raise

    def compare_timestamp(self, mission, blobpath, filepath):
        """Compare the timestamp of the local file and cloud file.

        Args:
            mission [in]: an MissionInfo object.
            blobpath [in]: relative path to the Blob root on Azure.
            filename [in]: path to the file on a local machine.

        Return:
            0: equal timestamp (including both non-exists)
            1: local file is newer (including cloud file non-exists)
            2: cloud file is newer (including local file non-exists)
        """

        self.logger.debug("Comparing file %s and blob %s", filepath, blobpath)

        assert isinstance(mission, MissionInfo), "Type error!"
        assert isinstance(blobpath, str), "Type error!"
        assert isinstance(filepath, str), "Type error!"

        local_mtime = datetime.datetime(
            datetime.MINYEAR, 1, 1, tzinfo=datetime.timezone.utc)
        cloud_mtime = datetime.datetime(
            datetime.MINYEAR, 1, 1, tzinfo=datetime.timezone.utc)

        # dealing with local file
        if os.path.isfile(filepath):
            local_mtime = datetime.datetime.utcfromtimestamp(
                os.path.getmtime(filepath)).replace(
                    microsecond=0, tzinfo=datetime.timezone.utc)

        # dealing with cloud file
        blobkey = base64.urlsafe_b64encode(blobpath.encode()).decode()
        try:
            entity = self.table_client.get_entity(
                mission.table_name, "blobfiles", blobkey)
        except azure.common.AzureMissingResourceHttpError:
            entity = None

        try:
            blob_props = self.storage_client.get_blob_properties(
                mission.container_name, blobpath).properties
        except azure.common.AzureMissingResourceHttpError:
            blob_props = None

        # error case
        if entity is not None and blob_props is None:
            raise RuntimeError(
                "Blob file {} does not exist ".format(blobpath) +
                "in container %s, ".format(mission.container_name) +
                "but its record can be found in " +
                "table {}.".format(mission.table_name))

        # both exist; calculate time delta and add to a base time
        if entity is not None and blob_props is not None:

            # check if the record match
            if entity["local_path"] != os.path.abspath(filepath):
                raise RuntimeError(
                    "{} does not match the ".format(os.path.abspath(filepath)) +
                    "local_path property of blob {}".format(blobpath))

            cloud_mtime = blob_props.last_modified - \
                entity["cloud_utc_mtime"] + entity["local_utc_mtime"]

        # no entity implies this blob is created by computing nodes. Download
        if entity is None and blob_props is not None:
            cloud_mtime = datetime.datetime.utcnow().replace(
                microsecond=0, tzinfo=datetime.timezone.utc)

        self.logger.debug("local_mtime = %s", local_mtime)
        self.logger.debug("cloud_mtime = %s", cloud_mtime)

        if local_mtime == cloud_mtime:
            return 0

        if local_mtime > cloud_mtime:
            return 1

        # else cloud_mtime > local_mtime
        return 2

    def update_table_record(self, mission, blobpath, filepath):
        """Updating a blob's record in the table.

        Args:
            mission [in]: an MissionInfo object.
            blobpath [in]: relative path to the Blob root on Azure.
            filename [in]: path to the file on a local machine.
        """

        self.logger.debug(
            "Updating record of blob %s in table %s", blobpath, mission.table_name)

        assert isinstance(mission, MissionInfo), "Type error!"
        assert isinstance(blobpath, str), "Type error!"
        assert isinstance(filepath, str), "Type error!"

        local_utc_mtime = datetime.datetime.utcfromtimestamp(
            os.path.getmtime(filepath)).replace(
                microsecond=0, tzinfo=datetime.timezone.utc)

        cloud_utc_mtime = self.storage_client.get_blob_properties(
            mission.container_name, blobpath).properties.last_modified

        blobkey = base64.urlsafe_b64encode(blobpath.encode()).decode()

        entity = {
            "PartitionKey": "blobfiles", "RowKey": blobkey,
            "local_utc_mtime": local_utc_mtime,
            "cloud_utc_mtime": cloud_utc_mtime,
            "local_path": os.path.abspath(filepath)}

        self.table_client.insert_or_replace_entity(mission.table_name, entity)

        self.logger.info(
            "Done updating record in table %s", mission.table_name)

    def upload_local_file(self, mission, blobpath, filepath, syncmode=True):
        """Upload a local file to a mission's sotrage container.

        When syncmode is True, only when the timestamp of the local file is newer
        than that of the cloud file (if exists), this function will upload a
        file to cloud. If syncmode is False, this function will always upload
        the file to cloud regardless the status of the file on the cloud.

        Args:
            mission [in]: an MissionInfo object.
            blobpath [in]: relative path to the Blob root on Azure.
            filename [in]: path to the file on a local machine.
            syncmode [in]: use "syncronization mode" or "always upload" mode.
        """

        self.logger.debug("Uploading file %s to blob %s", filepath, blobpath)

        assert isinstance(mission, MissionInfo), "Type error!"
        assert isinstance(blobpath, str), "Type error!"
        assert isinstance(filepath, str), "Type error!"
        assert isinstance(syncmode, bool), "Type, errir!"

        if not os.path.isfile(filepath):
            raise FileNotFoundError("{} does not exist".format(filepath))

        # if we are in sync mode
        if syncmode:
            code = self.compare_timestamp(mission, blobpath, filepath)
            upload = (code == 1)
        else:
            upload = True

        # upload to Azure storage
        if upload:
            self.storage_client.create_blob_from_path(
                mission.container_name, blobpath, filepath, max_connections=4)

            self.logger.info(
                "Done uploading file %s to blob %s", filepath, blobpath)

            # updating record in the table
            self.update_table_record(mission, blobpath, filepath)
        else:
            self.logger.info(
                "No need to upload file %s to blob %s", filepath, blobpath)

    def download_cloud_file(self, mission, blobpath, filepath, syncmode=True):
        """Download a file from a mission's sotrage container to local machine.

        When syncmode is True, only when the timestamp of the cloud file is newer
        than that of the local file (if exists), this function will download the
        file from cloud. If syncmode is False, this function will always download
        the file from cloud regardless the status of the local file.

        Args:
            mission [in]: an MissionInfo object.
            blobpath [in]: relative path to the Blob root on Azure.
            filename [in]: path to the file on a local machine.
            syncmode [in]: use "syncronization mode" or "always download" mode.
        """

        self.logger.debug("Download blob %s to file %s", blobpath, filepath)

        assert isinstance(mission, MissionInfo), "Type error!"
        assert isinstance(blobpath, str), "Type error!"
        assert isinstance(filepath, str), "Type error!"
        assert isinstance(syncmode, bool), "Type, errir!"

        if not self.storage_client.exists(mission.container_name, blobpath):
            raise FileNotFoundError("Blob {} does not exist".format(blobpath))

        # if we are in sync mode
        if syncmode:
            code = self.compare_timestamp(mission, blobpath, filepath)
            download = (code == 2)
        else:
            download = True

        # download from Azure storage
        if download:
            # make sure all intermediate folders exist
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            self.storage_client.get_blob_to_path(
                mission.container_name, blobpath, filepath, max_connections=4)
            self.logger.info(
                "Done downloading blob %s to file %s", blobpath, filepath)

            # updating record in the table
            self.update_table_record(mission, blobpath, filepath)
        else:
            self.logger.info(
                "No need to download blob %s to file %s", blobpath, filepath)

    def delete_cloud_file(self, mission, blobpath, ignore_not_exist=False):
        """Delete a file in Azure blob storage and its record in Azure table.

        Args:
            mission [in]: an MissionInfo object.
            blobpath [in]: relative path to the Blob root on Azure.
            ignore_not_exist [in]: ignore non-exist file or raise exception.
        """

        self.logger.debug("Deleting blob %s", blobpath)

        assert isinstance(mission, MissionInfo), "Type error!"
        assert isinstance(blobpath, str), "Type error!"
        assert isinstance(ignore_not_exist, bool), "Type error!"

        if not self.storage_client.exists(mission.container_name, blobpath):
            # if we choose to ignore it
            if ignore_not_exist:
                self.logger.info("Blob %s not exists. Skip.", blobpath)
                return
            # otherwise, raise an error
            raise FileNotFoundError("Blob {} does not exist".format(blobpath))

        # delete blob
        self.storage_client.delete_blob(mission.container_name, blobpath)
        self.logger.info("Done deleting blob %s", blobpath)

        # delete record from Azure table
        self.logger.debug("Deleting record of %s from the table", blobpath)
        try:
            blobkey = base64.urlsafe_b64encode(blobpath.encode()).decode()
            self.table_client.delete_entity(
                mission.table_name, "blobfiles", blobkey)
        except azure.common.AzureMissingResourceHttpError:
            pass
        self.logger.info("Done deleting record of %s from the table", blobpath)

    def upload_local_dir(self, mission, dirblobname, dirpath,
                         syncmode=True, ignore_patterns=["__pycache__"]):
        """Upload a directory to a mission's storage container.

        Args:
            mission [in]: an MissionInfo object.
            dirblobname [in]: the blobpath relative to the container's root path.
            dirpath [in]: path to the directory on a local machine.
            syncmode [in]: use "syncronization mode" or "always upload" mode.
            ignore_patterns [in]: a list of Python regular expression string.
        """

        self.logger.debug("Uploading directory %s to blob %s", dirpath, dirblobname)

        assert isinstance(mission, MissionInfo), "Type error!"
        assert isinstance(dirblobname, str), "Type error!"
        assert isinstance(dirpath, str), "Type error!"
        assert isinstance(syncmode, bool), "Type, errir!"
        assert isinstance(ignore_patterns, list), "Type, errir!"

        if not os.path.isdir(dirpath):
            raise FileNotFoundError("{} does not exist".format(dirpath))

        # get the full and absolute path (and basename)
        dirpath = os.path.abspath(os.path.normpath(dirpath))

        # upload files
        for parent_dir, _, files in os.walk(dirpath):
            for f in files:
                filepath = os.path.join(parent_dir, f)
                relfilepath = os.path.relpath(filepath, dirpath)

                if path_ignored(relfilepath, ignore_patterns):
                    continue

                fileblobname = os.path.join(dirblobname, relfilepath)
                self.upload_local_file(mission, fileblobname, filepath, syncmode)

        self.logger.info("Done uploading directory %s to blob %s", dirpath, dirblobname)

    def download_cloud_dir(self, mission, dirblobname, dirpath,
                           syncmode=True, ignore_patterns=["__pycache__"]):
        """Download a directory from the sotrage container to local machine.

        Args:
            mission [in]: an MissionInfo object.
            dirblobname [in]: the blobpath relative to the container's root path.
            dirpath [in]: path to the directory on a local machine.
            syncmode [in]: use "syncronization mode" or "always download" mode.
            ignore_patterns [in]: a list of Python regular expression string.
        """

        self.logger.debug(
            "Downloading directory %s from blob %s", dirpath, dirblobname)

        assert isinstance(mission, MissionInfo), "Type error!"
        assert isinstance(dirblobname, str), "Type error!"
        assert isinstance(dirpath, str), "Type error!"
        assert isinstance(syncmode, bool), "Type, errir!"
        assert isinstance(ignore_patterns, list), "Type, errir!"

        # get the full and absolute path
        dirpath = os.path.abspath(os.path.normpath(dirpath))

        blob_list = self.storage_client.list_blobs(
            mission.container_name,
            prefix="{}/".format(dirblobname), num_results=50000)

        for blob in blob_list:
            relblob = os.path.relpath(blob.name, dirblobname)

            # check against ignored patterhs
            if path_ignored(relblob, ignore_patterns):
                continue

            filename = os.path.join(dirpath, relblob)
            self.download_cloud_file(mission, blob.name, filename, syncmode)

        self.logger.info(
            "Done downloading directory %s from blob %s", dirpath, dirblobname)

    def delete_cloud_dir(self, mission, dirblobname, ignore_not_exist=False):
        """Delete a folder in Azure blob storage and its record in Azure table.

        Args:
            mission [in]: an MissionInfo object.
            dirblobname [in]: relative path to the Blob root on Azure.
            ignore_not_exist [in]: ignore non-exist file or raise exception.
        """

        self.logger.debug("Deleting %s from container.", dirblobname)

        assert isinstance(mission, MissionInfo), "Type error!"
        assert isinstance(dirblobname, str), "Type error!"
        assert isinstance(ignore_not_exist, bool), "Type error!"

        blob_list = self.storage_client.list_blobs(
            mission.container_name,
            prefix="{}/".format(dirblobname), num_results=50000)

        for blob in blob_list:
            self.delete_cloud_file(mission, blob.name, ignore_not_exist)

        self.logger.info("Done deleting directory %s", dirblobname)

    def add_task(self, mission, casename, casepath, ignore_exist=True):
        """Add a task to the mission's job (i.e., task scheduler).

        Args:
            mission [in]: an MissionInfo object.
            casename [in]: str; the name of the case
            casepath [in]: str; the path to case's directory
            ignore_exist [in]: skip adding this task if already exists
        """

        self.logger.debug("Adding %s to job", casename)

        assert isinstance(mission, MissionInfo), "Type error!"
        assert isinstance(casename, str), "Type error!"
        assert isinstance(casepath, str), "Type error!"
        assert isinstance(ignore_exist, bool), "Type error!"

        if casename in mission.tasks:
            if ignore_exist:
                return
            # if choose not to ignore, delete the existing task
            self.delete_task(mission, casename)

        casepath = os.path.abspath(casepath)

        ignore_patterns = ["__pycache__" ,".*?\.data", "fort\..*?",
                           "_plots" ,".*?\.asc", ".*?\.prj", ".*?\.nc"]

        # upload to the storage container
        self.upload_local_dir(mission, casename, casepath, True, ignore_patterns)

        # configuration of Docker image being used
        task_container_settings = azure.batch.models.TaskContainerSettings(
            image_name="barbagroup/landspill:bionic",
            container_run_options="--rm --workdir /home/landspill")

        # file that will be copied to VM from Azure storage
        input_data = [
            azure.batch.models.ResourceFile(
                storage_container_url=mission.container_url,
                blob_prefix="{}/".format(casename))]

        # file that will be copied to Azure storage from VM after simulation
        output_data = [
            azure.batch.models.OutputFile(
                file_pattern="{}/**/*".format(casename),
                upload_options=azure.batch.models.OutputFileUploadOptions(
                    upload_condition= \
                    azure.batch.models.OutputFileUploadCondition.task_completion),
                destination=azure.batch.models.OutputFileDestination(
                    container= \
                    azure.batch.models.OutputFileBlobContainerDestination(
                        container_url=mission.container_url,
                        path="{}".format(casename)))),
            azure.batch.models.OutputFile(
                file_pattern="$AZ_BATCH_TASK_DIR/std*.txt",
                upload_options=azure.batch.models.OutputFileUploadOptions(
                    upload_condition= \
                    azure.batch.models.OutputFileUploadCondition.task_completion),
                destination=azure.batch.models.OutputFileDestination(
                    container= \
                    azure.batch.models.OutputFileBlobContainerDestination(
                        container_url=mission.container_url,
                        path="{}".format(casename))))]

        # command to be executed on VM
        command = "/bin/bash -c \"" + \
            "cp -r $AZ_BATCH_TASK_WORKING_DIR/{} ./ && ".format(casename) + \
            "run.py {} && ".format(casename) + \
            "createnc.py {} && ".format(casename) + \
            "cp -r ./{} $AZ_BATCH_TASK_WORKING_DIR".format(casename) + \
            "\""

        # setting up the task
        task_params = azure.batch.models.TaskAddParameter(
            id=casename,
            command_line=command,
            container_settings=task_container_settings,
            resource_files=input_data,
            output_files=output_data)

        # add the task to the job
        self.batch_client.task.add(mission.job_name, task_params)

        # add the case information to MissionInfo object
        mission.add_task(casename, casepath)

        self.logger.debug("Done adding %s to job", casename)

    def delete_task(self, mission, case):
        """Delete a task from the mission's job (i.e., task scheduler)."""

        self.batch_client.task.delete(mission.job_name, case)
        mission.remove_task(case)
