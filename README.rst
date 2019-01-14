Experiment Manager (exman)
==========================

Simple and minimalistic utility to manage many experiments runs and
custom analysis of results

Why another custom solution?
----------------------------

My job is to do research in Deep Learning and I have dozens of different
experiments. Testing one hypothesis usually required several runs over
parameter grid. Plotting and visualizing results is often ad-hoc and
updating code producing output is a kind of overhead. Instead I decided
to collect all results in Jupyter notebook and create plots kind of
``interest ~ parameters``. As I said, plotting that is a separate task
almost every time. Such tools as
`ModelDB <https://github.com/mitdbg/modeldb>`__ provide you with simple
visualizations so that they can be easily aggregated for model
comparison. Testing a hypothesis is not about model comparison and thus
requires special treatment.

Visualizing results became a kind of pain, you had to remember a mapping
``parameters -> results``, separating results into different folders
made even more mess. I had really bad experience in visualizations. I
got that all I need was to iterate over folder with results and apply
the same function to it.

Installation
------------

.. code:: bash

    pip install -U git+https://github.com/ferrine/exman.git#egg=exman
    # or
    pip install exman

Simple Start
------------

Simple drop in replacement of standard ``argparse.ArgumentParser``

.. code:: python

    #file: main.py
    import exman
    # you should always use `exman.simpleroot(__file__)` unless you want another dir
    parser = exman.ExParser(root=exman.simpleroot(__file__))  # `root = ./exman` relative to the main file
    parser.add_argument(...)

You then just add arguments as you did before without any change.

Best Practices
--------------

Error Handling in main
~~~~~~~~~~~~~~~~~~~~~~

Since 0.0.3 you can use the following context manager. If ``main()``
function fails it will be moved to ``exman/fails``

.. code:: python

    import exman
    # you should always use `exman.simpleroot(__file__)` unless you want another dir
    parser = exman.ExParser(root=exman.simpleroot(__file__))  # `root = ./exman` relative to the main file
    parser.add_argument(...)
    ...
    if __name__ == '__main__':
        args = parser.parse_args()
        with args.safe_experiment:
            # do your stuff
            main(args)

Optional Parameters
~~~~~~~~~~~~~~~~~~~

To avoid issues in `reproducing experiments <#rerunning-experiment>`__
you should consider using ``exman.optional(type)`` for optional
arguments

.. code:: python

    import exman
    # you should always use `exman.simpleroot(__file__)` unless you want another dir
    parser = exman.ExParser(root=exman.simpleroot(__file__))  # `root = ./exman` relative to the main file
    parser.add_argument('--myarg', type=exman.optional(int))

Validators
~~~~~~~~~~

In simple argparser you cant easily validate multiple arguments, it is
easy in Exman. You can create an informative error message

.. code:: python

    import exman
    # you should always use `exman.simpleroot(__file__)` unless you want another dir
    parser = exman.ExParser(root=exman.simpleroot(__file__))  # `root = ./exman` relative to the main file
    parser.add_argument(...)
    # here `p` stands for initial namespace parsed from arguments
    parser.register_validator(lambda p: p.arg1 != p.arg2 or p.arg3 == p.arg4,
                              # next line will be autoformatted for you using .format
                              'You have provided wrong set of arguments: {arg1}, {arg2}, {arg3}, {arg4}')

Marry Pandas with Exman
~~~~~~~~~~~~~~~~~~~~~~~

Pandas is a great tool to work with table data. Experiments are the same
data and can be loaded in python. So all you need is to run batch of
experiments and open a Jupyter notebook.

.. code:: python

    import exman
    index = exman.Index(exman.simpleroot('/path/to/main.py'))
    experiments = index.info()

Table has columns ``time (datetime64[ns])`` of experiment and
``root (pathlib.Path)`` path to results. Moreover this table has all
other parameters of the experiment. You later can filter/order the
results according to them and have easy-breezy access to results folder
and it's content.

.. code:: python

    for i, ex in experiments.iterrows():
        # do some actions
        # use ex.param for parameters
        # ex.root / 'plot.png' for file paths
        ...

Local Configuration
~~~~~~~~~~~~~~~~~~~

You can store local configuration files in your experiment folder. You
should provide the filename to ExParser as well.

.. code:: python

    import exman
    # you should always use `exman.simpleroot(__file__)` unless you want another dir
    parser = exman.ExParser(
        root=exman.simpleroot(__file__),
        default_config_files=['local.cfg']
    )

Local configuration stores globally defined default values, they
override defaults set in main file

Auto Structure
~~~~~~~~~~~~~~

If you want argument specific human friendly directory structure you can
tie specific argument names for that

.. code:: python

    import exman
    # you should always use `exman.simpleroot(__file__)` unless you want another dir
    parser = exman.ExParser(
        root=exman.simpleroot(__file__),
        automark=['arg1', 'constant']
    )
    parser.add_argument('--arg1')

Later you can see your `marked folder <#directory-structure-and-cli>`__
looks like this

::

    exman/marked/arg1/<arg1>/constant/<name-of-experiment>/...

This can be usefull if you work in a team. Write in ``main.py``

.. code:: python

    import exman
    # you should always use `exman.simpleroot(__file__)` unless you want another dir
    parser = exman.ExParser(
        root=exman.simpleroot(__file__),
        automark=['user'],
        # store `user: myuser` content in local.cfg
        default_config_files=['local.cfg']
    )
    parser.add_argument('--user')

After you've done that, your team runs can be stored in a single exman
directory assuming all access rights are correctly set up.

::

    exman/marked/user/<username>/constant/<name-of-experiment>/...

Directory Structure and CLI
---------------------------

In command line runs will look also the same:

::

    python main.py --param1 foo --param2 bar

Things change if you actually run the program. It dumps all the parsed
parameters combined with defaults into Yaml style file into location
``root/runs/<name-of-experiment>/params.yaml``. ``name-of-experiment``
is generic and autocreated on the fly. For quick look or search there
are symlinks in the ``index`` folder e.g.
``root/index/<name-of-experiment>.yaml``. Since a lot of experiments are
created and debugging is sometimes needed, you might want not to create
debug experiments in ``runs`` folder. For that case you just add
``--tmp`` flag and new filed will be written to
``root/tmp/<name-of-experiment>`` folder. That is convenient as you both
do not loose important info about experiment and results and can restore
these symlinks in index by hand if needed.

::

    root
    |-- runs
    |   `-- xxxxxx-YYYY-mm-dd-HH-MM-SS
    |       |-- params.yaml
    |       `-- ...
    |-- fails
    |-- index
    |   `-- xxxxxx-YYYY-mm-dd-HH-MM-SS.yaml (symlink)
    |-- marked
    |   `-- <mark>
    |       `-- xxxxxx-YYYY-mm-dd-HH-MM-SS (symlink)
    |           |-- params.yaml
    |           `-- ...
    `-- tmp
        `-- xxxxxx-YYYY-mm-dd-HH-MM-SS
            |-- params.yaml
            `-- ...

Rerunning experiment
~~~~~~~~~~~~~~~~~~~~

If you want to reproduce an experiment, you can provide source
configuration file in yaml format. For example:

.. code:: bash

    python main.py --config root/index/<name-of-experiment-to-reproduce>.yaml

All the values will be restored from the previous run. You can also
modify old values in ``--config ...`` using

.. code:: bash

    python main.py --config root/index/<name-of-experiment-to-reproduce>.yaml --override-param=new_value

In case you do not want to restore some argument from saved config (it
may be some dynamic setted variable) you should use ``volatile=True`` in
``add_argument``:

.. code:: python

    parser.add_argument('--my_dynamic_id', default=os.environ.get('AUTOSETTED_ID'), volatile=True)

Marking experiments
-------------------

If you like some experiments you can mark them for easier later access.

::

    cd root_of_exman_dir
    exman mark <key> <#ex1> [<#ex2> <#ex3> ...]

and later in Jupyter

.. code:: python

    index = exman.Index(exman.simpleroot('/path/to/main.py'))
    experiments = index.info('<key>')
    # assuming you work in a team and use best practice advice
    user_experiments = index.info('user/username')

Deleting experiments
--------------------

::

    cd root_of_exman_dir
    # delete only index
    exman delete <#ex1> [<#ex2> <#ex3> ...]
    # delete all files
    exman delete --all <#ex1> [<#ex2> <#ex3> ...]
