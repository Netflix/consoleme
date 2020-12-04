# OIDC/OAuth2 \(Tested with Okta\)

ConsoleMe can directly authenticate users against an OIDC identity provider. We have an example configuration [here](https://github.com/Netflix/consoleme/blob/master/example_config/example_config_oidc.yaml). 

The settings that must be defined for the OIDC flow to work are as follows:

```text
auth:
  get_user_by_oidc: true
  force_redirect_to_identity_provider: false
  set_auth_cookie: true

get_user_by_oidc_settings:
  resource: <REPLACE>
  metadata_url: https://dev-123456.okta.com/oauth2/default/.well-known/oauth-authorization-server
  # If you have a metadata URL and it returns JSON with authorization_endpoint, token_endpoint, and jwks_uri, you do
  # not need to specify those values in the configuration.
  #authorization_endpoint: https://dev-123456.okta.com/oauth2/default/v1/authorize
  #token_endpoint: https://dev-123456.okta.com/oauth2/default/v1/token
  #jwks_uri: https://dev-123456.okta.com/oauth2/default/v1/keys
  jwt_verify: true
  jwt_email_key: email
  jwt_groups_key: groups
  grant_type: authorization_code
  id_token_response_key: id_token
  access_token_response_key: access_token
  access_token_audience: "consoleme"

oidc_secrets:
  client_id: <REPLACE>
  secret: <REPLACE>
  client_scope:
    - email
    - groups
    - openid
```



