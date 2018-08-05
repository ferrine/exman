import configargparse
import pandas as pd
import pathlib
import strconv
import json
import functools
import datetime
from . import parser
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


def none2none(none):
    if none is None:
        return None
    else:
        raise ValueError


converter = strconv.Strconv(converters=[
    ('int', strconv.convert_int),
    ('float', strconv.convert_float),
    ('bool', only_value_error(parser.str2bool)),
    ('time', strconv.convert_time),
    ('datetime', strconv.convert_datetime),
    ('datetime1', lambda time: datetime.datetime.strptime(time, parser.TIME_FORMAT)),
    ('date', strconv.convert_date),
    ('json', only_value_error(json.loads))
])


class Index(object):
    def __init__(self, root):
        self.root = pathlib.Path(root)

    @property
    def index(self):
        return self.root / 'index'

    @property
    def marked(self):
        return self.root / 'marked'

    def info(self, source=None):
        if source is None:
            source = self.index
            files = source.iterdir()
        else:
            source = self.marked / source
            files = source.glob('**/*/'+parser.PARAMS_FILE)

        def get_dict(cfg):
            return configargparse.YAMLConfigFileParser().parse(cfg.open('r'))

        def convert_column(col):
            types = set(converter.infer(i) for i in col)
            types -= {None}
            if len(types) == 1:
                return pd.Series(converter.convert_series(col), name=col.name, index=col.index)
            else:
                return col
        try:
            return (pd.DataFrame
                    .from_records((get_dict(c) for c in files))
                    .apply(lambda s: convert_column(s))
                    .sort_values('id')
                    .assign(root=lambda df: df.root.apply(self.root.__truediv__))
                    .reset_index(drop=True))
        except FileNotFoundError as e:
            raise KeyError(source.name) from e
