# Policies View

ConsoleMe's Policy View is a datatable showing all of the resources across your environment that we were able to sync from AWS Config, including your organization's IAM roles, S3 buckets, SQS queues, and SNS topics.

For resource types for which ConsoleMe does not offer a native policy editor, we provide a link that will take you to the resource \(or as close as possible\) in the AWS Console.

![](../../.gitbook/assets/image%20%285%29.png)

The policy table is configurable. At Netflix, we show the number of recent Cloudtrail errors associated with our resources, and also provide a link to the internal template of a resource if one exists. These features are not currently implemented in the open source code.

Here's a quick demo of the policies table in action:

{% embed url="https://youtu.be/Rpp3b5lNXTc" caption="" %}

