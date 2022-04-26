# Dynamic Configuration

ConsoleMe's dynamic configuration endpoint \([https://your-consoleme-url/config\](https://your-consoleme-url/config%29\) allows **administrators** to make changes that will be loaded by all running ConsoleMe instances and Celery hosts in up to 60 seconds.

This configuration is stored as a compressed yaml file in DynamoDB. It is versioned, and tagged by the user who updated it last, when it was last updated, and a compressed form of the configuration.

The namespace of ConsoleMe's dynamic configuration is different than the static configurations \(examples of the static configuration are [here](https://github.com/Netflix/consoleme/blob/master/example_config/)\). This ensures that you won't accidentally overwrite configuration that is critical for ConsoleMe to operate properly. To load dynamic configuration, code must explicitly request attributes in the `dynamic_config` namespace. Examples are [here](https://github.com/Netflix/consoleme/search?q=%22config.get%28%5C%22dynamic_config%22).

ConsoleMe uses dynamic configuration to store the following:

* In addition to using role tags, you can authorize a user or groups to access a role in Dynamic configuration. The code that processes this is defined [here](https://github.com/Netflix/consoleme/blob/master/consoleme/lib/cloud_credential_authorization_mapping/dynamic_config.py). An example configuration is below

```text
group_mapping:
  groupA@example.com
    cli_only_roles:
      - 'arn:aws:iam::123456789012:role/role1InstanceProfile'
    roles:
      - 'arn:aws:iam::123456789012:role/role2'
  userb@example.com:
    cli_only_roles:
      - 'arn:aws:iam::123456789012:role/role2'
      ....
```

* In addition to using role tags, you can authorize a user or groups to access a role in Dynamic configuration. The code that processes this is defined [here](https://github.com/Netflix/consoleme/blob/master/consoleme/lib/cloud_credential_authorization_mapping/dynamic_config.py). An example configuration is below

```text
group_mapping:
  groupA@example.com
    cli_only_roles:
      - 'arn:aws:iam::123456789012:role/role1InstanceProfile'
    roles:
      - 'arn:aws:iam::123456789012:role/role2'
  userb@example.com:
    cli_only_roles:
      - 'arn:aws:iam::123456789012:role/role2'
      ....
```

* We store IAM inline policy permission templates in dynamic configuration. This is where you can add templates that fit your organization's needs, and it will show up in the dropdown menu for the inline policy editor. Here's an example of how you can add templates to your dynamic config:

```yaml
permission_templates:
    -   key: default
        text: Default Template
        value: |-
            {
                "Statement":[
                    {
                        "Action":[
                            ""
                        ],
                        "Effect":"Allow",
                        "Resource": [
                            ""
                        ]
                    }
                ],
                "Version":"2012-10-17"
            }
    -   key: s3write
        text: S3 Write Access
        value: |-
            {
                "Statement":[
                    {
                        "Action":[
                            "s3:ListBucket",
                            "s3:GetObject",
                            "s3:PutObject",
                            "s3:DeleteObject"
                        ],
                        "Effect":"Allow",
                        "Resource":[
                            "arn:aws:s3:::BUCKET_NAME",
                            "arn:aws:s3:::BUCKET_NAME/OPTIONAL_PREFIX/*"
                        ],
                        "Sid":"s3readwrite"
                    }
                ]
            }
...
```

