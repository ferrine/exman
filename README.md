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
import exman
import pathlib

parser = exman.ExParser(root=exman.simpleroot(__file__))  # root = ./exman
parser.add_argument(...)
```

You then just add arguments as you did before without any change.

In command line runs will look also the same

```
python main.py --param1 foo --param2 bar
```

Things change if you actually run the program. It dumps all the parsed parameters combined with defaults into Yaml style
file into location `root/runs/<name-of-experiment>/params.yaml`. `name-of-experiment` is generic and autocreated on the
fly. For quick look or search there are symlinks in the `index` folder e.g. `root/index/<name-of-experiment>.yaml`.
Since a lot of experiments are created and debugging is sometimes needed, you might want not to create debug
experiments in `runs` folder. For that case you just add `--tmp` flag and new filed will be written to
`root/tmp/<name-of-experiment>` folder. That is convenient as you both do not loose important info about experiment and
results and can restore the symlinks in index by hand if needed.
