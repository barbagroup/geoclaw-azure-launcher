#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
########################################################################################################################
# Copyright © 2019 The George Washington University and G2 Integrated Solutions, LLC.
# All Rights Reserved.
#
# Contributors: Pi-Yueh Chuang <pychuang@gwu.edu>
#               J. Tracy Thorleifson <tracy.thorleifson@g2-is.com>
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
An object holding user information for Azure services.
Modified to use the cyrptography library, rather than pycrypto, for encrypting azure credentials.
6/28/2019 - G2 Integrated Solutions, LLC - J.T. Thorleifson
"""
import azure.storage.blob
import azure.cosmosdb.table.tableservice
import azure.batch.batch_auth
import azure.batch.batch_service_client
import pickle
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class UserCredential:
    """UserCredential"""

    def __init__(self, batch_account_name=None, batch_account_key=None,
                 batch_account_url=None, storage_account_name=None,
                 storage_account_key=None, credential_file=None):
        """__init__

        The credential_file in the arg list is unencrypted file. To load
        encrypted credential file, create an empty UserCredential object and
        then use read_encrypted member function.

        Args:
            batch_account_name [in]: Batch account name
            batch_account_key [in]: Batch account key
            batch_account_url [in]: Batch account URL
            storage_account_name [in]: Storage account name
            storage_account_key [in]: Storage account key
            credential_file [in]: text file with credential info. Required if
                other credential info are not specified in this init func.
        """

        if credential_file is not None:
            args = []
            with open(credential_file, "r") as f:
                for i in range(5):
                    args.append(f.readline().rstrip("\n"))

            self.batch_account_name = args[0]
            self.batch_account_key = args[1]
            self.batch_account_url = args[2]
            self.storage_account_name = args[3]
            self.storage_account_key = args[4]

        else:
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

    def create_table_client(self):
        """create_table_client

        Return:
            A new instance of azure.cosmosdb.table.tableservice.TableService.
        """

        return azure.cosmosdb.table.tableservice.TableService(
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

    def write_encrypted(self, passcode, filename):
        """Write encrypted credential to a file."""

        # Encode the passcode and generate set the 'salt.'
        passcode = passcode.encode()
        salt = b'Rm\x95\xaf\xe9p`=\xbe\xf3\xb3\xa1\xef\x112\xf5'

        # Create the key definition object using the 'salt.'
        key_def = PBKDF2HMAC(algorithm=hashes.SHA3_256(), length=32, salt=salt, iterations=100000,
                             backend=default_backend())

        # Derive the encryption key by combining the key definition with the passcode.
        key = base64.urlsafe_b64encode(key_def.derive(passcode))

        # Construct the encryptor using the key.
        encryptor = Fernet(key)

        message = [
            encryptor.encrypt(self.batch_account_name.encode()),
            encryptor.encrypt(self.batch_account_key.encode()),
            encryptor.encrypt(self.batch_account_url.encode()),
            encryptor.encrypt(self.storage_account_name.encode()),
            encryptor.encrypt(self.storage_account_key.encode())]

        with open(filename, "wb") as f:
            pickle.dump(message, f)

    def read_encrypted(self, passcode, filename):
        """Read credential from an encrypted file."""
        from cryptography.fernet import InvalidToken

        with open(filename, "rb") as f:
            message = pickle.load(f)

        # Encode the passcode and generate set the 'salt.'
        passcode = passcode.encode()
        salt = b'Rm\x95\xaf\xe9p`=\xbe\xf3\xb3\xa1\xef\x112\xf5'

        # Create the key definition object using the 'salt.'
        key_def = PBKDF2HMAC(algorithm=hashes.SHA3_256(), length=32, salt=salt, iterations=100000,
                             backend=default_backend())

        # Derive the encryption key by combining the key definition with the passcode.
        key = base64.urlsafe_b64encode(key_def.derive(passcode))

        # Construct the decryptor using the key.
        decryptor = Fernet(key)

        # Attempt to decrypt the message. Note that if the user has supplied an invalid passcode, the derived key is,
        # by definition, incompatible with the encrypted message (token). In this case, decrypt method will not decrypt
        # the message. Rather, this will cause the decrypt method to raise the InvalidToken error. The InvalidToken
        # error does not return any message; we use it here to set the decrypted variable to a value that will allow
        # the script's original ValueError message to be raised.
        try:
            decrypted = [decryptor.decrypt(s) for s in message]

        except InvalidToken:
            decrypted = [b"Invalid Token."]

        if decrypted[0] == b"Invalid Token.":
            raise ValueError("Wrong passcode.")

        self.batch_account_name = decrypted[0].decode()
        self.batch_account_key = decrypted[1].decode()
        self.batch_account_url = decrypted[2].decode()
        self.storage_account_name = decrypted[3].decode()
        self.storage_account_key = decrypted[4].decode()
