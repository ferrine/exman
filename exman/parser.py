import configargparse
import argparse
import pathlib
import datetime
import yaml
import yaml.representer
import os
import functools
import itertools
import collections
import shutil
import traceback
from filelock import FileLock

__all__ = ["ExParser", "simpleroot", "optional"]


TIME_FORMAT_DIR = "%Y-%m-%d-%H-%M-%S"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
DIR_FORMAT = "{num}-{time}"
EXT = "yaml"
PARAMS_FILE = "params." + EXT
FOLDER_DEFAULT = "exman"

Validator = collections.namedtuple("Validator", "call,message")


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


def str2bool(s):
    true = ("true", "t", "yes", "y", "on", "1")
    false = ("false", "f", "no", "n", "off", "0")

    if s.lower() in true:
        return True
    elif s.lower() in false:
        return False
    else:
        raise argparse.ArgumentTypeError(
            s, "bool argument should be one of {}".format(str(true + false))
        )


def optional(t):
    def converter(obj):
        if obj is None or obj.lower() in {"none"}:
            return None
        else:
            return t(obj)

    return converter


class ExmanDirectory(object):
    RESERVED_DIRECTORIES = {"runs", "index", "tmp", "marked", "fails"}

    def __init__(self, root, zfill=6, mode="create"):
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
        for directory in itertools.chain(
            self.runs.iterdir(), self.tmp.iterdir(), self.fails.iterdir()
        ):
            num = int(directory.name.split("-", 1)[0])
            if num > max_num:
                max_num = num
        return max_num

    def num_ex(self):
        return len(list(self.runs.iterdir()))

    def next_ex(self):
        return self.max_ex() + 1

    def next_ex_str(self):
        return str(self.next_ex()).zfill(self.zfill)


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
    def __init__(self, *args, root=None, zfill=6, **kwargs):
        ExmanDirectory.__init__(self, root, zfill, mode="create")
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
        **kwargs
    ):
        self._volatile = set()
        super().__init__(
            *args,
            root=root,
            zfill=zfill,
            args_for_setting_config_path=args_for_setting_config_path,
            config_file_parser_class=configargparse.YAMLConfigFileParser,
            ignore_unknown_config_file_keys=True,
            **kwargs
        )
        self.automark = automark
        self.validators = []
        self.setters = []
        self.add_argument("--tmp", action="store_true")

    def _initialize_dir(self, tmp):
        try:
            with self.lock:  # different processes can make it same time, this is needed to avoid collision
                time = datetime.datetime.now()
                num = self.next_ex_str()
                name = DIR_FORMAT.format(num=num, time=time.strftime(TIME_FORMAT_DIR))
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
            return self._initialize_dir(tmp)
        return absroot, relroot, name, time, num

    def parse_args(self, *args, **kwargs):
        args = super().parse_args(*args, **kwargs)
        self.set_additional_params(args)
        self.validate_params(args)
        absroot, relroot, name, time, num = self._initialize_dir(args.tmp)
        args.root = absroot
        yaml_params_path = args.root / PARAMS_FILE
        rel_yaml_params_path = pathlib.Path("..", "runs", name, PARAMS_FILE)
        dumpd = argparse.Namespace(**args.__dict__)
        self.write_config_file(dumpd, [str(yaml_params_path)])
        print("root: '{}'".format(relroot), file=yaml_params_path.open("a"))
        print(
            "time: '{}'".format(time.strftime(TIME_FORMAT)),
            file=yaml_params_path.open("a"),
        )
        print("id:", int(num), file=yaml_params_path.open("a"))
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


def _validate(validator: Validator, params: argparse.Namespace):
    try:
        ret = validator.call(params)
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


class SafeExperiment(ExmanDirectory):
    def __init__(self, root, run, extra_symlinks=()):
        super().__init__(root, mode="validate")
        self.run = run
        self.extra_symlinks = extra_symlinks

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            shutil.move(self.run, self.fails / self.run.name)
            for link in self.extra_symlinks:
                os.unlink(link)
            with (self.fails / self.run.name / "traceback.txt").open("w") as f:
                f.writelines(traceback.format_exception(exc_type, exc_val, exc_tb))
