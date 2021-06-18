from ruamel.yaml import YAML

typ = "rt"
yaml = YAML(typ=typ)
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.representer.ignore_aliases = lambda *data: True
yaml.width = 4096
