# Self-Service IAM Wizard

ConsoleMe's self-service wizard walks your users through the process of requesting the permissions they need, without needing to know the IAM JSON policy syntax.

Step one of the wizard asks the user to identify the name of their application or role requiring permissions. After choosing their role, we show them context about the role that they can confirm before proceeding to the next step.

Step 2 of the wizard offers a configurable set of permission choices in plain English. Users are able to add the permissions they want. Most of the fields requiring a resource ARN offer a typeahead based on the ARNs we know about in your environment.

In Step 3 of the wizard, most users can type in their justification and submit their policy request. Today, these requests will go to your cloud administrators. In the future, we plan to redirect requests to the appropriate owners of the resources that you're requesting access to.

Advanced users can choose to modify the JSON policy generated for their request, and submit the modified request instead.

Here's a feature video:

{% embed url="https://youtu.be/txnYP0BlITo" caption="" %}

