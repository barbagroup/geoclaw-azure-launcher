#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Pi-Yueh Chuang <pychuang@gwu.edu>
#
# Distributed under terms of the MIT license.

"""
Download required data for the test cases.
"""
import os
import sys
import time

if sys.version_info.major == 2:
    from urllib import urlretrieve
elif sys.version_info.major == 3:
    from urllib.request import urlretrieve
else:
    raise ImportError("Unknown Python version.")


def download(file_path, file_url):
    """Download a file to file_path from file_url."""

    if os.path.isfile(file_path):
        print("{} already exists. Skip downloading.".format(file_path))
    else:
        print("Downloading file: {}".format(file_path))
        urlretrieve(file_url, file_path)
        print("Done.")


def download_all():
    """Download everything."""

    script_path = os.path.dirname(os.path.abspath(__file__))

    file_path = os.path.join(script_path, "test_case_1/utah_dem_topo_3.txt")
    file_url = "https://dl.dropboxusercontent.com/s/hhpebow2s81yzgo/utah_dem_topo_3.txt?dl=0"
    download(file_path, file_url)

    file_path = os.path.join(script_path, "test_case_1/hydro_feature1.asc")
    file_url = "https://dl.dropboxusercontent.com/s/02lbf2kg84b5sij/hydro_feature1.asc?dl=0"
    download(file_path, file_url)

    file_path = os.path.join(script_path, "test_case_1/hydro_feature2.asc")
    file_url = "https://dl.dropboxusercontent.com/s/mh8eh7wx6jy1z2t/hydro_feature2.asc?dl=0"
    download(file_path, file_url)

    file_path = os.path.join(script_path, "test_case_1/hydro_feature3.asc")
    file_url = "https://dl.dropboxusercontent.com/s/gs3g7amhatn9pxf/hydro_feature3.asc?dl=0"
    download(file_path, file_url)

    file_path = os.path.join(script_path, "test_case_2/mountain.asc")
    file_url = "https://dl.dropboxusercontent.com/s/c21eg6yt90jll1r/mountain.asc?dl=0"
    download(file_path, file_url)


if __name__ == "__main__":
    download_all()
