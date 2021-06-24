# Development Guide

We welcome your PRs and feature enhancements. 

You'll want to create a fork of the ConsoleMe repository, and follow the [Local Quick Start](../quick-start/local-development.md) guide using your fork. 

We recommend using an IDE such as PyCharm or VS Code to get ConsoleMe running in a debug state.

Below is a very basic configuration of ConsoleMe in PyCharm. You'll need to set up the [virtual environment configuration](https://www.jetbrains.com/help/pycharm/creating-virtual-environment.html) yourself.

![](../.gitbook/assets/image%20%2810%29.png)

After your virtual environment is installed, you'll want to install `pre-commit`. ConsoleMe uses pre-commit to enforce code linting and to run our unit tests on commit.

```text
pre-commit install
```

Pre-commit will automatically run across changed files when you run a git commit. You can also force it to run across all files with: 

```text
pre-commit run -a
```

When creating a PR, we highly recommend that you select [`Allow Edits from Maintainers`](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/allowing-changes-to-a-pull-request-branch-created-from-a-fork) on your PR for better collaboration.

After your fork is configured, set Netflix's ConsoleMe as an upstream, create a new commit, write your code, and push it to a branch on your fork.

```text
git remote add upstream https://github.com/Netflix/consoleme.git
git checkout -b your_cool_feature
# Hack hack hack
# git add / git commit your changes
git push -u origin your_cool_feature
```

In the GitHub URL for your branch \( i.e.: https://github.com/YOU/consoleme/pull/new/your\_cool\_feature \), you should have the option to submit a pull request.

