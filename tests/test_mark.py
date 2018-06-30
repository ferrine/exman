import pytest
import exman

# fixtures:
#   parser: exman.ExParser


def test_mark_warn(parser: exman.ExParser):
    args = parser.parse_args([])
    with pytest.raises(SystemExit), pytest.warns(RuntimeWarning, match=r'runs {2} were not found'):
        parser.parse_args('mark new 1 2')
    assert (parser.marked / 'new' / (args.root.name + '.' + exman.parser.EXT)).exists()
