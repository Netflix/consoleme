# Export

Weep can generate a command to export credentials to [environment variables](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html) in your shell.

{% hint style="success" %}
Read about [AWS configuration settings and precedence](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html#cli-configure-quickstart-precedence) for information about precedence of credential sources.
{% endhint %}

Here's a basic call to print out the credential export command:

```bash
weep export test_account_user
```

{% hint style="info" %}
Weep will do its best to detect your shell and generate the correct export command. Bash, Zsh, and Fish are currently supported.
{% endhint %}

To automatically export the credentials, just modify your command to be evaluated by the shell:

{% tabs %}
{% tab title="Bash" %}
```bash
eval $(weep export test_account_user)
```
{% endtab %}

{% tab title="Zsh" %}
```bash
eval $(weep export test_account_user)
```
{% endtab %}

{% tab title="Fish" %}
```bash
eval (weep export test_account_user)
```
{% endtab %}
{% endtabs %}

Then you can verify that the credentials are set in your environment:

```bash
env | grep AWS
```

