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


Introduction
============

Agentic Data Generation Toolkit is designed to provide an easy to use interface for both a human user as well as an Agent. The primary purpose of this Toolkit is to provide a framework for experimentation with Agents that generate data. The framework provides all the automation needed to excute a scenario while providing the user with both consistent measurements across scenarios as well as tracking and reporting of results.

The goal is to provide an easy to modify or extend toolkit to support your research needs.

Highlights
==========
- A "lab journal" which can be invoked through an experiment.
- Reports saved to disk of both preview and results of an experiment.
- Extensible architecture. The framework is designed to be extensible on load and during execution.
- Custom components can be created and used in your experiments. You are not constrained to the components that are provided.


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

.. code-block:: console

   adgtk-mgr [options]  

   Commands:
      project      : Project management (create, destroy)
      experiment   : Experiment operations (create, run, list, preview)
      factory      : List Factory or if include a group the group listing
      
   options:
   -h, --help            show a help message and exits
   -f FILE, --file FILE  override the settings file with this file
   --version             show program's version number and exit
   --yaml                Use YAML format when creating the project settings file

   Project
   -------
      $ adgtk-mgr project create example1   Creates a new project called example1
      $ adgtk-mgr project destroy example1  deletes the example1 project

   Experiment
   ----------
      $ adgtk-mgr experiment list           lists all available experiments
      $ adgtk-mgr experiment create         Starts a wizard to build an experiment
      $ adgtk-mgr experiment create exp1     Starts a wizard to build an experiment with the name exp1
      $ adgtk-mgr experiment run            via a menu select and run an experiment
      $ adgtk-mgr experiment run exp1       Run exp1
      $ adgtk-mgr experiment report         Starts a web server for reports

   Factory
   -------
      $ adgtk-mgr factory                   Lists available factory blueprints
      $ adgtk-mgr factory agent             Lists agent factory blueprints

   


When your not creating or destroying a project by default the toolkit will look for a file called `project.toml` in the current directory. This file is used to store the settings for the project. If you want to use a different file you can use the `--file` option to specify the file to use. For example, to use a file called `settings1.toml` you would use the following command:

.. code-block:: console

      $ adgtk-mgr --file settings1.toml factory   
