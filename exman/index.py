import configargparse
import pandas as pd
import strconv
import json
import functools
import datetime
import joblib
from . import parser

__all__ = ["Index"]


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


converter = strconv.Strconv(
    converters=[
        ("int", strconv.convert_int),
        ("float", strconv.convert_float),
        ("bool", only_value_error(parser.str2bool)),
        ("time", strconv.convert_time),
        ("datetime", strconv.convert_datetime),
        (
            "datetime1",
            lambda time: datetime.datetime.strptime(time, parser.TIME_FORMAT),
        ),
        ("date", strconv.convert_date),
        ("json", only_value_error(json.loads)),
    ]
)


class Index(parser.ExmanDirectory):
    def __init__(self, root):
        super().__init__(root, mode="validate")

    def info(self, source=None, *, njobs=-1):
        if source is None:
            source = self.index
            files = source.iterdir()
        else:
            source = self.marked / source
            files = source.glob("**/*/" + parser.PARAMS_FILE)

        def get_dict(cfg):
            return configargparse.YAMLConfigFileParser().parse(cfg.open("r"))

        def convert_column(col):
            if any(isinstance(v, str) for v in converter.convert_series(col)):
                return col
            else:
                return pd.Series(
                    converter.convert_series(col), name=col.name, index=col.index
                )

        records = joblib.Parallel(n_jobs=njobs)(
            (joblib.delayed(get_dict)(c) for c in files)
        )

        try:
            df = (
                pd.DataFrame.from_records(records)
                .apply(lambda s: convert_column(s))
                .sort_values("id")
                .assign(root=lambda _: _.root.apply(self.root.__truediv__))
                .reset_index(drop=True)
            )
            cols = df.columns.tolist()
            cols.insert(0, cols.pop(cols.index("id")))
            return df.reindex(columns=cols)
        except FileNotFoundError as e:
            raise KeyError(source.name) from e
