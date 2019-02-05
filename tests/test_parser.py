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


def test_safe_experiment(root):
    parser = exman.ExParser(root=root)
    args = parser.parse_args([])
    with pytest.raises(ValueError), args.safe_experiment:
        raise ValueError('funny exception')
    assert not (parser.index / exman.parser.yaml_file(args.root.name)).exists()
    assert not args.root.exists()
    assert (parser.fails / args.root.name).exists()
    assert (parser.fails / args.root.name / 'traceback.txt').exists()
    assert 'funny exception' in (parser.fails / args.root.name / 'traceback.txt').read_text()


def test_safe_experiment_tmp(root):
    parser = exman.ExParser(root=root)
    args = parser.parse_args(['--tmp'])
    with pytest.raises(ValueError), args.safe_experiment:
        raise ValueError('funny exception')
    assert not (parser.index / exman.parser.yaml_file(args.root.name)).exists()
    assert not args.root.exists()
    assert (parser.fails / args.root.name).exists()
    assert (parser.fails / args.root.name / 'traceback.txt').exists()
    assert 'funny exception' in (parser.fails / args.root.name / 'traceback.txt').read_text()


def test_setters(root):
    parser = exman.ExParser(root=root)
    parser.register_setter(lambda p: p.__dict__.update(arg1=1))
    args = parser.parse_args(['--tmp'])
    assert args.arg1 == 1


def test_dest_taken_in_account_while_reuse(root):
    parser = exman.ExParser(root=root)
    parser.add_argument('--arg1', dest='arg2', default='1')
    args1 = parser.parse_args(['--arg1', '2'])
    params = args1.root / exman.parser.yaml_file('params')
    args2 = parser.parse_args('--config {}'.format(params).split())
    assert args2.arg2 == '2'


def test_volatile(root):
    parser = exman.ExParser(root=root)
    parser.add_argument('--arg1', dest='arg1', default='1')
    parser.add_argument('--arg2', dest='arg2', default='1', volatile=True)
    args1 = parser.parse_args(['--arg1', '2', '--arg2', '2'])
    params = args1.root / exman.parser.yaml_file('params')
    args2 = parser.parse_args('--config {}'.format(params).split())
    assert args2.arg1 == '2'
    assert args2.arg2 == '1'


def test_optional(root):
    parser = exman.ExParser(root=root)
    parser.add_argument('--arg1', type=exman.optional(int), dest='arg1', default=None)

    args1 = parser.parse_args(['--arg1', '2'])
    params = args1.root / exman.parser.yaml_file('params')
    args2 = parser.parse_args('--config {}'.format(params).split())
    assert args2.arg1 == 2
    args3 = parser.parse_args([])
    params = args3.root / exman.parser.yaml_file('params')
    args4 = parser.parse_args('--config {}'.format(params).split())
    assert args4.arg1 is None


def test_dest(root):
    parser = exman.ExParser(root=root)
    parser.add_argument('--arg1', type=exman.optional(int), dest='arg2', default=None)

    args1 = parser.parse_args(['--arg1', '2'])
    params = args1.root / exman.parser.yaml_file('params')
    args2 = parser.parse_args('--config {}'.format(params).split())
    assert args2.arg2 == 2
