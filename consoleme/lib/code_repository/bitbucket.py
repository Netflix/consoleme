from atlassian import Bitbucket

from consoleme.lib.code_repository.base import BaseCodeRepository


class BitBucketCodeRepository(BaseCodeRepository):
    def __init(self, *args, **kwargs):
        self.bitbucket = Bitbucket(
            url=kwargs["url"],
            username=kwargs["username"],
            password=kwargs["password"],
        )

    async def create_pull_request(
        self,
        source_project: str,
        source_repo: str,
        dest_project: str,
        dest_repo: str,
        branch_name: str,
        main_branch_name: str,
        commit_title: str,
        commit_message: str,
    ) -> str:
        pull_request = self.bitbucket.open_pull_request(
            source_project,
            source_repo,
            dest_project,
            dest_repo,
            branch_name,
            main_branch_name,
            commit_title,
            commit_message,
        )
        pull_request_url = pull_request["links"]["self"][0]["href"]
        return pull_request_url
