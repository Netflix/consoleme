# Assuming Roles

For commands that support assuming a role, pass the `-A` flag with a role ARN. You can do this as many times as you'd like and the roles will be assumed in the order passed in.

{% hint style="info" %}
**Note:** You must provide the whole ARN for the role\(s\) to be assumed
{% endhint %}

```bash
# Assume otherRole using credentials from exampleRole
weep serve exampleRole -A arn:aws:iam::123456789012:role/otherRole

# Assume otherRole then assume andAnother
weep serve exampleRole -A arn:aws:iam::123456789012:role/otherRole -A arn:aws:iam::123456789012:role/andAnother

# Roles to assume can also be passed as a comma-separated list. This will do the same thing as the previous example
weep serve exampleRole -A arn:aws:iam::123456789012:role/otherRole,arn:aws:iam::123456789012:role/andAnother
```

When using the ECS credential provider, pass the role\(s\) to be assumed as a comma-separated query-string with the key `assume`:

In one shell:

```bash
weep ecs_credential_provider
```

And in a second shell:

```bash
export AWS_CONTAINER_CREDENTIALS_FULL_URI=http://localhost:9091/ecs/consoleme_oss_1?assume=arn:aws:iam::123456789012:role/otherRole,arn:aws:iam::123456789012:role/andAnother

aws sts get-caller-identity
{
    "UserId": "AROA4JEFLERSKVPFT4INI:user@example.com",
    "Account": "123456789012",
    "Arn": "arn:aws:sts::123456789012:assumed-role/andAnother/user@example.com"
}
```

