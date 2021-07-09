import random
import re
import string
from datetime import datetime
from random import randint
from typing import Any, Dict, List, Optional, Union
from urllib.parse import unquote_plus

import pandas as pd
import ujson as json
from dateutil import parser

from consoleme.config import config
from consoleme.exceptions.exceptions import MissingRequestParameter
from consoleme.models import (
    AwsResourcePrincipalModel,
    HoneybeeAwsResourceTemplatePrincipalModel,
)


def str2bool(v: Optional[Union[bool, str]]) -> bool:
    if isinstance(v, bytes):
        v = v.decode()
    if not v:
        return False
    if type(v) is bool and v is True:
        return True
    return v.lower() in ["true", "True"]


# Yield successive n-sized
# chunks from list list_.
def divide_chunks(list_, n):
    """
    Yields successive n=zied chunks from list l by looping
    until length l.

    `divide_chunks(["a","b","c","d","e"], 2)` yields:
    ['a', 'b', 'c']
    ['d', 'e']
    """
    for i in range(0, len(list_), n):
        yield list_[i : i + n]


def generate_html(d: List[Dict[str, Union[str, bool]]]) -> str:
    """
    Pass in a dict with a list of rows to include in a formatted table. This will return the HTML for the table.

    :param d:
    :return:
        html: HTML formatted table
    """
    if not d:
        return
    pd.set_option("display.max_colwidth", -1)
    df = pd.DataFrame(d)
    html = df.to_html(classes=["ui", "celled", "table"], escape=False, index=False)
    return html


def auto_split(s: str) -> List[str]:
    results = []

    for i in s.splitlines():
        results.extend(i.split(","))
    return results


def is_valid_role_arn(arn: str) -> bool:
    # This is valid enough as far as we are concerned.
    if not arn.startswith("arn:aws:iam::"):
        return False
    return True


def regex_filter(
    filter: Dict[str, str], items: List[Dict[str, Union[str, None, bool]]]
) -> List[Dict[str, Union[str, None, bool]]]:
    if filter.get("filter"):
        results = []
        if filter.get("type", "") == "date":
            from_date = None
            to_date = None
            try:
                if filter.get("from_date"):
                    from_date = parser.parse(filter.get("from_date"))
                if filter.get("to_date"):
                    to_date = parser.parse(filter.get("to_date"))
                if not from_date and not to_date:
                    return items
            except:  # noqa
                # Unable to parse date. Return items.
                return results
            for item in items:
                item_date = parser.parse(
                    item.get(filter.get("field"))
                )  # What if invalid date
                if from_date and to_date and from_date <= item_date <= to_date:
                    results.append(item)
                    continue
                if from_date and not to_date and item_date >= from_date:
                    results.append(item)
                    continue
                if to_date and not from_date and item_date <= to_date:
                    results.append(item)
                    continue
            return results
        else:
            regexp = re.compile(r"{}".format(filter.get("filter")), re.IGNORECASE)
            for item in items:
                try:
                    if regexp.search(item.get(filter.get("field"))):
                        results.append(item)
                except re.error:
                    # Regex error. Return no results
                    pass
            return results
    else:
        return items


def is_in_group(
    user: str, user_groups: List[str], required_groups: Union[List[str], str]
) -> bool:
    if isinstance(required_groups, str):
        required_groups = [required_groups]
    for group in required_groups:
        if group in user_groups or user == group:
            return True
    return False


async def write_json_error(message, obj):
    result = {"status": "error", "message": message}
    obj.write(json.dumps(result))
    obj.finish()


async def sort_nested_dictionary_lists(d):
    for k, v in d.items():
        if isinstance(v, list):
            for i in range(0, len(v)):
                if isinstance(v[i], dict):
                    v[i] = await sort_nested_dictionary_lists(v[i])
                d[k] = sorted(v)
        if isinstance(v, dict):
            d[k] = await sort_nested_dictionary_lists(v)
    return d


def is_in_time_range(t, time_range):
    valid_days = time_range.get("days")
    if t.weekday() not in valid_days:
        return False
    valid_start_time = t.replace(
        hour=time_range.get("hour_start", 0),
        minute=time_range.get("minute_start", 0),
        second=0,
        microsecond=0,
    )
    valid_end_time = t.replace(
        hour=time_range.get("hour_end", 0),
        minute=time_range.get("minute_end", 0),
        second=0,
        microsecond=0,
    )
    if t < valid_start_time or t > valid_end_time:
        return False
    return True


async def get_random_security_logo():
    if config.get("consoleme_logo.image"):
        return config.get("consoleme_logo.image")
    month = datetime.now().month
    summer = month in [6, 7, 8]

    dir = "sunglasses" if summer else "nosunglasses"
    file = f"{randint(1, 3)}.png"  # nosec
    return f"/images/logos/{dir}/{file}"


async def generate_random_string(string_length=4):
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(string_length))  # nosec


async def filter_table(filter_key, filter_value, data):
    if not (filter_key and filter_value):
        # Filter parameters are incorrect. Don't filter
        return data
    results = []
    if isinstance(filter_value, str):
        try:
            regexp = re.compile(r"{}".format(str(filter_value).strip()), re.IGNORECASE)
        except:  # noqa
            # Regex is incorrect. Don't filter
            return data

        for d in data:
            try:
                if regexp.search(str(d.get(filter_key))):
                    results.append(d)
            except re.error:
                # Regex error. Return no results
                pass
        return results
    elif (
        isinstance(filter_value, list)
        and len(filter_value) == 2
        and isinstance(filter_value[0], int)
        and isinstance(filter_value[1], int)
    ):
        # Handles epoch time filter. We expect a start_time and an end_time in
        # a list of elements, and they should be integers
        for d in data:
            if filter_value[0] < int(d.get(filter_key)) < filter_value[1]:
                results.append(d)
        return results


async def iterate_and_format_dict(d: Dict, replacements: Dict):
    """
    Iterates through the values of a dictionary (with or without nested dictionaries), and formats values accordingly
    if they exist in the `replacements` dictionary.

    Example args:
        d = {"something": {"nested": "1{thing}1"},
        replacements = {"thing": "toreplace", "thing2": "dontreplace"}
    Returns: {"something": {"nested": "1toreplace1"}


    :param d:
    :param replacements:
    :return:
    """
    for k, v in d.items():
        if isinstance(v, dict):
            await iterate_and_format_dict(v, replacements)
        else:
            try:
                d[k] = v.format(**replacements)
            except KeyError:
                pass
    return d


async def should_force_redirect(req):
    """
    ConsoleMe should only force a 302 redirect for non-XHR requests
    """
    if req.headers.get("X-Requested-With", "") == "XMLHttpRequest":
        return False
    if req.headers.get("Accept") == "application/json":
        return False
    return True


def sort_dict(original):
    """Recursively sorts dictionary keys and dictionary values in alphabetical order"""
    if isinstance(original, dict):
        res = (
            dict()
        )  # Make a new "ordered" dictionary. No need for Collections in Python 3.7+
        for k, v in sorted(original.items()):
            res[k] = v
        d = res
    else:
        d = original
    for k in d:
        if isinstance(d[k], str):
            continue
        if isinstance(d[k], list) and len(d[k]) > 1 and isinstance(d[k][0], str):
            d[k] = sorted(d[k])
        if isinstance(d[k], dict):
            d[k] = sort_dict(d[k])
        if isinstance(d[k], list) and len(d[k]) >= 1 and isinstance(d[k][0], dict):
            for i in range(len(d[k])):
                d[k][i] = sort_dict(d[k][i])
    return d


def un_wrap_json(json_obj: Any) -> Any:
    """Helper function to unwrap nested JSON in the AWS Config resource configuration."""
    # pylint: disable=C0103,W0703,R0911
    # Is this a field that we can safely return?
    if isinstance(json_obj, (type(None), int, bool, float)):  # noqa
        return json_obj
    # Is this a Datetime? Convert it to a string and return it:
    if isinstance(json_obj, datetime):
        return str(json_obj)
    # Is this a Dictionary?
    if isinstance(json_obj, dict):
        decoded = {}
        for k, v in json_obj.items():
            decoded[k] = un_wrap_json(v)
    # Is this a List?
    elif isinstance(json_obj, list):
        decoded = []
        for x in json_obj:
            decoded.append(un_wrap_json(x))
        # Yes, try to sort the contents of lists. This is because AWS does not consistently store list ordering for many resource types:
        try:
            sorted_list = sorted(decoded)
            decoded = sorted_list
        except Exception:  # noqa  # nosec   # If we can't sort then NBD
            pass
    else:
        # Try to load the JSON string:
        try:
            # Check if the string starts with a "[" or a "{" (because apparently '123' is a valid JSON)
            for check_field in {
                "{",
                "[",
                '"{',
                '"[',
            }:  # Some of the double-wrapping is really ridiculous
                if json_obj.startswith(check_field):
                    decoded = json.loads(json_obj)
                    # If we loaded this properly, then we need to pass the decoded JSON back in for all the nested stuff:
                    return un_wrap_json(decoded)
            # Check if this string is URL Encoded - if it is, then re-run it through:
            decoded = unquote_plus(json_obj)
            if decoded != json_obj:
                return un_wrap_json(decoded)
            return json_obj
        # If we didn't get a JSON back (exception), then just return the raw value back:
        except Exception:  # noqa
            return json_obj
    return decoded


def un_wrap_json_and_dump_values(json_obj: Any) -> Any:
    json_obj = un_wrap_json(json_obj)
    for k, v in json_obj.items():
        json_obj[k] = json.dumps(v)
    return json_obj


async def get_principal_friendly_name(principal):
    if isinstance(principal, HoneybeeAwsResourceTemplatePrincipalModel):
        return principal.resource_identifier
    if isinstance(principal, AwsResourcePrincipalModel):
        return principal.principal_arn
    raise MissingRequestParameter("Unable to determine principal")


class Struct:
    def __init__(self, **entries):
        self.__dict__.update(entries)
