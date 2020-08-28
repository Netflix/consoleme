---
id: OIDC
title: OpenID Connect/OAuth 2.0 Configuration
---

The example OpenID Connect configuration for ConsoleMe exists in the ConsoleMe repository at `docker/example_config_oidc.yaml`.

ConsoleMe's configuration needs to specify one authentication method
(`auth.get_user_by_oidc` must be `true`).

`get_user_by_saml_settings.saml_path` must point to the configuration path for OneLogin's SAML Python Toolkit.
An example configuration exists [here](https://github.com/Netflix/consoleme/tree/master/docker/saml_example).

ConsoleMe expects to receive attributes in the SAML Response from the IdP which identify the user and their groups.
These attribute names can be customized by the
`get_user_by_saml_settings.attributes.email`, and `get_user_by_saml_settings.attributes.groups` keys.

Here is the essential part of the SAML configuration:

```
auth:
  get_user_by_saml: true
  set_auth_cookie: true

get_user_by_saml_settings:
  saml_path: docker/saml_example
  jwt:
    expiration_hours: 1
    email_key: email
    groups_key: groups
  attributes:
    groups: groups
    email: email
```
