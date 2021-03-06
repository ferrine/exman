import pytest
import tempfile
import pathlib
import exman


@pytest.fixture
def root():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield pathlib.Path(tmpdir)


@pytest.fixture
def parser(root):
    exparser = exman.ExParser(root=root)
    exparser.add_argument("--arg1", default=1, type=int)
    exparser.add_argument("--arg2", default=True, type=bool)
    return exparser
