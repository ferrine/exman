import configargparse
import argparse
import pathlib
import datetime
import yaml
import yaml.representer
__all__ = [
    'ExParser'
]


TIME_FORMAT_DIR = '%Y-%m-%d-%H-%M-%S'
TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
DIR_FORMAT = '{num}-{time}'
EXT = 'yaml'
PARAMS_FILE = 'params.'+EXT


def represent_as_str(self, data):
    return yaml.representer.Representer.represent_str(self, str(data))


yaml.add_representer(pathlib.PosixPath, represent_as_str)
yaml.add_representer(pathlib.WindowsPath, represent_as_str)


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
        selected = list(map(int, selected))
        dest = parser.marked / dest
        for run in parser.index.iterdir():
            if int(run.name.split('-', 1)[0]) in selected:
                if not dest.exists():
                    dest.mkdir()
                (dest / run.name).symlink_to(run)
                print('Created symlink from', dest / run.name, '->', run)
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
        if not self.runs.exists():
            self.runs.mkdir()
        if not self.runs.exists():
            self.tmp.mkdir()
        if not self.index.exists():
            self.index.mkdir()
        if not self.marked.exists():
            self.marked.mkdir()

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
        for directory in self.runs.iterdir():
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
    root +- runs +- 000001-2018-06-27-14-36-21/params.yaml ...
         |       |- 000002-2018-06-27-14-36-23/params.yaml ...
         |       |- xxxxxx-YYYY-mm-dd-HH-MM-SS/params.yaml ...
         |
         |- index +- 000001-2018-06-27-14-36-21.yaml (symlink)
                  |- 000002-2018-06-27-14-36-23.yaml
                  |- xxxxxx-YYYY-mm-dd-HH-MM-SS.yaml
    """
    def __init__(self, *args, root=None, zfill=6,
                 args_for_setting_config_path=('--config', ),
                 **kwargs):
        super().__init__(*args, root=root, zfill=zfill,
                         args_for_setting_config_path=args_for_setting_config_path,
                         config_file_parser_class=configargparse.YAMLConfigFileParser,
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
        print(yaml_params_path.read_text())
        symlink = self.index / (name + '.' + EXT)
        if not args.tmp:
            symlink.symlink_to(yaml_params_path)
            print('Created symlink from', symlink, '->', yaml_params_path)
        return args, argv
