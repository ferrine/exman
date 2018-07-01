import pathlib
import pytest
import exman

# fixtures:
#   parser: exman.ExParser


def test_collect(parser: exman.ExParser):
    args = parser.parse_args('--arg1=10 --arg2=F'.split())
    parser.parse_args('--arg1=9 --arg2=t'.split())
    info = exman.Index(parser.root).info()
    assert len(info) == 2
    assert str(info.dtypes.arg2) == 'bool'
    assert str(info.dtypes.arg1) == 'int64'
    assert isinstance(info.root[0], pathlib.Path)
    assert info.root[0] == args.root
    assert str(info.dtypes.time) == 'datetime64[ns]'


def test_list_in_yaml(parser: exman.ExParser):
    parser.add_argument('--list', nargs=2, type=int, default=[1, 3])
    parser.parse_args([])
    namespace = parser.parse_args('--list 1 4'.split())
    assert isinstance(namespace.list, list)
    info = exman.Index(parser.root).info()
    assert isinstance(info.list[0], list)
    assert isinstance(info.list[0][0], int)
    assert isinstance(info.list[1], list)
    assert isinstance(info.list[1][0], int)


def test_marked(parser: exman.ExParser):
    parser.parse_args('--arg1=10 --arg2=F'.split())
    parser.parse_args('--arg1=9 --arg2=t'.split())
    with pytest.raises(SystemExit):
        parser.parse_args('mark new 1')
    info = exman.Index(parser.root).info()
    new = exman.Index(parser.root).info('new')
    assert len(info) == 2
    assert len(new) == 1
    assert new.id[0] == 1
    with pytest.raises(KeyError):
        exman.Index(parser.root).info('missing')

