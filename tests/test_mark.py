import pytest
import exman

# fixtures:
#   parser: exman.ExParser


def test_mark(parser: exman.ExParser):
    args = parser.parse_args([])
    with pytest.raises(SystemExit):
        parser.parse_args('mark new 1')
    assert (parser.marked / 'new' / (args.root.name + '.' + exman.parser.EXT)).exists()
