==================
Concept and Design
==================

.. toctree::
   :maxdepth: 1
   
   concept/architecture
   concept/extending

ADGTK is designed to provide an easy to use interface for both a human user as well as an Agent. The primary purpose of this Toolkit is to provide a framework for experimentation with Agents that generate data. The framework provides all the automation needed to excute a scenario while providing the user with both consistent measurements across scenarios as well as tracking and reporting of results.

The spirit and intent of this approach is that a researcher (both human or machine) can craft their own experiments and by using a factory create their own custom components. 

Project
=======

A project is a collection of experiments. It is the highest level of organization in the toolkit. A project is a collection of experiments that are related in some way. For example, a project could be a collection of experiments that are all related to a single research question. To create a project you can create a project from the command line by issuing:

.. code-block:: console

    adgtk-mgr --sample project create project1

Which creates a project called project1. navigating into this folder will allow you to define custom components as well as create and run experiments. 

Experiment
==========

An experiment is a scenario that is run by the toolkit. It is a collection of components that are defined by a file within the experiment definition folder. You can change the folder name in the project.yaml/.toml file. By default the folder is experiment-def. An experiment can be created by hand or it can be created via a wizard. To engage the wizard you can issue the following command:

.. code-block:: console

    adgtk-mgr experiment create experiment1

This will start an interactive wizard that will guide you through the creation of an experiment. It is not required to use the wizard, but it is a helpful tool to get started. To create alternative experiments you can copy the file you created and modify it to suit your needs. For example, changing the prompt across the different files will allow you to create a new experiment that is similar to the original.
 
Factory
=======

The Factory is responsible for creating the components that are used in the experiment. To see a list of available components you can issue the following command:

.. code-block:: console

    adgtk-mgr factory

and if you wanted to see more details about a group such as measurement you can issue the following command:

..  code-block:: console

    adgtk-mgr factory measurement