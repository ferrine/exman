import configargparse
import argparse
import pathlib
import datetime
__all__ = [
    'ExParser'
]


TIME_FORMAT_DIR = '%Y-%m-%d-%H-%M-%S'
TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
DIR_FORMAT = '{num}-{time}'
PARAMS_FILE = 'params.yml'


def str2bool(s):
    true = ('true', 't', 'yes', 'y', 'on', '1')
    false = ('false', 'f', 'no', 'n', 'off', '0')

    if s.lower() in true:
        return True
    elif s.lower() in false:
        return False
    else:
        raise argparse.ArgumentTypeError(s, 'bool argument should be one of {}'.format(str(true + false)))


class ExParser(configargparse.ArgumentParser):
    """
    root +- runs +- 00001-2018-06-27-14-36-21/params.json ...
         |       |- 00002-2018-06-27-14-36-23/params.json ...
         |       |- xxxxx-YYYY-mm-dd-HH-MM-SS/params.json ...
         |
         |- index +- 00001-2018-06-27-14-36-21.json (symlink)
                  |- 00002-2018-06-27-14-36-23.json
                  |- xxxxx-YYYY-mm-dd-HH-MM-SS.json
    """
    def __init__(self, *args, root=None, zfill=6,
                 args_for_setting_config_path=('--config', ),
                 **kwargs):
        super().__init__(*args, args_for_setting_config_path=args_for_setting_config_path,
                         config_file_parser_class=configargparse.YAMLConfigFileParser,
                         **kwargs)
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
        if not self.index.exists():
            self.index.mkdir()

    @property
    def runs(self):
        return self.root / 'runs'

    @property
    def index(self):
        return self.root / 'index'

    def parse_known_args(self, *args, **kwargs):
        args, argv = super().parse_known_args(*args, **kwargs)
        time = datetime.datetime.now()
        num = self.next_ex_str()
        name = DIR_FORMAT.format(num=num, time=time.strftime(TIME_FORMAT_DIR))
        exroot = self.runs / name
        exroot.mkdir()
        args.root = exroot
        yaml_params_path = args.root / PARAMS_FILE
        self.write_config_file(args, [str(yaml_params_path.absolute())])
        with yaml_params_path.open('a') as f:
            print("time: '{}'".format(time.strftime(TIME_FORMAT)), file=f)
            print("root: '{}'".format(exroot), file=f)
        print(yaml_params_path.read_text())
        symlink = self.index / (name + '.cfg')
        symlink.symlink_to(yaml_params_path)
        print('Created symlink from', symlink, '->', yaml_params_path)
        return args, argv

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
