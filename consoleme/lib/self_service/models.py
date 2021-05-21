from enum import Enum
from typing import List, Optional

from consoleme.lib.pydantic import BaseModel


class SelfServiceResourceType(Enum):
    AwsIamRole = "AwsIamRole"
    HoneybeeAwsIamRoleTemplate = "HoneybeeAwsIamRoleTemplate"


class SelfServiceTypeaheadModel(BaseModel):
    icon: str
    resource_type: SelfServiceResourceType
    number_of_affected_resources: int
    display_text: str
    account: Optional[str] = None
    details_endpoint: str
    application_name: Optional[str] = None
    resource_identifier: Optional[str] = None


class SelfServiceTypeaheadModelArray(BaseModel):
    typeahead_entries: Optional[List[SelfServiceTypeaheadModel]] = None
