import configargparse
import argparse
import pathlib
import datetime
import yaml
import yaml.representer
import os
import functools
import itertools
import warnings
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


class Mark(argparse.Action):
    def __init__(self, option_strings, dest=argparse.SUPPRESS, marked_root=None, nargs='+', **kwargs):
        self.marked_root = marked_root
        super().__init__(option_strings, dest=dest, nargs=nargs, type=str, **kwargs)

    def __call__(self, parser: 'ParserWithRoot', namespace, values, option_string=None):
        dest, *selected = values
        if dest in RESERVED_DIRECTORIES:
            raise argparse.ArgumentError('"{}" mark is not allowed'.format(dest))
        if dest.isnumeric():
            raise argparse.ArgumentError('Mark "{}" should not be numeric'.format(dest))
        if not selected:
            raise argparse.ArgumentError('Empty list of runs to mark')
        selected = set(map(int, selected))
        dest = parser.marked / dest
        for run in parser.runs.iterdir():
            ind = int(run.name.split('-', 1)[0])
            if ind in selected:
                if not dest.exists():
                    dest.mkdir()
                (dest / yaml_file(run.name)).symlink_to(run / yaml_file('params'))
                selected.remove(ind)
                print('Created symlink from', dest / run.name, '->', run)
        if selected:
            warnings.warn('runs {} were not found'.format(selected), category=RuntimeWarning)
        parser.exit(0)


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
            if not getattr(self, directory).exists():
                getattr(self, directory).mkdir()

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
    |       `-- xxxxxx-YYYY-mm-dd-HH-MM-SS.yaml (symlink)
    `-- tmp
        `-- xxxxxx-YYYY-mm-dd-HH-MM-SS
            |-- params.yaml
            `-- ...
    ```
    """
    def __init__(self, *args, root=None, zfill=6,
                 args_for_setting_config_path=('--config', ),
                 **kwargs):
        super().__init__(*args, root=root, zfill=zfill,
                         args_for_setting_config_path=args_for_setting_config_path,
                         config_file_parser_class=configargparse.YAMLConfigFileParser,
                         ignore_unknown_config_file_keys=True,
                         **kwargs)
        self.add_argument('--tmp', action='store_true')
        self.subparsers = self.add_subparsers(title='sub commands', parser_class=ParserWithRoot)
        self.__init_mark__()

    def __init_mark__(self):
        mark = self.subparsers.add_parser('mark', root=self.root)
        mark.add_argument('runs', action=Mark,)

    def parse_known_args(self, *args, **kwargs):
        args, argv = super().parse_known_args(*args, **kwargs)
        time = datetime.datetime.now()
        num = self.next_ex_str()
        name = DIR_FORMAT.format(num=num, time=time.strftime(TIME_FORMAT_DIR))
        if args.tmp:
            exroot = self.tmp / name
        else:
            exroot = self.runs / name
        exroot.mkdir()
        args.root = exroot
        yaml_params_path = args.root / PARAMS_FILE
        with yaml_params_path.open('a') as f:
            yaml.dump(args.__dict__, f, default_flow_style=False)
            print("time: '{}'".format(time.strftime(TIME_FORMAT)), file=f)
            print("id:", int(num), file=f)
        print(yaml_params_path.read_text())
        symlink = self.index / yaml_file(name)
        if not args.tmp:
            symlink.symlink_to(yaml_params_path)
            print('Created symlink from', symlink, '->', yaml_params_path)
        return args, argv
