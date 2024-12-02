# Setup

This page provides setup and installation information for the `ACI` repo.

## Prerequisites

- Python >= 3.11

### Optional Prerequisites

- [Docker](https://docs.docker.com/get-docker/)

Clone the repo:

### Conda Environment

You may want to create a Python environment to isolate the dependencies for this
project. You can do this with `conda`. You will need to have `conda` installed.

```bash
conda create -n cambrian python=3.12
conda activate cambrian
```

## Installation

First, clone the repo:

```
git clone https://github.com/camera-culture/ACI.git
```

Then you can install the `cambrian` package by doing the following.

```bash
pip install -e .
```

```{eval-rst}

.. note::

    The package was actually designed to be used with poetry, and is required when `contributing <./contributing.html>`_ to the project. To install poetry, you can do the following:

    .. code-block:: bash

        pip install poetry
        poetry install

```
