import configargparse
import pandas as pd
import pathlib
import strconv
import json
import functools
import datetime
from .parser import str2bool, TIME_FORMAT
__all__ = [
    'Index'
]


def only_value_error(conv):
    @functools.wraps(conv)
    def new_conv(value):
        try:
            return conv(value)
        except Exception as e:
            raise ValueError from e
    return new_conv


converter = strconv.Strconv()

converter.register_converter('bool', only_value_error(str2bool))
converter.register_converter('time', only_value_error(
    lambda time: datetime.datetime.strptime(time, TIME_FORMAT)
))
converter.register_converter('json', only_value_error(json.loads))
# last resort
converter.register_converter('string', str)


class Index(object):
    def __init__(self, root):
        self.root = pathlib.Path(root)
        self.info = self._collect_info()

    @property
    def runs(self):
        return self.root / 'runs'

    @property
    def index(self):
        return self.root / 'index'

    def _collect_info(self):
        def get_dict(cfg):
            return configargparse.YAMLConfigFileParser().parse(cfg.open('r'))

        def convert_column(col):
            types = list(set(converter.infer(i) for i in col))
            if len(types) == 1 and types[0] is not None:
                return col.apply(converter.get_converter(types[0]))
            else:
                return col
        dataframe = pd.DataFrame.from_records((get_dict(c) for c in self.index.iterdir()))
        dataframe = dataframe.apply(lambda s: convert_column(s))
        return dataframe.assign(root=lambda s: s.root.apply(pathlib.Path))


