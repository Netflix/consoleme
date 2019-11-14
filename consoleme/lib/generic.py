import re
from typing import Dict, List, Optional, Union

import pandas as pd
import ujson as json
from dateutil import parser


def str2bool(v: Optional[Union[bool, str]]) -> bool:
    if not v:
        return False
    if type(v) == bool and v is True:
        return True
    return v.lower() in ["true", "True"]


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
