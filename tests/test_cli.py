import exman
import pytest

# fixtures:
#   parser: exman.ExParser


@pytest.mark.parametrize(
    'mark',
    ['new', 'new/21', 'a/a/a/a/a/a/a']
)
def test_mark(parser: exman.ExParser, script_runner, root, mark):
    script_runner.launch_mode = 'in_process'
    args = parser.parse_args([])
    info = script_runner.run('exman', 'mark', mark, '1', '2', cwd=root)
    assert info.success
    assert (parser.marked / mark / args.root.name).exists()
    assert r'runs {2} were not found' in info.stderr


def test_delete(parser: exman.ExParser, script_runner, root):
    script_runner.launch_mode = 'in_process'
    args = parser.parse_args([])
    assert (parser.runs / args.root.name).exists()
    assert (parser.index / exman.parser.yaml_file(args.root.name)).exists()
    info = script_runner.run('exman', 'delete', '1', '2', cwd=root)
    assert info.success
    assert r'runs {2} were not found' in info.stderr
    assert not (parser.index / exman.parser.yaml_file(args.root.name)).exists()
    assert (parser.runs / args.root.name).exists()


def test_delete_all(parser: exman.ExParser, script_runner, root):
    script_runner.launch_mode = 'in_process'
    args = parser.parse_args([])
    assert (parser.runs / args.root.name).exists()
    assert (parser.index / exman.parser.yaml_file(args.root.name)).exists()
    info1 = script_runner.run('exman', 'delete', '--all', '1', '2', cwd=root)
    assert info1.success
    assert r'runs {2} were not found' in info1.stderr
    assert not (parser.index / exman.parser.yaml_file(args.root.name)).exists()
    assert not (parser.runs / args.root.name).exists()
