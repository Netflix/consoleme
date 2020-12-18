# Policy Request - Review Page

Your cloud administrators \(And eventually your resource owners\) will receive an e-mail to a user's policy request when a user submits it.

The policy request review page shows context about the user and the request, as well as any changes that the user has requested. The user has the ability to update the permissions associated with their request, cancel individual changes within the request, or cancel the entire request.

Your cloud administrators can approve or reject individual changes in the request, or reject the entire request. Approving a change applies it immediately to the resource.

ConsoleMe will naively attempt to auto-generate cross-account resource policies for the request, if required. It will only generate resource policies if the resource is known to be on a different account, and if it is a supported resource type. Today, only S3, SQS, and SNS are supported resource types. We hope to add support for more in the future.

The only difference between cancelling and rejecting a request is that users can cancel their own requests. Only cloud administrators can reject a request. Otherwise, both features are identical.

{% embed url="https://www.youtube.com/watch?v=ayYAVJsifPs" caption="" %}

