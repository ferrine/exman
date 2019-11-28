import pathlib
import pytest
import exman
import random
import time

# fixtures:
#   parser: exman.ExParser


def test_collect(parser: exman.ExParser):
    args = parser.parse_args("--arg1=10 --arg2=F".split())
    parser.parse_args("--arg1=9 --arg2=t".split())
    info = exman.Index(parser.root).info()
    assert len(info) == 2
    assert str(info.dtypes.arg2) == "bool"
    assert str(info.dtypes.arg1) == "int64"
    assert isinstance(info.root[0], pathlib.Path)
    assert info.root[0] == args.root
    assert str(info.dtypes.time) == "datetime64[ns]"


def test_list_in_yaml(parser: exman.ExParser):
    parser.add_argument("--list", nargs=2, type=int, default=[1, 3])
    parser.parse_args([])
    namespace = parser.parse_args("--list 1 4".split())
    assert isinstance(namespace.list, list)
    info = exman.Index(parser.root).info()
    assert isinstance(info.list[0], list)
    assert isinstance(info.list[0][0], int)
    assert isinstance(info.list[1], list)
    assert isinstance(info.list[1][0], int)


@pytest.mark.parametrize("mark", ["new", "new/21/", "a/a/a/a/a/a/a/"])
def test_marked(parser: exman.ExParser, script_runner, root, mark):
    parser.parse_args("--arg1=10 --arg2=F".split())
    parser.parse_args("--arg1=9 --arg2=t".split())
    run_info = script_runner.run("exman", "mark", mark, "1", cwd=root)
    assert run_info.success
    info = exman.Index(parser.root).info()
    new = exman.Index(parser.root).info(mark)
    assert len(info) == 2
    assert len(new) == 1
    assert new.id[0] == 1
    with pytest.raises(KeyError):
        exman.Index(parser.root).info("missing")


def test_automarked(root: pathlib.Path):
    parser = exman.ExParser(root=root, automark=["arg1"])
    parser.add_argument("--arg1", default=1, type=int)
    parser.add_argument("--arg2", default=True, type=bool)
    parser.parse_args("--arg1=10 --arg2=F".split())
    parser.parse_args("--arg1=9 --arg2=t".split())
    info = exman.Index(parser.root).info()
    arg1_9 = exman.Index(parser.root).info("arg1/9")
    arg1_10 = exman.Index(parser.root).info("arg1/10")
    assert len(info) == 2
    assert len(arg1_9) == 1
    assert arg1_9.id[0] == 2
    assert len(arg1_10) == 1
    assert arg1_10.id[0] == 1


def test_automarked2(root: pathlib.Path):
    parser = exman.ExParser(root=root, automark=["arg1", "arg2"])
    parser.add_argument("--arg1", default=1, type=int)
    parser.add_argument("--arg2", default=True, type=bool)
    parser.parse_args("--arg1=10 --arg2=F".split())
    parser.parse_args("--arg1=9 --arg2=t".split())
    info = exman.Index(parser.root).info()
    arg1_9 = exman.Index(parser.root).info("arg1/9/arg2/True")
    arg1_10 = exman.Index(parser.root).info("arg1/10/arg2/False")
    arg_10_9 = exman.Index(parser.root).info("arg1/")
    assert len(info) == 2
    assert len(arg1_9) == 1
    assert arg1_9.id[0] == 2
    assert len(arg1_10) == 1
    assert arg1_10.id[0] == 1
    assert len(arg_10_9) == 2


def test_automarked3(root: pathlib.Path):
    parser = exman.ExParser(root=root, automark=["test", "arg1", "arg2"])
    parser.add_argument("--arg1", default=1, type=int)
    parser.add_argument("--arg2", default=True, type=bool)
    parser.parse_args("--arg1=10 --arg2=F".split())
    parser.parse_args("--arg1=9 --arg2=t".split())
    info = exman.Index(parser.root).info()
    arg1_9 = exman.Index(parser.root).info("test/arg1/9/arg2/True")
    arg1_10 = exman.Index(parser.root).info("test/arg1/10/arg2/False")
    arg_10_9 = exman.Index(parser.root).info("test/")
    assert len(info) == 2
    assert len(arg1_9) == 1
    assert arg1_9.id[0] == 2
    assert len(arg1_10) == 1
    assert arg1_10.id[0] == 1
    assert len(arg_10_9) == 2


def test_nans(root: pathlib.Path):
    parser = exman.ExParser(root=root, automark=["test", "arg1", "arg2"])
    parser.add_argument("--arg1", default=1, type=int)
    parser.add_argument("--arg2", default=True, type=bool)
    parser.parse_args("--arg1=10 --arg2=F".split())
    parser.parse_args("--arg1=9 --arg2=t".split())
    parser.add_argument("--arg3", default=2, type=int)
    parser.add_argument("--arg4", default="a", type=str)
    parser.parse_args("--arg1=9 --arg2=t".split())
    parser.parse_args("--arg1=9 --arg4=1".split())
    info = exman.Index(parser.root).info()
    # TODO: what is the proper way to process nans???
    # The below appears to be float64
    assert str(info.dtypes["arg3"]) == "float64"
    assert str(info.dtypes["arg4"]) == "object"
    assert info.arg4.iloc[-1] == "1"
