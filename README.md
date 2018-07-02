# Experiment Manager (exman)

Simple and minimalistic utility to manage many experiments runs and custom analysis of results?

## Why another custom solution?
My job is to do research in Deep Learning and I have dozens of different experiments. Testing one hypothesis usually
required several runs over parameter grid. Plotting and visualizing results is often ad-hoc and updating code producing
output is a kind of overhead. Instead I decided to collect all results in Jupyter notebook and create plots kind of
`interest ~ parameters`. As I said, plotting that is a separate task almost every time. Such tools as
[ModelDB](https://github.com/mitdbg/modeldb) provide you with simple visualizations so that they can be easily
aggregated for model comparison. Testing a hypothesis is not about model comparison and thus requires special treatment.

Visualizing results became a kind of pain, you had to remember a mapping `parameters -> results`, separating results
into different folders made even more mess. I had really bad experience in visualizations. I got that all I need was
to iterate over folder with results and apply the same function to it.

## Main Features
Simple drop in replacement of standard `argparse.ArgumentParser`
```python
#file: main.py
import exman

parser = exman.ExParser(root=exman.simpleroot(__file__))  # `root = ./exman` relative to the main file
parser.add_argument(...)
```

You then just add arguments as you did before without any change.

In command line runs will look also the same:

```
python main.py --param1 foo --param2 bar
```

Things change if you actually run the program. It dumps all the parsed parameters combined with defaults into Yaml style
file into location `root/runs/<name-of-experiment>/params.yaml`. `name-of-experiment` is generic and autocreated on the
fly. For quick look or search there are symlinks in the `index` folder e.g. `root/index/<name-of-experiment>.yaml`.
Since a lot of experiments are created and debugging is sometimes needed, you might want not to create debug
experiments in `runs` folder. For that case you just add `--tmp` flag and new filed will be written to
`root/tmp/<name-of-experiment>` folder. That is convenient as you both do not loose important info about experiment and
results and can restore these symlinks in index by hand if needed.

```
root
|-- runs
|   `-- xxxxxx-YYYY-mm-dd-HH-MM-SS
|       |-- params.yaml
|       `-- ...
|-- index
|   `-- xxxxxx-YYYY-mm-dd-HH-MM-SS.yaml (symlink)
|-- marked
|   `-- <mark>
|       `-- xxxxxx-YYYY-mm-dd-HH-MM-SS.yaml (symlink)
`-- tmp
    `-- xxxxxx-YYYY-mm-dd-HH-MM-SS
        |-- params.yaml
        `-- ...
```


## Rerunning experiment
If you want to reproduce an experiment, you can provide source configuration file in yaml format. For example:

```bash
python main.py --config root/index/<name-of-experiment-to-reproduce>.yaml
```

All the values will be restored from the previous run.

## Loading Pandas
Pandas is a great tool to work with table data. Experiments are the same data and can be loaded in python. So all you
need is to run batch of experiments and open a Jupyter notebook.

```python
import exman
index = exman.Index(exman.simpleroot('/path/to/main.py'))
experiments = index.info()
```

Table has columns `time (datetime64[ns])` of experiment and `root (pathlib.Path)` path to results. Moreover this
table has all other parameters of the experiment. You later can filter/order the results according to them and have
easy-breezy access to results folder and it's content.

```python
for i, ex in experiments.iterrows():
    # do some actions
    # use ex.param for parameters
    # ex.root / 'plot.png' for file paths
```

## Marking experiments
If you like some experiments you can mark them for easier later access.

```
python main.py mark <key> <#ex1> [<#ex2> <#ex3> ...]
```

and later in Jupyter

```python
experiments = index.info('<key>')
```
