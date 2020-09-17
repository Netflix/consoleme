from typing import Dict

from consoleme.config import config
from consoleme.lib.cloud_credential_authorization_mapping.models import (
    CredentialAuthzMappingGenerator,
    RoleAuthorizations,
    user_or_group,
)


class DynamicConfigAuthorizationMappingGenerator(CredentialAuthzMappingGenerator):
    async def generate_credential_authorization_mapping(
        self, authorization_mapping: Dict[user_or_group, RoleAuthorizations]
    ) -> Dict[user_or_group, RoleAuthorizations]:
        """This will list accounts that meet the account attribute search criteria."""
        group_mapping_configuration = config.get("dynamic_config.group_mapping")

        if not group_mapping_configuration:
            return authorization_mapping

        for group, role_mapping in group_mapping_configuration.items():
            if not authorization_mapping.get(group):
                authorization_mapping[group] = RoleAuthorizations.parse_obj(
                    {"authorized_roles": set(), "authorized_roles_cli_only": set()}
                )
            authorization_mapping[group].authorized_roles.update(
                role_mapping.get("roles", [])
            )
            authorization_mapping[group].authorized_roles_cli_only.update(
                role_mapping.get("cli_only_roles", [])
            )
        return authorization_mapping
