# geoclaw-azure-launcher

This repository provides helpers for launching GeoClaw LandSpill simulations on Microsoft Azure.
Documentation is still a WIP.

## Prerequisites

* Azure Python API v4.0.0: `$ pip install azure`
* Azure Batch Python API v6.0.0 `$ pip install -I azure-batch==6.0.0`
* Python cryptography module v2.6.1 or higher `$ pip install cryptography` or `conda install -c anaconda cryptography`

## Running tests

The script `test.py` provides a very simple example for the usage of the helpers.
To run this script, first, you'll have to install the prerequisites described in the prerequisite section.
Second, you'll need an available Azure subscription.
You should then be able to find the information regarding how to create Azure Batch and Azure Storage accounts in Azure documentation.
Put the Azure Batch and Azure Storage account credentials into the text file `credential.txt`, then execute the Python script: `$ python test.py`.

The script will create the necessary resources on Azure and execute the simulations.
It will monitor the progress of the tasks on Azure and download result data whenever there's a simulation completed.
Finally, it will delete all resources on Azure after all simulations finished.
However, keep in mind, this helper is still under development, so please go to [Azure Portal](https://portal.azure.com) to make sure if all resources are indeed deleted to avoid burning money for nothing.

## Using ArcGIS Pro to run the helpers

This repository contains an [ArcGIS Pro](https://https://www.esri.com/en-us/arcgis/products/arcgis-pro/overview) Python toolbox (Land-spill Azure.pyt) that allows the helpers to be used to launch GeoClaw LandSpill simulations on Azure from the commercial ArcGIS Pro desktop GIS application. The Python toolbox requires ArcGIS Pro v2.4, or higher, and contains the following tools:

* **Create Encrypted Azure Credential File** - Builds an encrypted, passcode-protected file that stores Microsoft Azure batch and storage account credentials.
* **Create GeoClaw Cases** - Constructs case directories for GeoClaw simulations for one or more fluid point sources.
* **Delete Azure Resources** - A tool to delete Microsoft Azure job, pool and storage resources used to run a set of simulations.
* **Download Cases from Azure** - Downloads simulation results from Microsoft Azure to your local desktop.
* **Monitor Azure Resources** - A tool to monitor Microsoft Azure resource usage as a GeoClaw LandSpill job progresses.
* **Run Cases on Azure** - Submits GeoClaw LandSpill simulation cases to Azure for execution. 

## Using the helpers in other Python scripts:

The documentation of this part is still a WIP.
In a nutshell, the helper objects are under the folder `helpers`.
And the main object is the `Mission` class.

## Contact:
Pi-Yueh Chuang (pychuang@gwu.edu)

J. Tracy Thorleifson (tracy.thorleifson@g2-is.com)
