# ADGTK getting started

The overall goal of ADGTK projects is to provide a:
1. A centralized factory that creates both built-in and your objects that you want to register and configure as part of an experiment.
2. Consistent results and measurements across experiments
3. A set of tools for an Agent to interact with and create its own sub-experiments.

## Getting started

### Folder structure and the settings file
The creation of this project provided a minimum set of folders for an experiment.

1. **plugin** is an example module on how you can extend the code base
2. **settings.toml** provides you with the ability to change folder and file names along with some common behavior.
3. **templates** contains Jinja2 templates. These are used for the creation of reports, etc.

Note: Additional folders are created once you take some action such as running an experiment.

### Useful commands

#### Factory operations
To see all groups and types within the factory currently registered. This includes both built-in and your code
```adgtk-mgr -f```

To see only those options in a single group
```adgtk-mgr -F agent```

#### Experiments
To create an experiment definition ```adgt-mgr -b``` to use an interactive mode to create your experiment definition. This definition is stored in the folder as specified in your settings.toml file. The default is experiment-def.  You can also update or create by hand an experiment by simply updating this file that was created in the experiment-def folder.

Once you have created an experiment you can confirm it by ```adgtk-mgr -l``` which will list the available experiments.

To create preview reports and to preview the configuration to the screen use ```adgtk-mgr -P your-experiment-name```. This created a report within the results folder for the experiment and shows on screen the tree of the experiment definition.

and to run the experiment ```adgtk-mgr -R your-experiment-name``` or ```adgtk-mgr -r``` to select which experiment to run.

The ADGTK CLI is designed to work solely in the root of your project. It will navigate to the appropriate folders for whatever action is needed. For experiment operations it is critical therefore that you have a valid settings file and are in the root of your project (this folder).

#### Project management
To create this folder you ran ```adgtk-mgr -C project-name``` and to delete it move out of this directory (up one) and issue ```adgtk-mgr -D project-name``` and it will destroy this project and all the folders, etc.

