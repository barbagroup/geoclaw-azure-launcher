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

    def __init__(self,
                 batch_account_name, batch_account_key, batch_account_url,
                 storage_account_name, storage_account_key):
        """__init__

        Args:
            batch_account_name [in]: Batch account name
            batch_account_key [in]: Batch account key
            batch_account_url [in]: Batch account URL
            storage_account_name [in]: Storage account name
            storage_account_key [in]: Storage account key
        """

        self.batch_account_name = batch_account_name
        self.batch_account_key = batch_account_key
        self.batch_account_url = batch_account_url
        self.storage_account_name = storage_account_name
        self.storage_account_key = storage_account_key

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
            credentials, base_url=self.batch_account_url)
