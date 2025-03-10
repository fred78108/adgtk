===============================
Agentic Data Generation Toolkit
===============================
Agentic Data Generation Toolkit is designed to provide an easy to use interface for both a human user as well as an Agent. The primary purpose of this Toolkit is to provide a framework for experimentation with Agents that generate data. The framework provides all the automation needed to excute a scenario while providing the user with both consistent measurements across scenarios as well as tracking and reporting of results.


Highlights
==========
- A "lab journal" which can be invoked through an experiment.
- Reports saved to disk of both preview and results of an experiment.
- extensible architecture. The framework is designed to be extensible on load and during execution.


Installation
============
To install adgtk please use the following command:

Via PyPi
--------


To install the package, you can use pip:

.. code-block:: console

   pip install adgtk

Manual installation from source
-------------------------------

If you wish to clone the repository and install the package manually, you can do so by following these steps:

1. active your virtual environment.
2. Download the project from https://github.com/fred78108/adgtk.
3. from the root folder of adgtk, run the following command:

.. code-block:: console

   (.venv) $ python -m pip install -e .

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

   Factory
   -------
      $ adgtk-mgr factory                   Lists available factory blueprints
      $ adgtk-mgr factory agent             Lists agent factory blueprints

