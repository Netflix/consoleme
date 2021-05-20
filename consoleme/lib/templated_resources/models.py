from typing import List, Optional

from consoleme.lib.pydantic import BaseModel


class TemplateFile(BaseModel):
    name: Optional[str]
    owner: Optional[str]
    include_accounts: Optional[List[str]]
    exclude_accounts: Optional[List[str]]
    number_of_accounts: Optional[int]
    resource: str
    resource_type: str
    repository_name: str
    template_language: str  # terraform|honeybee
    web_path: str
    file_path: str
    content: Optional[str]


class TemplatedFileModelArray(BaseModel):
    templated_resources: List[TemplateFile]
