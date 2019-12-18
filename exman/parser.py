import configargparse
import argparse
import pathlib
import datetime
import yaml
import yaml.representer
import os
import inputimeout
import sys
import re
import functools
import itertools
import collections
import shutil
import traceback
import git as gitlib
from filelock import FileLock
import contextlib

try:
    # happens in an interactive session
    from termios import error as termios_error
except ImportError:
    termios_error = inputimeout.TimeoutOccurred


__all__ = ["ExParser", "simpleroot", "optional", "ArgumentError"]


TIME_FORMAT_DIR = "%Y-%m-%d-%H-%M-%S"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
DIR_FORMAT = "{num}-{time}"
DIR_PATTERN = re.compile(r"^\d+-\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}")
EXT = "yaml"
PARAMS_FILE = "params." + EXT
DIFF_FILE = "changes.diff"
FOLDER_DEFAULT = "exman"

Validator = collections.namedtuple("Validator", "call,message")
# make this public
ArgumentError = argparse.ArgumentError


def yaml_file(name):
    return name + "." + EXT


def simpleroot(__file__):
    root = pathlib.Path(os.path.dirname(os.path.abspath(__file__))) / FOLDER_DEFAULT
    return root


def represent_as_str(self, data, tostr=str):
    return yaml.representer.Representer.represent_str(self, tostr(data))


def register_str_converter(*types, tostr=str):
    for T in types:
        yaml.add_representer(T, functools.partial(represent_as_str, tostr=tostr))


register_str_converter(pathlib.PosixPath, pathlib.WindowsPath)


@contextlib.contextmanager
def umask_permissions(active=False):
    if active:
        oldmask = os.umask(000)
        yield
        os.umask(oldmask)
    else:
        yield


def str2bool(s, default=None):
    true = ("true", "t", "yes", "y", "on", "1")
    false = ("false", "f", "no", "n", "off", "0")

    if s.lower() in true:
        return True
    elif s.lower() in false:
        return False
    else:
        if default is None:
            raise argparse.ArgumentTypeError(
                s, "bool argument should be one of {}".format(str(true + false))
            )
        else:
            return default


def optional(t):
    def converter(obj):
        if obj is None or obj.lower() in {"none", "null"}:
            return None
        else:
            return t(obj)

    return converter


_ExperimentDirectory = collections.namedtuple(
    "ExperimentDirectory", "absroot, relroot, name, time, num, shared"
)


class ExperimentDirectory(_ExperimentDirectory):
    def permissions_context(self):
        return umask_permissions(self.shared)


class ExmanDirectory(object):
    RESERVED_DIRECTORIES = {"runs", "index", "tmp", "marked", "fails"}

    def __init__(self, root, zfill=6, mode="create", shared=False):
        with umask_permissions(shared):
            assert mode in {"create", "validate"}
            self.root = root
            if root is None:
                raise ValueError("Root directory is not specified")
            root = pathlib.Path(root)
            if mode == "create":
                if not root.is_absolute():
                    raise ValueError(root, "Root directory is not an absolute path")
                os.makedirs(self.root, exist_ok=True)
            if not root.exists():
                raise ValueError(root, "Root directory does not exist")
            self.root = pathlib.Path(root)
            self.zfill = zfill
            if mode == "create":
                for directory in self.RESERVED_DIRECTORIES:
                    getattr(self, directory).mkdir(exist_ok=True)
            else:
                for directory in self.RESERVED_DIRECTORIES:
                    if not getattr(self, directory).exists():
                        raise ValueError(
                            "The provided directory does not seem to be Exman root directory"
                        )

            self.lock = FileLock(str(self.root / "lock"))
            self.shared = shared

    def permissions_context(self):
        return umask_permissions(self.shared)

    @property
    def fails(self):
        return self.root / "fails"

    @property
    def runs(self):
        return self.root / "runs"

    @property
    def marked(self):
        return self.root / "marked"

    @property
    def index(self):
        return self.root / "index"

    @property
    def tmp(self):
        return self.root / "tmp"

    def max_ex(self):
        max_num = 0
        for directory in filter(
            lambda d: DIR_PATTERN.match(d.name),
            itertools.chain(
                self.runs.iterdir(), self.tmp.iterdir(), self.fails.iterdir()
            ),
        ):
            num = int(directory.name.split("-", 1)[0])
            if num > max_num:
                max_num = num
        return max_num

    def num_ex(self):
        return len(
            list(filter(lambda d: DIR_PATTERN.match(d.name), self.runs.iterdir()))
        )

    def next_ex(self):
        return self.max_ex() + 1

    def next_ex_str(self):
        return str(self.next_ex()).zfill(self.zfill)

    def new_directory(self, tmp=False, tag=""):
        try:
            with self.lock, self.permissions_context():
                # different processes can make it same time, this is needed to avoid collision
                time = datetime.datetime.now()
                num = self.next_ex_str()
                name = DIR_FORMAT.format(num=num, time=time.strftime(TIME_FORMAT_DIR))
                if tag:
                    name = name + "-" + str(tag)
                if tmp:
                    absroot = self.tmp / name
                    relroot = pathlib.Path("tmp") / name
                else:
                    absroot = self.runs / name
                    relroot = pathlib.Path("runs") / name
                # this process now safely owns root directory
                # raises FileExistsError on fail
                absroot.mkdir()
        except FileExistsError:  # shit still happens
            return self.new_directory(tmp, tag)
        return ExperimentDirectory(absroot, relroot, name, time, num, self.shared)


class VolatileAwareParser(object):
    def __init__(self, parser, volatile):
        self._parser = parser
        self._volatile = volatile

    def __getattr__(self, item):
        return getattr(self._parser, item)

    def __dir__(self):
        return self._parser.__dir__()

    def parse(self, *args, **kwargs):
        parsed = self._parser.parse(*args, *kwargs)
        for key in self._volatile:
            parsed.pop(key, None)
        return parsed


class ParserWithRoot(ExmanDirectory, configargparse.ArgumentParser):
    def __init__(self, *args, root=None, zfill=6, shared=False, **kwargs):
        ExmanDirectory.__init__(self, root, zfill, mode="create", shared=shared)
        configargparse.ArgumentParser.__init__(self, *args, **kwargs)
        self.register("type", bool, str2bool)


class ExParser(ParserWithRoot):
    """
    Parser responsible for creating the following structure of experiments
    ```
    root
    |-- runs
    |   `-- xxxxxx-YYYY-mm-dd-HH-MM-SS
    |       |-- params.yaml
    |       `-- ...
    |-- index
    |   `-- xxxxxx-YYYY-mm-dd-HH-MM-SS.yaml (symlink)
    |-- marked
    |   `-- <mark>
    |       `-- xxxxxx-YYYY-mm-dd-HH-MM-SS (symlink)
    |           |-- params.yaml
    |           `-- ...
    `-- tmp
        `-- xxxxxx-YYYY-mm-dd-HH-MM-SS
            |-- params.yaml
            `-- ...
    ```
    """

    def __init__(
        self,
        *args,
        root=None,
        zfill=6,
        args_for_setting_config_path=("--config",),
        automark=(),
        git=None,
        git_assert_clean=False,
        **kwargs
    ):
        self._volatile = set()
        super().__init__(
            *args,
            root=root,
            zfill=zfill,
            shared=False,
            args_for_setting_config_path=args_for_setting_config_path,
            config_file_parser_class=configargparse.YAMLConfigFileParser,
            ignore_unknown_config_file_keys=True,
            **kwargs
        )
        self.automark = automark
        self.validators = []
        self.setters = []
        self._init_git(git, git_assert_clean)
        self.add_argument(
            "--tmp",
            action="store_true",
            help="Run experiment in tmp directory, not adding it to index",
        )
        self.add_argument(
            "--git-dirty",
            action="store_true",
            help="Force run experiment not asserting it is clean",
        )
        self.add_argument(
            "--name",
            help="Name for the experiment, will appear as suffix to a directory",
        )

    def _init_git(self, git, git_assert_clean):
        if git is not None or git_assert_clean:
            if git_assert_clean and git is None:
                git = "."
            elif git is True:
                git = "."
            try:
                repo = gitlib.Repo(git)
            except gitlib.InvalidGitRepositoryError as e:
                raise gitlib.InvalidGitRepositoryError(
                    "{}\nto solve the problem, please provide absolute path to ExParser".format(
                        str(e)
                    )
                )
            self.repo = repo
            self.git_assert_clean = git_assert_clean
        else:
            self.repo = None
            self.git_assert_clean = False

    def parse_args(self, *args, **kwargs):
        with umask_permissions(self.shared):
            args = super().parse_args(*args, **kwargs)
            if self.git_assert_clean and not args.git_dirty and self.repo.is_dirty():
                raise RuntimeError("Repository is dirty, please commit changes")
            self.set_additional_params(args)
            self.validate_params(args)

            absroot, relroot, name, time, num, _ = self.new_directory(
                args.tmp, args.name
            )
            args.root = absroot
            yaml_params_path = args.root / PARAMS_FILE
            rel_yaml_params_path = pathlib.Path("..", "runs", name, PARAMS_FILE)
            self.dump_config(args, relroot, time, num, yaml_params_path)
            if self.repo is not None and self.repo.is_dirty():
                self.dump_git_diff(args.root / DIFF_FILE)
            print(yaml_params_path.read_text())
            created_symlinks = []
            if not args.tmp:
                symlink = self.index / yaml_file(name)
                created_symlinks.append(symlink)
                symlink.symlink_to(rel_yaml_params_path)
                print("Created symlink from", symlink, "->", rel_yaml_params_path)
            if self.automark and not args.tmp:
                automark_path_part = pathlib.Path(
                    *itertools.chain.from_iterable(
                        (mark, str(getattr(args, mark, ""))) for mark in self.automark
                    )
                )
                markpath = pathlib.Path(self.marked, automark_path_part)
                markpath.mkdir(exist_ok=True, parents=True)
                relpathmark = (
                    pathlib.Path("..", *([".."] * len(automark_path_part.parts)))
                    / "runs"
                    / name
                )
                (markpath / name).symlink_to(relpathmark, target_is_directory=True)
                created_symlinks.append(markpath / name)
                print("Created symlink from", markpath / name, "->", relpathmark)
            safe_experiment = SafeExperiment(
                self.root, args.root, extra_symlinks=created_symlinks
            )
            args.safe_experiment = safe_experiment
            return args

    def register_validator(
        self, validator: callable, message: str = "validation error"
    ):
        if not callable(validator):
            raise TypeError("validator should be callable")
        self.validators.append(Validator(validator, message))

    def register_setter(self, setter: callable):
        """Use with care"""
        self.setters.append(setter)

    def validate_params(self, params):
        for validator in self.validators:
            _validate(validator, params)

    def set_additional_params(self, params):
        for setter in self.setters:
            setter(params)

    def add_argument(self, *args, volatile=False, **kwargs):
        action = super().add_argument(*args, **kwargs)
        if volatile:
            config_file_keys = self.get_possible_config_keys(action)
            # the key used to save value
            self._volatile.add(config_file_keys[0])
        return action

    @property
    def _config_file_parser(self):
        return self.__config_file_parser

    @_config_file_parser.setter
    def _config_file_parser(self, parser):
        # self._volatile is mutable, changes should affect parser
        self.__config_file_parser = VolatileAwareParser(parser, self._volatile)

    @_config_file_parser.deleter
    def _config_file_parser(self):
        self.__config_file_parser = None

    def dump_git_diff(self, diff_file):
        with open(diff_file, "w") as f:
            f.write(self.repo.git.diff(self.repo.head))

    def dump_config(self, args, relroot, time, num, target_yaml):
        with target_yaml.open("a") as f:
            dumpd = args.__dict__.copy()
            if self.repo is not None:
                dumpd["commit"] = str(self.repo.head.commit)
                dumpd["dirty"] = self.repo.is_dirty()
            dumpd["root"] = relroot
            yaml.dump(dumpd, f, default_flow_style=False)
            print("time: '{}'".format(time.strftime(TIME_FORMAT)), file=f)
            print("id:", int(num), file=f)

    def get_possible_config_keys(self, action):
        keys = super().get_possible_config_keys(action)
        return list(keys) + [action.dest]


def _validate(validator: Validator, params: argparse.Namespace):
    try:
        ret = validator.call(params)
    except argparse.ArgumentError as e:
        # do not override this error
        raise e
    except Exception as e:
        raise argparse.ArgumentError(
            None, validator.message.format(**params.__dict__)
        ) from e
    else:
        if (ret is True) or (ret is None):
            return
        else:
            raise argparse.ArgumentError(
                None, validator.message.format(**params.__dict__)
            )


class _TeeOutput(object):
    def __init__(self, stream, out):
        self.out = pathlib.Path(out)
        self.stream = stream

    def write(self, buffer):
        with self.out.open('a') as f:
            f.write(buffer)
            f.flush()
        self.stream.write(buffer)
        self.flush()

    def flush(self):
        self.stream.flush()

    def close(self):
        pass


class SafeExperiment(ExmanDirectory):
    def __init__(self, root, run, extra_symlinks=(), prompt=False, default=True):
        super().__init__(root, mode="validate")
        self.run = run
        self.extra_symlinks = extra_symlinks
        self.prompt = prompt
        self.default = default

    def __enter__(self):
        self.stdout = _TeeOutput(sys.stdout, self.run / "log.txt")
        self.redirect = contextlib.redirect_stdout(self.stdout)
        self.redirect.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.redirect.__exit__(exc_type, exc_val, exc_tb)
        self.stdout.close()
        if exc_type is not None:
            critical = not issubclass(exc_type, KeyboardInterrupt)
            if not critical and self.prompt:
                default = {True: "yes", False: "no"}[self.default]
                try:
                    ans = inputimeout.inputimeout(
                        "\nmove to fails? ({}): ".format(default), 10
                    )
                except (inputimeout.TimeoutOccurred, termios_error, KeyboardInterrupt):
                    ans = default
                critical = str2bool(ans, self.default)
            if critical:
                shutil.move(self.run, self.fails / self.run.name)
                for link in self.extra_symlinks:
                    os.unlink(link)
                tracefile = self.fails / self.run.name / "traceback.txt"
            else:
                tracefile = self.run / "traceback.txt"
            trace = traceback.format_exception(exc_type, exc_val, exc_tb)
            with tracefile.open("w") as f:
                f.writelines(trace)
            print("\n".join(trace), file=sys.stdout)
            return not critical

    def __call__(self, *, prompt=None, default=None):
        if prompt is not None:
            self.prompt = prompt
        if default is not None:
            self.default = default
        return self
