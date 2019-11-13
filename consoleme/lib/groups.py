from typing import Any

from consoleme.config import config


def does_group_require_bg_check(group_info: Any) -> bool:
    seg_groups_requiring_bg_check = config.get("groups.require_bg_check")
    if (
        group_info.backgroundcheck_required
        or group_info.name in seg_groups_requiring_bg_check
    ):
        return True
    return False


def can_user_request_group_based_on_domain(user: str, group_info: Any) -> bool:
    if not group_info.allow_cross_domain_users:
        user_domain = user.split("@")[1]
        if user_domain != group_info.domain:
            return False
    return True


def get_group_url(group: str) -> str:
    return "{}/accessui/group/{}".format(config.get("url"), group)


def get_accessui_group_url(group):
    return "{}/groups/{}".format(config.get("accessui_url"), group)
