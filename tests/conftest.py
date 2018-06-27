import pytest
import tempfile
import exman


@pytest.fixture
def parser():
    with tempfile.TemporaryDirectory() as tmpdir:
        exparser = exman.ExParser(root=tmpdir)
        exparser.add_argument('--arg1', default=1, type=int)
        exparser.add_argument('--arg2', default=True, type=bool)
        yield exparser
