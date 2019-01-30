#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Pi-Yueh Chuang <pychuang@gwu.edu>
#
# Distributed under terms of the MIT license.

"""
An object holding user information for Azure services.
"""
import azure.storage.blob
import azure.batch.batch_auth
import azure.batch.batch_service_client


class UserCredential:
    """UserCredential"""

    def __init__(self, batch_account_name=None, batch_account_key=None,
                 batch_account_url=None, storage_account_name=None,
                 storage_account_key=None, credential_file=None):
        """__init__

        Args:
            batch_account_name [in]: Batch account name
            batch_account_key [in]: Batch account key
            batch_account_url [in]: Batch account URL
            storage_account_name [in]: Storage account name
            storage_account_key [in]: Storage account key
            credential_file [in]: text file with credential info. Required if
                other credential info are not specified in this init func.
        """

        if credential_file is None:
            assert batch_account_name is not None
            assert batch_account_key is not None
            assert batch_account_url is not None
            assert storage_account_name is not None
            assert storage_account_key is not None

            self.batch_account_name = batch_account_name
            self.batch_account_key = batch_account_key
            self.batch_account_url = batch_account_url
            self.storage_account_name = storage_account_name
            self.storage_account_key = storage_account_key
        else:
            args = []
            with open(credential_file, "r") as f:
                for i in range(5):
                    args.append(f.readline().rstrip("\n"))

            self.batch_account_name = args[0]
            self.batch_account_key = args[1]
            self.batch_account_url = args[2]
            self.storage_account_name = args[3]
            self.storage_account_key = args[4]

    def create_blob_client(self):
        """create_blob_client

        Return:
            A new instance of azure.storage.blob.BlockBlobService.
        """

        return azure.storage.blob.BlockBlobService(
            account_name=self.storage_account_name,
            account_key=self.storage_account_key)

    def create_batch_client(self):
        """create_batch_client

        Return:
            A new instance of azure.batch.batch_service_client.BatchServiceClient.
        """

        credentials = azure.batch.batch_auth.SharedKeyCredentials(
            self.batch_account_name, self.batch_account_key)
        return azure.batch.batch_service_client.BatchServiceClient(
            credentials, batch_url=self.batch_account_url)
