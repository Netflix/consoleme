# SAML

ConsoleMe can directly authenticate users against an SAML identity provider. We have an example configuration [here](https://github.com/Netflix/consoleme/blob/master/example_config/example_config_saml.yaml).

The settings that must be defined for the SAML flow to work are as follows. You will want to have multiple configurations for your development, test, and production environments with the appropriate URLs for each.

```text
auth:
  get_user_by_saml: true
  set_auth_cookie: true
  force_redirect_to_identity_provider: false
get_user_by_saml_settings:
  # On the provider, set ACS url to https://your_consoleme_url/saml/acs and saml audience to "https://your_consoleme_url/"
  idp_metadata_url: "https://dev-12345.us.auth0.com/samlp/metadata/abcdefg"
  saml_path: example_config/saml_example
  attributes:
    user: user
    groups: groups
    email: email
  saml_settings:
    debug: false
    # IDP settings are not necessary if you provided the get_user_by_saml_settings.idp_metadata_url configuration setting
    # They are provided here as an example
    #    idp:
    #      entityId: https://portal.sso.us-east-1.amazonaws.com/saml/assertion/CUSTOMENDPOINT
    #      singleLogoutService:
    #        binding: urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect
    #        url: https://portal.sso.us-east-1.amazonaws.com/saml/logout/CUSTOMENDPOINT
    #      singleSignOnService:
    #        binding: urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect
    #        url: https://portal.sso.us-east-1.amazonaws.com/saml/assertion/CUSTOMENDPOINT
    #      x509cert: MIIDAz.....
    sp:
      NameIDFormat: urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress
      assertionConsumerService:
        binding: urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST
        url: http://localhost:8081/saml/acs
      entityId: http://localhost:8081
      singleLogoutService:
        binding: urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect
        url: http://localhost:8081/saml/sls
    strict: false
    support:
      emailAddress: support@example.com
      givenName: support_name
      technical:
        emailAddress: technical@example.com
        givenName: technical_name
    organization:
      en-US:
        displayname: ConsoleMe
        name: ConsoleMe
        url: http://localhost:8081
    security:
      authnRequestsSigned: false
      digestAlgorithm: http://www.w3.org/2000/09/xmldsig#sha1
      logoutRequestSigned: true
      logoutResponseSigned: true
      nameIdEncrypted: false
      signMetadata: false
      signatureAlgorithm: http://www.w3.org/2000/09/xmldsig#rsa-sha1
      wantAssertionsEncrypted: false
      wantAssertionsSigned: true
      wantMessagesSigned: true
      wantNameId: true
      wantNameIdEncrypted: false
```

## Steps

These are the general steps to follow when configuring ConsoleMe as a SAML service provider:

1. Update ConsoleMe's configuration with your configuration parameters \(Shown above\)
2. Put your Service Provider certificate and private key in a subdirectory `certs` within the location you specified in your

   `get_user_by_saml_settings.saml_path` configuration value.

   as `sp.crt` and `sp.key`. \(You can generate a certificate and private key with the following command:

   `openssl req -x509 -nodes -sha256 -days 3650 -newkey rsa:2048 -keyout sp.key -out sp.crt`\). The default configuration points here: [example\_config/saml\_example/certs/](https://github.com/Netflix/consoleme/tree/master/example_config/saml_example/certs)

3. Start ConsoleMe with your desired configuration, and test the flow:

```bash
CONFIG_LOCATION=example_config/example_config_saml.yaml python consoleme/__main__.py
```

## Important configuration variables

`get_user_by_saml_settings.idp_metadata_url`: The URL of the SAML Metadata that ConsoleMe can load SAML configuration from.

`get_user_by_saml_settings.saml_path`: Location of SAML settings used by the OneLoginSaml2 library - You'll need to configure the entity ID, IdP Binding urls, and ACS urls in this file

`get_user_by_saml_settings.jwt`: After the user has authenticated, ConsoleMe will give them a jwt valid for the time specified in this configuration, along with the jwt attribute names for the user's email and groups.

`get_user_by_saml_settings.attributes`: Specifies the attributes that we expect to see in the SAML response, including the user's username, groups, and e-mail address

