"""Contains the text for when no flag is set"""


intro = f"""
======================================
ADGTK - Agent Data Generation Tool-Kit
======================================

Interaction with ADGTK is done through the command line. It should be run from the root directory of an experiment folder or used to create a new project.

You can use the wizard to create an experiment or hand craft your experiment with YAML or TOML.


For more information please visit the project at http://todo/docs <= UPDATE LINK!

Key definitions
===============

    - project    : A set of folders that contains the experiments and results.
    - experiment : A single definition and associated results from that definition.
    - blueprint  : A set of configurations used to build an experiment and is registered in the factory.
    - sample     : Provides a sample project, a "helloworld" project.


Usage
=====

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
   
Modify the start example
------------------------
(Loads settings1.toml and runs the factory command)

   $ adgtk-mgr --file settings1.toml factory   
"""
