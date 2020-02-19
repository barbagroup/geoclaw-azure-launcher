#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019-2020 Pi-Yueh Chuang and Lorena A. Barba.
#
# Distributed under terms of the BSD 3-Clause license.

"""
A script to create cred.dat, which is required for running tests.
"""
import os
import sys
import getpass

if __name__ == "__main__":

    test_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(test_dir))

    from helpers.azuretools.user_credential import UserCredential

    batch_account_name = input("Azure Batch account name: ")
    batch_account_key = input("Azure Batch account key: ")
    batch_account_url = input("Azure Batch account url: ")
    storage_account_name = input("Azure Storage account name: ")
    storage_account_key = input("Azure Storage account key: ")
    passcode = getpass.getpass("Passcode (hidden from the screen): ")

    u = UserCredential(
        batch_account_name, batch_account_key, batch_account_url,
        storage_account_name, storage_account_key)

    filename = os.path.join(test_dir, "cred.dat")

    u.write_encrypted(passcode, filename)
