# Role Tags

We highly recommend establishing a set of role tags that will help ConsoleMe determine which users are authorized to get credentials and/or console access. These would be defined in your configuration YAML files \([examples](https://github.com/Netflix/consoleme/tree/master/example_config)\) under the `cloud_credential_authorization_mapping` key.

Here's an example configuration:

```text
cloud_credential_authorization_mapping:
  role_tags:
    enabled: true
    authorized_groups_tags:
      - consoleme-authorized
    authorized_groups_cli_only_tags:
      - consoleme-owner-dl
      - consoleme-authorized-cli-only
```

Once this is set up, you'd define the list of users / groups that are authorized to access the role in your role tags. If multiple users or groups need access to a role, you must delimit them by a colon \(:\). Commas, unfortunately, are not valid characters in tag values.

Here's a role's tag set using the above configuration. This tag set would allow a group or user named `consoleme_admins` and one named `consoleme_users` to get access to this role by both the **CLI** and via ConsoleMe's **web interface.** The users `usera@example.com` and `userb@example.com` would have access to this role's credentials via the CLI only.

![](../../../.gitbook/assets/image%20%281%29.png)

Make sure that ConsoleMe and your administrative users are the only ones able to manipulate these tags. We recommend using an [SCP](role-tagging-service-control-policy-recommended.md) to restrict it.

