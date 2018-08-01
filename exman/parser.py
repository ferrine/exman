import configargparse
import argparse
import pathlib
import datetime
import yaml
import yaml.representer
import os
import functools
import itertools
from filelock import FileLock
__all__ = [
    'ExParser',
    'simpleroot',
]


TIME_FORMAT_DIR = '%Y-%m-%d-%H-%M-%S'
TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
DIR_FORMAT = '{num}-{time}'
EXT = 'yaml'
PARAMS_FILE = 'params.'+EXT
FOLDER_DEFAULT = 'exman'
RESERVED_DIRECTORIES = {
    'runs', 'index',
    'tmp', 'marked'
}


def yaml_file(name):
    return name + '.' + EXT


def simpleroot(__file__):
    return pathlib.Path(os.path.dirname(os.path.abspath(__file__)))/FOLDER_DEFAULT


def represent_as_str(self, data, tostr=str):
    return yaml.representer.Representer.represent_str(self, tostr(data))


def register_str_converter(*types, tostr=str):
    for T in types:
        yaml.add_representer(T, functools.partial(represent_as_str, tostr=tostr))


register_str_converter(pathlib.PosixPath, pathlib.WindowsPath)


def str2bool(s):
    true = ('true', 't', 'yes', 'y', 'on', '1')
    false = ('false', 'f', 'no', 'n', 'off', '0')

    if s.lower() in true:
        return True
    elif s.lower() in false:
        return False
    else:
        raise argparse.ArgumentTypeError(s, 'bool argument should be one of {}'.format(str(true + false)))


class ParserWithRoot(configargparse.ArgumentParser):
    def __init__(self, *args, root=None, zfill=6,
                 **kwargs):
        super().__init__(*args, **kwargs)
        if root is None:
            raise ValueError('Root directory is not specified')
        root = pathlib.Path(root)
        if not root.is_absolute():
            raise ValueError(root, 'Root directory is not absolute path')
        if not root.exists():
            raise ValueError(root, 'Root directory does not exist')
        self.root = pathlib.Path(root)
        self.zfill = zfill
        self.register('type', bool, str2bool)
        for directory in RESERVED_DIRECTORIES:
            getattr(self, directory).mkdir(exist_ok=True)
        self.lock = FileLock(str(self.root/'lock'))

    @property
    def runs(self):
        return self.root / 'runs'

    @property
    def marked(self):
        return self.root / 'marked'

    @property
    def index(self):
        return self.root / 'index'

    @property
    def tmp(self):
        return self.root / 'tmp'

    def max_ex(self):
        max_num = 0
        for directory in itertools.chain(self.runs.iterdir(), self.tmp.iterdir()):
            num = int(directory.name.split('-', 1)[0])
            if num > max_num:
                max_num = num
        return max_num

    def num_ex(self):
        return len(list(self.runs.iterdir()))

    def next_ex(self):
        return self.max_ex() + 1

    def next_ex_str(self):
        return str(self.next_ex()).zfill(self.zfill)


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
    def __init__(self, *args, root=None, zfill=6,
                 args_for_setting_config_path=('--config', ),
                 automark=(),
                 **kwargs):
        super().__init__(*args, root=root, zfill=zfill,
                         args_for_setting_config_path=args_for_setting_config_path,
                         config_file_parser_class=configargparse.YAMLConfigFileParser,
                         ignore_unknown_config_file_keys=True,
                         **kwargs)
        self.automark = automark
        self.add_argument('--tmp', action='store_true')

    def _initialize_dir(self, tmp):
        try:
            with self.lock:  # different processes can make it same time, this is needed to avoid collision
                time = datetime.datetime.now()
                num = self.next_ex_str()
                name = DIR_FORMAT.format(num=num, time=time.strftime(TIME_FORMAT_DIR))
                if tmp:
                    absroot = self.tmp / name
                    relroot = pathlib.Path('tmp') / name
                else:
                    absroot = self.runs / name
                    relroot = pathlib.Path('runs') / name
                # this process now safely owns root directory
                # raises FileExistsError on fail
                absroot.mkdir()
        except FileExistsError:  # shit still happens
            return self._initialize_dir(tmp)
        return absroot, relroot, name, time, num

    def parse_known_args(self, *args, **kwargs):
        args, argv = super().parse_known_args(*args, **kwargs)
        absroot, relroot, name, time, num = self._initialize_dir(args.tmp)
        args.root = absroot
        yaml_params_path = args.root / PARAMS_FILE
        rel_yaml_params_path = pathlib.Path('..', 'runs', name, PARAMS_FILE)
        with yaml_params_path.open('a') as f:
            dumpd = args.__dict__.copy()
            dumpd['root'] = relroot
            yaml.dump(dumpd, f, default_flow_style=False)
            print("time: '{}'".format(time.strftime(TIME_FORMAT)), file=f)
            print("id:", int(num), file=f)
        print(yaml_params_path.read_text())
        symlink = self.index / yaml_file(name)
        if not args.tmp:
            symlink.symlink_to(rel_yaml_params_path)
            print('Created symlink from', symlink, '->', rel_yaml_params_path)
        if self.automark and not args.tmp:
            automark_path_part = pathlib.Path(*itertools.chain.from_iterable(
                (mark, str(getattr(args, mark, '')))
                for mark in self.automark))
            markpath = pathlib.Path(self.marked, automark_path_part)
            markpath.mkdir(exist_ok=True, parents=True)
            relpathmark = pathlib.Path('..', *(['..']*len(automark_path_part.parts))) / 'runs' / name
            (markpath / name).symlink_to(relpathmark, target_is_directory=True)
            print('Created symlink from', markpath / name, '->', relpathmark)
        return args, argv
