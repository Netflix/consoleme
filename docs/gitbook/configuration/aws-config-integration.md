# AWS Config Integration

ConsoleMe will attempt to sync resources from AWS Config across your accounts. If you haven't enabled AWS Config yet, learn how to set it up [here](https://docs.aws.amazon.com/config/latest/developerguide/gs-console.html). Also keep in mind that AWS Config is not free. Carefully decide which resource types to record.

ConsoleMe will assume a role on each of your accounts, and run a query against AWS Config on the account to gather all resources. ConsoleMe also supports using an AWS Config aggregator, but we don't use it for syncing resources across accounts because queries tend to time out for large organizations

The example configuration below tells ConsoleMe to assume the "ConsoleMe" role on spoke accounts before performing actions, such as querying AWS Config or updating policies for resources on the spoke account:

```text
policies:
  role_name: ConsoleMe
```



