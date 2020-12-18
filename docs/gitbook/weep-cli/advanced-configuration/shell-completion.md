# Shell Completion

Weep can automatically generate shell completion scripts for Bash, Zsh, and Fish.

{% tabs %}
{% tab title="Bash" %}
```bash
source <(weep completion bash)
```

To load completions for each session, execute this command once:

```text
# Linux:
weep completion bash > /etc/bash_completion.d/weep
# MacOS:
weep completion bash > /usr/local/etc/bash_completion.d/weep
```
{% endtab %}

{% tab title="Zsh" %}
If shell completion is not already enabled in your environment you will need to enable it. You can execute the following once:

```bash
echo "autoload -U compinit; compinit" >> ~/.zshrc
```

To load completions for each session, execute this command once:

```bash
weep completion zsh > "${fpath[1]}/_weep"
```

You will need to start a new shell for this setup to take effect.
{% endtab %}

{% tab title="Fish" %}
```bash
weep completion fish | source
```

To load completions for each session, execute this command once:

```bash
weep completion fish > ~/.config/fish/completions/weep.fish
```
{% endtab %}
{% endtabs %}

