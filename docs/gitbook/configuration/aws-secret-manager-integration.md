# AWS Secret Manager Integration

If you'd like to add secrets to ConsoleMe's configuration, we recommend using our AWS Secrets Manager integration. Using this is simple:

1. Make a YAML file that contains the secrets that you would like to merge into your ConsoleMe configuration. 

```text
oidc_secrets:
  client_id: oidc_client_id
  secret: 12345SuperS3KrET!1
  client_scope:
    - email
    - openid
jwt_secret: "ConsoleMeJwtSigningSecret"
```

2. Add this secret to AWS Secrets Manager

{% hint style="warning" %}
The secret that you store in AWS Secrets Manager **must** be valid YAML.
{% endhint %}

3. Give permissions to your [Central Account](../prerequisites/required-iam-permissions/central-account-consolemeinstanceprofile.md) role \(The role that the ConsoleMe service uses on-instance\) to read your new secret

4. Modify your ConsoleMe Configuration YAML to reference this secret in an `extends` parameter. 

Example:

```text
extends: 
  - AWS_SECRETS_MANAGER:my_secret_name_1
  
auth:
  get_user_by_oidc: true
  set_auth_cookie: true
.... Other configuration
```

5. Deploy ConsoleMe. If you're deploying the vanilla ConsoleMe docker image, you can specify an environment variable with an S3 location that ConsoleMe can download it's configuration from. More details are in the [Configuration](./) section.



