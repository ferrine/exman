import pathlib
import exman

# fixtures:
#   parser: exman.ExParser


def test_collect(parser: exman.ExParser):
    args1 = parser.parse_args('--arg1=10 --arg2=F'.split())
    args1 = parser.parse_args('--arg1=10 --arg2=F'.split())
    index = exman.Index(parser.root)
    assert len(index.info) == 2
    assert str(index.info.dtypes.arg2) == 'bool'
    assert str(index.info.dtypes.arg1) == 'int64'
    assert isinstance(index.info.root[0], pathlib.Path)
    assert str(index.info.dtypes.time) == 'datetime64[ns]'


def test_list_in_yaml(parser: exman.ExParser):
    parser.add_argument('--list', nargs=2, type=int, default=[1, 3])
    parser.parse_args([])
    parser.parse_args('--list 1 4'.split())
    index = exman.Index(parser.root)
    assert isinstance(index.info.list[0], list)
    assert isinstance(index.info.list[0][0], int)
    assert isinstance(index.info.list[1], list)
    assert isinstance(index.info.list[1][0], int)

