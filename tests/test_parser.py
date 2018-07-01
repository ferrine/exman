import exman
import pytest
# fixtures:
#   parser: exman.ExParser


def test_dirs(parser: exman.ExParser):
    args = parser.parse_args([])
    assert args.root.exists()
    assert args.root.name.startswith('1'.zfill(parser.zfill) + '-')
    assert parser.runs.exists()
    assert parser.index.exists()
    assert (parser.index / exman.parser.yaml_file(args.root.name)).exists()


def test_num(parser: exman.ExParser):
    assert parser.num_ex() == 0
    assert parser.next_ex() == 1
    parser.parse_args([])
    assert parser.num_ex() == 1
    assert parser.next_ex() == 2


@pytest.mark.parametrize(
    'type,nargs,py_value,str_value',
    [
        (str, None, 'example', 'example'),
        (str, '+', ['example', 'example'], 'example example'),
        (str, None, '1', '1'),
        (str, '+', ['1', '2'], '1 2'),
        (int, None, 1, '1'),
        (int, '+', [1, 2], '1 2'),
        (float, None, 1.1, '1.1'),
        (float, '+', [1., 2.1], '1 2.1'),
        (bool, None, True, '1'),
        (bool, '+', [True, False], 'T F'),
    ]
)
def test_reuse(root, type, nargs, py_value, str_value):
    parser = exman.ExParser(root=root)
    parser.add_argument('--param', nargs=nargs, type=type)
    args = parser.parse_args('--param '+str_value)
    assert args.param == py_value
    params = args.root / exman.parser.yaml_file('params')
    args2 = parser.parse_args('--config {}'.format(params).split())
    assert args2.param == py_value
