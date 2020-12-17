import json  # I don't think I can use ujson here
from datetime import datetime
from decimal import Decimal

from deepdiff.model import PrettyOrderedSet


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (frozenset, set, PrettyOrderedSet)):
            return list(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.timestamp()
        if isinstance(obj, Exception):
            return str(obj)
        return json.JSONEncoder.default(self, obj)
