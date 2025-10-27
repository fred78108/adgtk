=======================================
ADGTK - Agentic Data Generation Toolkit
=======================================

.. toctree::
   :maxdepth: 1
   
   concept
   roadmap
   changes/index
   api/index
   logging


.. warning::
   This project is in the early stages of development. As this package is under active development the API and documentation are subject to change. Please check back often for updates.

.. warning::
   Version 0.2.0b1 is a beta release. Documentation updates are pending.


Introduction
============

Agentic Data Generation Toolkit is designed to provide an easy to use interface for both a human user as well as an Agent. The primary purpose of this Toolkit is to provide a framework for experimentation with Agents that generate data. The framework provides all the automation needed to excute a scenario while providing the user with both consistent measurements across scenarios as well as tracking and reporting of results.

The goal is to provide an easy to modify or extend toolkit to support your research needs.

Highlights
==========
- A "lab journal" which can be invoked through an experiment.
- Extensible architecture. The framework is designed to be extensible on load and during execution.
- Extensible architecture supports user defined objects via a common factory.


Installation
============

Via PyPi
--------

To install the package, you can use pip:

.. code-block:: console

   $ pip install adgtk

This is useful for when you wish to run the toolkit in your own projects.

Manual installation from source
-------------------------------

If you wish to clone the repository and install the package manually, you can do so by following these steps:

1. active your virtual environment.
2. Download the project from https://github.com/fred78108/adgtk.
3. from the root folder of adgtk, run the following command:

.. code-block:: console

   $ python -m pip install -e .

This will let you modify your copy of adgtk and evaluate the results. This is useful for development of your own version of adgtk.


Usage
=====

Command structure
-----------------

ADGTK is designed to be run from the command line. The primary command is `adgtk-mgr`. This command is used to manage the toolkit. The command has a number of subcommands that are used to manage the toolkit.

When your not creating or destroying a project by default the toolkit will look for a file called `bootstrap.py` in the current directory. This file is used to extend the adgtk framework with your code.
