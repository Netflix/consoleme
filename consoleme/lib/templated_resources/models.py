from typing import List, Optional

from consoleme.lib.pydantic import BaseModel


class TemplateFile(BaseModel):
    name: Optional[str]
    owner: Optional[str]
    include_accounts: Optional[List[str]]
    exclude_accounts: Optional[List[str]]
    resource: str
    resource_type: str
    template_language: str  # terraform|honeybee
    web_path: str
    file_path: str
    content: Optional[str]


class TemplatedResourceModelArray(BaseModel):
    templated_resources: List[TemplateFile]
