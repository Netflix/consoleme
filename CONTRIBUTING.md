# Contributing to ConsoleMe

## Reporting issues

Issues can be opened for bugs, feature requests, missing documentation, etc. To create an issue, click [here](https://github.com/Netflix-Skunkworks/consoleme/issues/new).

## Contributing Code and Docs

To submit a code or documentation changes to ConsoleMe:

```bash
git clone <consoleme repo>
cd consoleme
git checkout -b my-branch
# Make the changes
git add {filename}
git commit -m "Write about your changes"
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
