from typing import List

import ujson as json
from asgiref.sync import sync_to_async

from consoleme.config import config
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.redis import RedisHandler
from consoleme.models import RoleModel

aws = get_plugin_by_name(config.get("plugins.aws"))()
account_ids_to_names = aws.get_account_ids_to_names()


async def get_role(account_id: str, role_name: str) -> RoleModel:
    red = await RedisHandler().redis()
    redis_key = config.get("aws.iamroles_redis_key", "IAM_ROLE_CACHE")

    arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    role = await sync_to_async(red.hget)(redis_key, arn)
    if role is not None:
        role_dict = json.loads(role)
        return RoleModel(
            name=role_dict["name"],
            account_id=role_dict["accountId"],
            arn=role_dict["arn"],
            account_name=account_ids_to_names.get(account_id, [None])[0],
        )


async def get_roles_by_account(account_id: str) -> List[RoleModel]:
    roles: List[RoleModel] = []
    red = await RedisHandler().redis()
    redis_key = config.get("aws.iamroles_redis_key", "IAM_ROLE_CACHE")
    for role in await sync_to_async(red.hscan_iter)(redis_key, match=f"*{account_id}*"):
        role_dict = json.loads(role[1])
        roles.append(
            RoleModel(
                name=role_dict["name"],
                account_id=role_dict["accountId"],
                arn=role_dict["arn"],
                account_name=account_ids_to_names.get(account_id, [None])[0],
            )
        )
    return roles
