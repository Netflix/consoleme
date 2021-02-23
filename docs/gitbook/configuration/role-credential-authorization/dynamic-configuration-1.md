# Role Authorization through Dynamic Configuration

ConsoleMe administrators can provide users/groups with authorization to retrieve AWS credentials through ConsoleMe's "Dynamic configuration" endpoint. Visit [https://your.consoleme.url/config](https://your.consoleme.url/config) to make updates. Here is an example configuration:

```yaml
group_mapping:
  groupa@example.com:
    roles:
      - arn:aws:iam::123456789012:role/roleA
      - arn:aws:iam::123456789012:role/roleB
  userb@example.com:
    roles:
      - arn:aws:iam::123456789012:role/roleA
```

Read more about ConsoleMe's dynamic configuration [here](../dynamic-configuration.md).

