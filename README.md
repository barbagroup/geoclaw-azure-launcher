# geoclaw-azure-launcher

This repository provides helpers for launching GeoClaw land-spill simulations on Azure.
Documentation is still a WIP.

## Prerequisites

* Azure Python API v4.0.0: `$ pip install azure`
* Azure Batch Python API v6.0.0 `$ pip install -I azure-batch==6.0.0`

## Running tests

The script `test.py` provides a very simple example for the usage of the helpers.
To run this script, first, you'll have to install the prerequisites described in the prerequisite section.
Second, you'll need an available Azure subscription.
You should then be able to find the information regarding how to create Azure Batch and Azure Storage accounts in Azure documentation.
Put the Azure Batch and Azure Storage account credentials into the text file `credential.txt`, then execute the Python script: `$ python test.py`.

The script will create the necessary resources on Azure and execute the simulations.
It will monitor the progress of the tasks on Azure and download result data whenever there's a simulation completed.
Finally, it will delete all resources on Azure after all simulations finished.
However, keep in mind, this helper is still under development, so please go to [Azure Protal](https://portal.azure.com) to make sure if all resources are indeed deleted to avoid burning money for nothing.

## Using the helper in other Python scripts:

The documentation of this part is still a WIP.
In a nutshell, the helper objects are under the folder `helpers`.
And the main object is the `Mission` class.

## Contact:
Pi-Yueh Chuang (pychuang@gwu.edu)
