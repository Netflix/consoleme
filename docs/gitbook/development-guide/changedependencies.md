# Managing Dependencies

To know about the required dependencies, their minimum required versions check the `requirements*.txt` files. Whenever we pin to a specific version in `requirements*.in`, we add a comment explaining why we are doing so. We also have comments on their use.

All the required dependencies for running pip-compile are in pip-tools \([https://github.com/jazzband/pip-tools](https://github.com/jazzband/pip-tools)\) which installs pip-compile command.

## To install or update all dependencies

**Note** : The pip-compile command lets you compile a `requirements*.txt` from your dependencies, specified in either `setup.py` or `requirements*.in`. So, ensure you don’t have `requirements.txt` if you compile `setup.py` or `requirements*.in` from scratch, otherwise, it might interfere. You can also specify a file name other than `requirements.txt` in the following command.

To compile all dependencies run

```text
pip-compile --output-file requirements.txt requirements.in
```

To update all dependencies; Install GNU Make and periodically run

```text
make up-reqs
```

To install all dependencies to your local environment run

```text
pip-sync requirements*.txt
```

## To add a specific new dependency

To compile a specific dependency run

```text
pip-compile --output-file requirements.txt requirements.in [package_name] --no-emit-index-url
```

Replace `[package_name]` with the dependency name you want from `requirements.txt` file.

Whenever we pin to a specific version in `requirements*.in`, we add a comment explaining why we are doing so. You can also specify the version you want to compile by running.

```text
pip-compile --output-file requirements.txt [package_name]==[package_version] --no-emit-index-url
```

Example of `bcrypt` package

```text
pip-compile --output-file requirements.txt bcrypt==3.2.0 --no-emit-index-url
```

## To update a specific dependency

**Note** : Make sure you check the `requirements*.in` file comments before you change the version.

To update a specific package to the latest version use the `--upgrade-package` or `-P` flag:

```text
pip-compile --output-file requirements.txt --upgrade-package [package_name]
```

Replace `[package_name]` with the dependency name you want from `requirements.txt` file.

Whenever we pin to a specific version in `requirements*.in`, we add a comment explaining why we are doing so. You can also specify the version you want to upgrade to by running.

```text
pip-compile --output-file requirements.txt --upgrade-package [package_name]==[package_version]
```

Example of `bcrypt` package

```text
pip-compile --output-file requirements.txt --upgrade-package bcrypt==3.2.0
```

You can combine `--upgrade` and `--upgrade-package` in one command, to provide constraints on the allowed upgrades. For example to upgrade all packages whilst constraining `bcrypt` to the latest version less than 3.0:

```text
pip-compile --output-file requirements.txt --upgrade --upgrade-package 'bcrypt<3.0'
```

