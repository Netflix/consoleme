import os
import random
import re
import string
from datetime import datetime
from random import randint
from typing import Dict, List, Optional, Union

import pandas as pd
import ujson as json
from dateutil import parser
from tornado.web import RequestHandler


def str2bool(v: Optional[Union[bool, str]]) -> bool:
    if not v:
        return False
    if type(v) == bool and v is True:
        return True
    return v.lower() in ["true", "True"]


# Yield successive n-sized
# chunks from list l.
def divide_chunks(l, n):
    """
    Yields successive n=zied chunks from list l by looping
    until length l.

    `divide_chunks(["a","b","c","d","e"], 2)` yields:
    ['a', 'b', 'c']
    ['d', 'e']
    """
    for i in range(0, len(l), n):
        yield l[i : i + n]


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


def is_in_group(user_groups: List[str], required_groups: List[str]) -> bool:
    for group in required_groups:
        if group in user_groups:
            return True
    return False


def render_404(handler: RequestHandler, config):
    not_found_path = (
        f"{os.path.dirname(os.path.realpath(__file__))}/../templates/static/404"
    )

    handler.render(
        "error.html",
        page_title="ConsoleMe - 404",
        current_page="error",
        user=handler.user,
        random_404_image=random.choice(os.listdir(not_found_path)),  # nosec
        user_groups=handler.groups,
        config=config,
    )


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
    month = datetime.now().month
    summer = True if month in [6, 7, 8] else False
    dir = "sunglasses" if summer else "nosunglasses"
    file = f"{randint(1, 3)}.png"  # nosec
    return f"/static/logos/{dir}/{file}"


async def generate_random_string(string_length=4):
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(string_length))  # nosec
