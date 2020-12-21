# Configuration

Weep searches for a configuration file in the following locations:

* `./.weep.yaml`
* `~/.weep.yaml`
* `~/.config/weep/.weep.yaml`

You can also specify a config file as a CLI arg:

```text
weep --config somethingdifferent.yaml list
```

Weep supports authenticating to ConsoleMe in either a standalone challenge mode \(ConsoleMe will authenticate the user according to its settings\), or mutual TLS \(ConsoleMe has to be configured to accept mutual TLS\).

In challenge mode, Weep will prompt the user for their username the first time they authenticate, and then attempt to derive their username from their valid/expired JWT on subsequent attempts. You can also specify the desired username in weep's configuration under the `challenge_settings.user` setting as seen in `example-config.yaml`.

Here's an example configuration file:

```yaml
consoleme_url: https://path_to_consoleme:port
authentication_method: mtls # challenge or mtls
server:
  http_timeout: 20
  metadata_port: 9090
  ecs_credential_provider_port: 9091
#challenge_settings: # (Optional) Username can be provided. If it is not provided, user will be prompted on first authentication attempt
#  user: you@example.com
mtls_settings: # only needed if authentication_method is mtls
  old_cert_message: mTLS certificate is too old, please run [refresh command]
  cert: mtls.crt
  key: mtls.key
  cafile: mtlsCA.pem
  insecure: false
  darwin: # weep will look in platform-specific directories for the three files specified above
    - "/run/mtls/certificates"
    - "/mtls/certificates"
    - "$HOME/.mtls/certificates"
    - "$HOME/.mtls"
  linux:
    - "/run/mtls/certificates"
    - "/mtls/certificates"
    - "$HOME/.mtls/certificates"
    - "$HOME/.mtls"
  windows:
    - "C:\\run\\mtls\\certificates"
    - "C:\\mtls\\certificates"
    - "$HOME\\.mtls\\certificates"
    - "$HOME\\.mtls"
metadata:
  routes:
    - path: latest/user-data
    - path: latest/meta-data/local-ipv4
      data: "127.0.0.1"
    - path: latest/meta-data/local-hostname
      data: ip-127-0-0-1.us-west-2.compute.internal
```

