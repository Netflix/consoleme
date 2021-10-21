# Local Development \(Auth bypass\)

When developing locally, you can bypass the authentication/authorization flow and override your local user and groups with a configuration like this example:

```yaml
# A development configuration can specify a specific user to impersonate locally.
_development_user_override: consoleme_admin@example.com

# A development configuration can override your groups locally
_development_groups_override:
  - groupa@example.com
  - groupb@example.com
  - configeditors@example.com
  - consoleme_admins@example.com
```

When bypassing the authentication/authorization flow you will need to ensure you have configured your environment for development:
```yaml
environment: dev
development: true
```
