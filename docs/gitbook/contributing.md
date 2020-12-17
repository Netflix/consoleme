# Contributing

## How to get started

There are ways for anyone to contribute to ConsoleMe and Weep, regardless of technical expertise. Take a look at the [open issues for ConsoleMe](https://github.com/Netflix/consoleme/issues) and [open issues for Weep](https://github.com/Netflix/weep/issues).

Documentation improvements are one of the easiest ways to help out. We can always make our documentation more thorough, intuitive, and accessible, and the best way to do that is for people like you to read through the docs \(and try things out, if you want\). You don't even need to know how to use Git to help with this -- it's as easy as [opening an issue](https://github.com/Netflix/consoleme/issues/new).

## Join the conversation

The project maintainers use Discord for synchronous conversation about ConsoleMe and Weep development. If you don't know where to start, [join our server](https://discord.gg/nQVpNGGkYu) and say hello.

## Reporting issues

We use GitHub issues to keep track of what needs to be done. Issues can be opened for bugs, feature requests, missing documentation, etc.

[Click here](https://github.com/Netflix/consoleme/issues/new) to create an issue for ConsoleMe. [Click here](https://github.com/Netflix/weep/issues/new) to create an issue for Weep.

## Submitting code and documentation changes

Before making code changes, [make a fork](https://help.github.com/en/github/getting-started-with-github/fork-a-repo) of the [ConsoleMe repository](https://github.com/Netflix/consoleme).

```bash
# Clone your fork, substituting your_username for your GitHub username then go into the repo root
git clone git@github.com:your_username/consoleme.git
cd consoleme

# Create a new branch for your changes
git switch -c my-branch
```

Now you can make your changes and save them. Once you've made changes, added/updated tests, and are ready to upload:

```bash
# Replace file1 with a list of the files you'd like to commit
git add file1
git commit -m "A short description of your change"
git push -u origin my-branch
```

### Pre-commit setup

ConsoleMe and Weep use [pre-commit](https://pre-commit.com/) for linting and running tests. Pre-commit can be installed and configured a few different ways:

{% tabs %}
{% tab title="pip" %}
```bash
pip install pre-commit

# Validate your install
pre-commit --version

# Make pre-commit run when you commit (run this once per repo)
pre-commit install
```
{% endtab %}

{% tab title="homebrew" %}
```bash
brew install pre-commit

# Validate your install
pre-commit --version

# Make pre-commit run when you commit (run this once per repo)
pre-commit install
```
{% endtab %}

{% tab title="conda" %}
```bash
conda install -c conda-forge pre-commit

# Validate your install
pre-commit --version

# Make pre-commit run when you commit (run this once per repo)
pre-commit install
```
{% endtab %}
{% endtabs %}

You're not required to run pre-commit locally, but it will make your life much easier since we run it \(and enforce its success\) in our CI. For more information, check out the [pre-commit documentation](https://pre-commit.com/).

### Keeping your fork up to date

Since your fork is a copy of the repository, you have to keep it in sync with our copy. You can do that by adding our copy as a remote, then pulling the changes from the master branch:

```bash
# From the consoleme repository root, check out your master branch
git switch master
# Add a remote called upstream
git remote add upstream git@github.com:Netflix/consoleme.git
# Pull changes from upstream
git pull upstream master
# Push changes to your fork
git push origin master
```

