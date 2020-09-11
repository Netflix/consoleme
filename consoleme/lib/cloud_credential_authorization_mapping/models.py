from typing import Dict, Set

from pydantic import BaseModel

user_or_group = str


class CredentialAuthzMappingGenerator(object):
    """This is a class that should be inherited for generating Cloud Credential Authorization mappings"""

    async def generate_credential_authorization_mapping(
        self,
    ) -> Dict[user_or_group, Dict[str, Set]]:
        """This will list accounts that meet the account attribute search criteria."""
        raise NotImplementedError()


class RoleAuthorizations(BaseModel):
    # roles that the user can get credentials for via CLI. Users will see these roles in the ConsoleMe UI and can
    # receive an authenticated web console url for the role
    authorized_roles: Set[str] = set()
    # roles that the user can get credentials for only via CLI (They won't see these in the consoleme web UI)
    authorized_roles_cli_only: Set[str] = set()


def RoleAuthorizationsDecoder(obj):
    if "authorized_roles" in obj and "authorized_roles_cli_only" in obj:
        return RoleAuthorizations.parse_obj(obj)
    return obj
