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
import pickle
import azure.batch.models
import azure.storage.blob
import azure.common
from . import UserCredential
from . import MissionInfo


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
            created = self.storage_client.create_container(
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

    def upload_single_file(self, mission, blobpath, filepath):
        """Upload a file to a mission's sotrage container.

        Args:
            mission [in]: an MissionInfo object.
            blobpath [in]: relative path to the Blob root on Azure.
            filename [in]: path to the file on a local machine.
        """

        self.logger.debug("Uploading file %s to blob %s", filepath, blobpath)

        # upload to Azure storage
        self.storage_client.create_blob_from_path(
            container_name=mission.container_name,
            blob_name=blobpath, file_path=filepath, max_connections=4)

        self.logger.info("Done uploading file %s to blob %s", filepath, blobpath)

    def download_single_file(self, mission, blobpath, filepath):
        """Download a file from a mission's sotrage container.

        Args:
            mission [in]: an MissionInfo object.
            blobpath [in]: relative path to the Blob root on Azure.
            filename [in]: path to the file on a local machine.
        """

        self.logger.debug("Download file %s from blob %s", filepath, blobpath)

        # download from Azure storage
        self.storage_client.get_blob_to_path(
            container_name=mission.container_name,
            blob_name=blobpath, file_path=filepath)

        self.logger.info("Done uploading file %s from blob %s", filepath, blobpath)

    def create_pool(self):
        """Create a pool on Azure based on the mission info."""

        # if the pool already exists (it does not mean it's ready)
        if self.batch_client.pool.exists(pool_id=self.info.pool_name):
            # update info.n_nodes
            pool_info = self.batch_client.pool.get(self.info.pool_name)
            self.info.n_nodes = pool_info.target_dedicated_nodes

            logger.info("Pool %s already exists.", self.info.pool_name)
            return "Already exist"

        # if the batch client is not aware of this pool
        logger.info("Issuing creation to pool %s.", self.info.pool_name)

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

        # pool setting
        pool_conf = azure.batch.models.PoolAddParameter(
            id=self.info.pool_name,
            virtual_machine_configuration=vm_conf,
            vm_size=self.info.vm_type,
            target_dedicated_nodes=self.info.n_nodes)

        # create the pool
        self.batch_client.pool.add(pool_conf)

        logger.info("Creation command issued.")

        return "Done"

    def resize_pool(self, n_nodes):
        """Resize the pool."""

        # if the pool already exists (it does not mean it's ready)
        if not self.batch_client.pool.exists(pool_id=self.info.pool_name):
            logger.error("Pool %s does not exist.", self.info.pool_name)
            raise RuntimeError(
                "Pool {} does not exist.".format(self.info.pool_name))

        # get the number of nodes in the pool on Azure
        pool_info = self.batch_client.pool.get(self.info.pool_name)

        # check if the size of the pool matches the self
        if pool_info.target_dedicated_nodes == n_nodes: # no change, skip
            logger.info(
                "Pool %s already has the specified number of nodes. Skip.",
                self.info.pool_name)
            return "No change"

        logger.info("Issuing a resizing command to pool %s.", self.info.pool_name)

        # an alias for shorter code
        pool_resizing = azure.batch.models.AllocationState.resizing
        pool_steady = azure.batch.models.AllocationState.steady

        # if the pool is under resizing, stop the resizing first
        if pool_info.allocation_state is pool_resizing:
            self.batch_client.pool.stop_resize(self.info.pool_name)

            while pool_info.allocation_state is not pool_steady:
                time.sleep(2) # wait for 2 seconds
                # get updated information of the pool
                pool_info = self.batch_client.pool.get(self.info.pool_name)

        # now resizing
        self.batch_client.pool.resize(
            pool_id=self.info.pool_name,
            pool_resize_parameter=azure.batch.models.PoolResizeParameter(
                target_dedicated_nodes=n_nodes,
                node_deallocation_option="requeue"))

        self.info.n_nodes = n_nodes

        logger.info("Resizing command issued to pool %s.", self.info.pool_name)

        return "Done"

    def delete_pool(self):
        """Delete a pool on Azure based on the content set in self."""

        logger.info("Issuing deletion to pool %s.", self.info.pool_name)

        # if the pool exists, issue a delete command
        if self.batch_client.pool.exists(pool_id=self.info.pool_name):
            self.batch_client.pool.delete(self.info.pool_name)
            logger.info("Deletion command issued to pool %s.", self.info.pool_name)

            return "Done"
        else:
            logger.info(
                "Pool %s does not exist. Skip deletion.", self.info.pool_name)
            return "Not exist"

    def create_job(self):
        """Create a job (i.e. task scheduler) for this mission."""

        # job parameters
        job_params = azure.batch.models.JobAddParameter(
            id=self.info.job_name,
            pool_info=azure.batch.models.PoolInformation(
                pool_id=self.info.pool_name))

        logger.info("Issuing creation to job %s", self.info.job_name)

        # add job
        try:
            self.batch_client.job.add(job_params)
            logger.info("Creation command issued.")
        except azure.batch.models.BatchErrorException as err:
            if err.message.value.startswith("The specified job already exists."):
                logger.info("Job already exists. SKIP creation.")
            else:
                raise

        return "Done"

    def delete_job(self):
        """Delete the mission job (i.e. task scheduler)."""

        logger.info("Issuing deletion to job %s", self.info.job_name)

        try:
            self.batch_client.job.delete(self.info.job_name)
        except azure.batch.models.BatchErrorException as err:
            if err.message.value.startswith("The specified job does not exist."):
                logger.info("Job does not exist. SKIP deletion.")
            else:
                raise

        logger.info("Deletion command issued.")

        return "Done"

    def upload_dir(self, dir_path, ignore_exist=False):
        """Upload a directory to the mission container.

        Args:
            dir_path [in]: the directory being uploaded.
        """

        # get the full and absolute path (and basename)
        dir_path = os.path.abspath(os.path.normpath(dir_path))
        dir_base_name = os.path.basename(dir_path)

        # check if the base name conflicts any uploaded cases
        if dir_base_name in self.uploaded_dirs.keys() and not ignore_exist:
            logger.error(
                "A case with the same base name %s already exists in the \
                 container. Can't upload it.", dir_base_name)
            raise RuntimeError(
                "A case with the same base name {} ".format(dir_base_name) +
                "already exists in the container. Can't upload it.")

        # check if the container was created
        assert self.container_url is not None
        assert self.container_token is not None

        logger.info("Uploading directory %s.", dir_path)

        # upload files
        for dirpath, dirs, files in os.walk(dir_path):
            for f in files:
                file_path = os.path.join(os.path.abspath(dirpath), f)
                blob_name = os.path.relpath(file_path, os.path.dirname(dir_path))

                logger.info("Uploading file %s.", file_path)
                self.storage_client.create_blob_from_path(
                    container_name=self.info.container_name, blob_name=blob_name,
                    file_path=file_path, max_connections=4)
                logger.info("Done uploading file %s.", file_path)

        logger.info("Done uploading directory %s.", dir_path)

        # add the case name and the parent path to the tracking list
        self.uploaded_dirs[dir_base_name] = os.path.dirname(dir_path)

        # write the uploaded info to a file and upload to the container as a log
        with open(os.path.join(self.wd, "uploaded_dirs.dat"), "wb") as f:
            f.write(pickle.dumps(self.uploaded_dirs))

        logger.info("Uploading uploaded_dirs.dat")
        self.storage_client.create_blob_from_path(
            container_name=self.info.container_name, blob_name="uploaded_dirs.dat",
            file_path=os.path.join(self.wd, "uploaded_dirs.dat"), max_connections=2)
        logger.info("Done uploading uploaded_dirs.dat")

        os.remove(os.path.join(self.wd, "uploaded_dirs.dat"))

        return "Done"

    def download_dir(self, dir_path, download_raw_output=False,
                     download_asc=False,
                     ignore_downloaded=True, ignore_not_exist=True):
        """Download a directory from the mission blob container."""

        # get the full and absolute path
        dir_path = os.path.abspath(os.path.normpath(dir_path))
        dir_base_name = os.path.basename(dir_path)

        # check if the container exists
        assert self.container_url is not None
        assert self.container_token is not None

        if ignore_downloaded and (dir_base_name in self.downloaded):
            logger.info("Directory %s already downloaded. Skip.", dir_path)
            return "Already downloaded. Skip."

        logger.info("Downloading directory %s.", dir_path)

        if dir_base_name not in self.uploaded_dirs.keys():
            if not ignore_not_exist:
                logger.error(
                    "Directory %s is not in the container.", dir_path)
                raise RuntimeError(
                    "Directory {} is not in the container.".format(dir_path))
            else:
                logger.warning(
                    "Directory %s is not in the container. SKIP.", dir_path)

                return "Not found on Azure. Skip."

        blob_list = self.storage_client.list_blobs(
            container_name=self.info.container_name,
            prefix="{}/".format(dir_base_name), num_results=50000)

        for blob in blob_list:
            file_abs_path = os.path.join(
                self.uploaded_dirs[dir_base_name], blob.name)

            f_dir, f = os.path.split(file_abs_path)
            base, ext = os.path.splitext(f)

            # check whether to skip raw results
            if not download_raw_output:
                if ext == ".data":
                    continue

                if base in ["fort", "claw_git_diffs", "claw_git_status"]:
                    continue

            # check whether to skip raster files (topo & hydro)
            if not download_asc and ext in [".asc", ".prj"]:
                continue

            # never download __pycache__
            if os.path.split(f_dir)[1] == "__pycache__":
                continue

            if not os.path.isdir(os.path.dirname(file_abs_path)):
                os.makedirs(os.path.dirname(file_abs_path))

            logger.info("Downloading file %s.", file_abs_path)
            self.storage_client.get_blob_to_path(
                container_name=self.info.container_name,
                blob_name=blob.name, file_path=file_abs_path)
            logger.info("Done downloading file %s.", file_abs_path)

        logger.info("Done downloading directory %s.", dir_path)

        # add the case name to the tracking list
        self.downloaded.append(dir_base_name)

        # write the downloaded info to a file and upload to the container as a log
        with open(os.path.join(self.wd, "downloaded.dat"), "wb") as f:
            f.write(pickle.dumps(self.downloaded))

        logger.info("Uploading downloaded.dat")
        self.storage_client.create_blob_from_path(
            container_name=self.info.container_name, blob_name="downloaded.dat",
            file_path=os.path.join(self.wd, "downloaded.dat"), max_connections=2)
        logger.info("Done uploading downloaded.dat")

        os.remove(os.path.join(self.wd, "downloaded.dat"))

        return "Done."

    def delete_dir(self, dir_path, ignore_not_exist=True):
        """Delete a directory from the mission's container."""

        # get the full and absolute path
        dir_path = os.path.abspath(os.path.normpath(dir_path))
        dir_base_name = os.path.basename(dir_path)

        # check if the container exists
        assert self.container_url is not None
        assert self.container_token is not None

        logger.info("Deleting %s from container.", dir_base_name)

        if dir_base_name not in self.uploaded_dirs.keys():
            if not ignore_not_exist:
                logger.error(
                    "Directory %s is not in the container.", dir_path)
                raise RuntimeError(
                    "Directory {} is not in the container.".format(dir_path))
            else:
                logger.warning(
                    "Directory %s is not in the container. SKIP.", dir_path)
        else:
            blob_list = self.storage_client.list_blobs(
                container_name=self.info.container_name,
                prefix="{}/".format(dir_base_name), num_results=50000)

            for blob in blob_list:
                logger.info("Deleting file %s.", blob.name)
                self.storage_client.delete_blob(
                    container_name=self.info.container_name,
                    blob_name=blob.name)
                logger.info("Done deleting file %s.", blob.name)

            logger.info("Done deleting directory %s.", dir_path)

            logger.info("Updating uploaded_dirs.dat")
            del self.uploaded_dirs[dir_base_name]
            with open(os.path.join(self.wd, "uploaded_dirs.dat"), "wb") as f:
                f.write(pickle.dumps(self.uploaded_dirs))

            logger.info("Uploading uploaded_dirs.dat")
            self.storage_client.create_blob_from_path(
                container_name=self.info.container_name, blob_name="uploaded_dirs.dat",
                file_path=os.path.join(self.wd, "uploaded_dirs.dat"), max_connections=2)
            logger.info("Done uploading uploaded_dirs.dat")

            os.remove(os.path.join(self.wd, "uploaded_dirs.dat"))

    def add_task(self, case, ignore_exist=False):
        """Add a task to the mission's job (i.e., task scheduler).

        Args:
            case [in]: str; the name of case directory
        """

        # upload to the storage container
        self.upload_dir(case, ignore_exist)

        # get the full and absolute path
        case_path = os.path.abspath(os.path.normpath(case))
        case = os.path.basename(case_path)

        task_container_settings = azure.batch.models.TaskContainerSettings(
            image_name="barbagroup/landspill:bionic",
            container_run_options="--rm " + \
                "--workdir /home/landspill")

        input_data = [
            azure.batch.models.ResourceFile(
                storage_container_url=self.container_url,
                blob_prefix="{}/".format(case))]

        output_data = [
            azure.batch.models.OutputFile(
                file_pattern="{}/**/*".format(case),
                upload_options=azure.batch.models.OutputFileUploadOptions(
                    upload_condition= \
                    azure.batch.models.OutputFileUploadCondition.task_completion),
                destination=azure.batch.models.OutputFileDestination(
                    container= \
                    azure.batch.models.OutputFileBlobContainerDestination(
                        container_url=self.container_url,
                        path="{}".format(case)))),
            azure.batch.models.OutputFile(
                file_pattern="$AZ_BATCH_TASK_DIR/std*.txt",
                upload_options=azure.batch.models.OutputFileUploadOptions(
                    upload_condition= \
                    azure.batch.models.OutputFileUploadCondition.task_completion),
                destination=azure.batch.models.OutputFileDestination(
                    container= \
                    azure.batch.models.OutputFileBlobContainerDestination(
                        container_url=self.container_url,
                        path="{}".format(case))))]

        command = "/bin/bash -c \"" + \
            "cp -r $AZ_BATCH_TASK_WORKING_DIR/{} ./ && ".format(case) + \
            "run.py {} && ".format(case) + \
            "createnc.py {} && ".format(case) + \
            "cp -r ./{} $AZ_BATCH_TASK_WORKING_DIR".format(case) + \
            "\""

        task_params = azure.batch.models.TaskAddParameter(
            id=case,
            command_line=command,
            container_settings=task_container_settings,
            resource_files=input_data,
            output_files=output_data)

        logger.info("Add task %s.", case)
        self.batch_client.task.add(self.info.job_name, task_params)

    def delete_task(self, case):
        """Delete a task from the mission's job (i.e., task scheduler)."""

        raise NotImplementedError
