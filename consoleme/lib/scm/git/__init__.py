import os
import shutil
import tempfile
from typing import Optional

import git
from asgiref.sync import sync_to_async


class Repository:
    def __init__(self, repo_url, repo_name, git_email):
        self.tempdir = tempfile.mkdtemp()
        self.repo_url = repo_url
        self.git_email = git_email
        self.repo = None
        self.repo_name = repo_name
        self.git = None

    async def clone(self, no_checkout=True, depth: Optional[int] = None):
        args = []
        kwargs = {}
        if no_checkout:
            args.append("-n")
        args.append(self.repo_url)
        if depth:
            kwargs["depth"] = depth
        await sync_to_async(git.Git(self.tempdir).clone)(*args, **kwargs)
        self.repo = git.Repo(os.path.join(self.tempdir, self.repo_name))
        self.repo.config_writer().set_value("user", "name", "ConsoleMe").release()
        if self.git_email:
            self.repo.config_writer().set_value(
                "user", "email", self.git_email
            ).release()
        self.git = self.repo.git
        return self.repo

    async def cleanup(self):
        await sync_to_async(shutil.rmtree)(self.tempdir)
