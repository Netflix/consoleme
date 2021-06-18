class BaseCodeRepository:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError

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
    ):
        raise NotImplementedError
