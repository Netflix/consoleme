# Contributing to ConsoleMe

## Reporting issues

Issues can be opened for bugs, feature requests, missing documentation, etc. To create an issue, click [here](https://github.com/Netflix-Skunkworks/consoleme/issues/new).

## Contributing Code and Docs

Before making code changes, [make a fork](https://help.github.com/en/github/getting-started-with-github/fork-a-repo) of the ConsoleMe repository.

```bash
# Clone your fork, substituting your_username for your GitHub username then go into the repo root
git clone git@github.com:your_username/consoleme.git
cd consoleme

# Create a new branch for your changes
git checkout -b my-branch
```

Now you can make your changes and save them. Once you've made changes, added/updated tests, and are ready to upload:

```bash
# Replace file1 with a list of the files you'd like to commit
git add file1
git commit -m "A short description of your change"
git push -u origin my-branch
```

You can now [create a Pull Request](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request).

Once your PR is merged, it is recommended to do some cleanup:

```bash
git checkout master
git pull
git branch -d my-branch  # This would delete the branch locally
git push origin --delete my-branch  # This would delete the remote branch
```

### Keeping your fork up to date

Since your fork is a copy of the repository, you have to keep it in sync with our copy. You can do that by adding our copy as a remote, then pulling the changes from the master branch:

```bash
# From the consoleme repository root, check out your master branch
git checkout master
# Add a remote called upstream
git remote add upstream git@github.com:your_username/consoleme.git
# Pull changes from upstream
git pull upstream master
# Push changes to your fork
git push origin master
```
