# Custom Authorization \(Internal Plugin\)

If you'd like more flexibility in generating a credential authorization mapping, you can write your own code via an internal plugin. ConsoleMe is shipped with a set of basic default plugins that you can override with your own logic. [This](https://github.com/Netflix/consoleme/blob/master/consoleme/default_plugins/plugins/group_mapping/group_mapping.py#L133) is the function that you'd override to customize your authorization mapping.

