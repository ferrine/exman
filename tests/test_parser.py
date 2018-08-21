import argparse
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
    parser.parse_args(['--tmp'])
    assert parser.num_ex() == 1
    assert parser.next_ex() == 3


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
    args1 = parser.parse_args('--param '+str_value)
    assert args1.param == py_value
    params = args1.root / exman.parser.yaml_file('params')
    args2 = parser.parse_args('--config {}'.format(params).split())
    assert args2.param == py_value
    assert args1.root != args2.root


def test_validator(root):
    parser = exman.ExParser(root=root)
    parser.add_argument('--param')

    def val1(p):
        return p.param != 'x'

    def val2(p):
        if p.param != 'y':
            return
        else:
            raise ValueError

    def val3(p):
        if p.param != 'z':
            return
        else:
            return 'should be z'

    parser.register_validator(val1, 'should be not x, got {param}')
    parser.register_validator(val2, 'should be not y, got {param}')
    parser.register_validator(val3, 'should be not x, got {param}')
    with pytest.raises(argparse.ArgumentError) as e:
        parser.parse_args('--param ' + 'x')
        assert e.match('got x')
    with pytest.raises(argparse.ArgumentError) as e:
        parser.parse_args('--param ' + 'y')
        assert e.match('got y')
    with pytest.raises(argparse.ArgumentError) as e:
        parser.parse_args('--param ' + 'z')
        assert e.match('got z')
