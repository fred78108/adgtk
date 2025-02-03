=======
Roadmap
=======

As ADGTK is in active development the roadmap is subject to change. The following is a list of features that are planned for the toolkit.

User Experience
===============
For the User Interface the current release is fairly basic. The roadmap for the User Interface includes the following features: 

- Provide a menu driven experience for the CLI when no command is provided.
- Provide a split screen view for the experiment builder.

Experiments
===========
The MVP release assumes a human interaction. For the target state the toolkit will provide at least one mechanism for an Agent to interact with the toolkit in order to create and run experiments.

Envision how language models today can use a tool. This facility will provide the tool for your agent for experiment activities.

Data processing
===============
Although the user can create their own measurements using the FactoryBlueprint pattern their are some core components that are shared such as the Measurement Engine and Set. The current MVP release does not support filtering of data before measuring. The first feature will be therefore to introduce the ability to filter data. This filtering mechanism can then be used across the different components such as the Measurement Set or figures.

- Add the ability to filter data within a measurement set before measuring.
- Improved plots and figures


Projects
========
The current release does not support the concept of a project journal. The project journal will be a place where the user can track the experiments that have been run and the results of those experiments. The journal will be a place where the user can track the progress of the project.

- Add project journal and tracking of experiments. This would be a global data tracking mechanism. Current plan is to use an ~/.adgtk folder for this purpose.
- Add the ability to track the progress of the project.
- Add the ability to report on the different projects.


Performance
===========

- Explore multi-threading / message bus for performance improvements.