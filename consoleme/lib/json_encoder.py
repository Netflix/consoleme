import json  # I don't think I can use ujson here

from datetime import datetime
from decimal import Decimal

from deepdiff.model import PrettyOrderedSet


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if (
            isinstance(obj, frozenset)
            or isinstance(obj, set)
            or isinstance(obj, PrettyOrderedSet)
        ):
            return list(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.timestamp()
        return json.JSONEncoder.default(self, obj)
