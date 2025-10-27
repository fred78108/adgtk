==============
Recording data
==============

.. toctree::
   :maxdepth: 1

Logging of data and events are done across a few modules depending on what you are wanting to record. The main areas are:

- adgtk.journals
- adgtk.tracking
- log file

Journals
========
For this version there is only an experiment version but the roadmap includes the idea of a project journal (multiple experiments). The experiment journal is a centralized place to record key data and events that occur during the experiment. This data is used to create the report at the end of the experiment. All the relevent data is also saved to disk.

To use the experiment journal you need to create an instance of the ExperimentJournal class and use the methods for recording. for example:

.. code-block:: python

    from adgtk.journals import ExperimentJournal

    journal = ExperimentJournal()

    # For when you created a new file
    journal.log_data_write(
        description="The new data",
        entry_type="created",
        file_w_path="mydata/new_records.csv")
    
    # and for comments, etc
    journal.add_entry(
        entry_type="comment",
        entry_text="The experiment observed a new trend"),
        component="agent",
        include_time=True)
        
    # And to build a report from this data
    journal.generate_report(experiment_name="my_experiment")
    

Tracking
========

The ADGTK framework has a flexible tracking module for use within your experiment. 


.. code-block:: python

    from adgtk.tracking import PerformanceTracker

    # if you have a journal object pass it and it the metric tracker
    # will add the data write to your report.
    tracker = PerformanceTracker(
        experiment_name="my_experiment",
        component="agent",
        journal=self.journal,
        last_only=False)
    
    # create once the label for the data.
    tracker.register_statistic(label="accuracy")
    tracker.register_statistic(label="loss")

    # and whenever you have data to add
    tracker.add_data(label="accuracy", value=0.82)
    tracker.add_data(label="accuracy", value=0.95)
    tracker.add_data(label="accuracy", value=0.98)
    tracker.add_data(label="loss", value=0.1)

    # and to save the data to disk. The location is based on the init
    # and not something your code needs to track. By ensuring a standard
    # location for the data it makes it easier to find and use later.
    tracker.save_data()
    

Log file
========
.. warning::
    Pending documentation update.

The log is centrally located in the ./logs directory. The file name is based on the name of the experiment. for example, my_experiment is my_experiment.log. The file is not cleared between runs so you can see the history of the experiment. The logging mechanism uses standard Python logging. To use:

.. code-block:: python

    import logging

    logging.info("The experiment started")
    logging.error("The agent failed to complete a task")
    logging.info("The experiment ended early")