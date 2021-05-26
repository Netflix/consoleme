from typing import List, Optional, Union

from consoleme.lib.pydantic import BaseModel
from consoleme.models import (
    AwsIamRolePrincipalModel,
    HoneybeeAwsIamRoleTemplatePrincipalModel,
)


class SelfServiceTypeaheadModel(BaseModel):
    icon: str
    number_of_affected_resources: int
    display_text: str
    account: Optional[str] = None
    details_endpoint: str
    application_name: Optional[str] = None
    principal: Union[AwsIamRolePrincipalModel, HoneybeeAwsIamRoleTemplatePrincipalModel]


class SelfServiceTypeaheadModelArray(BaseModel):
    typeahead_entries: Optional[List[SelfServiceTypeaheadModel]] = None
