import exman

# fixtures:
#   parser: exman.ExParser


def test_dirs(parser: exman.ExParser):
    args = parser.parse_args([])
    assert args.root.exists()
    assert args.root.name.startswith('1'.zfill(parser.zfill) + '-')
    assert parser.runs.exists()
    assert parser.index.exists()
    assert (parser.index / (args.root.name + '.' + exman.parser.EXT)).exists()


def test_num(parser: exman.ExParser):
    assert parser.num_ex() == 0
    assert parser.next_ex() == 1
    parser.parse_args([])
    assert parser.num_ex() == 1
    assert parser.next_ex() == 2


def test_params(parser: exman.ExParser):
    args = parser.parse_args('--arg1=10 --arg2=F'.split())
    assert args.arg1 == 10
    assert args.arg2 is False


def test_reuse(parser: exman.ExParser):
    args = parser.parse_args('--arg1=10 --arg2=F'.split())
    params = args.root / ('params.' + exman.parser.EXT)
    args2 = parser.parse_args('--config {}'.format(params).split())
    assert args.arg1 == args2.arg1
    assert args.arg2 == args2.arg2
