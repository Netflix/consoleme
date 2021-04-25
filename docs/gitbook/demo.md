# Demo

We provide a limited-functionality demo of ConsoleMe at [https://demo.consolemeoss.com](https://demo.consolemeoss.com).

After signing in through Google OAuth, you'll be operating as an administrator but you'll be unable to write any changes. For example, you'll be unable to mutate permissions, submit policy requests, or modify dynamic configuration.

You can receive credentials for a few roles after logging in. Note that these roles do not have any permissions.

You can also use these copies of Weep \([Win](https://demo.consolemeoss.com/static/files/windows/weep.exe), [Linux](https://demo.consolemeoss.com/static/files/linux/weep), [Mac](https://demo.consolemeoss.com/static/files/darwin/weep)\) to request and serve credentials locally from the demo site.

{% hint style="info" %}
The versions of Weep provided above have an embedded configuration pointing to [https://demo.consolemeoss.com](https://demo.consolemeoss.com).

ConsoleMe users can compile Weep with a custom embedded configuration for their environment by following the guidance in [Weep's readme](https://github.com/Netflix/weep#embedded-configuration).
{% endhint %}

## Exercises

Authenticate to [https://demo.consolemeoss.com](https://demo.consolemeoss.com), and try the exercises below:

### Use ConsoleMe to log into the AWS Console

1. Visit [https://demo.consolemeoss.com](https://demo.consolemeoss.com)
2. Click "**Sign-In**" next to ConsoleMeUserRoleA
3. Visit [https://demo.consolemeoss.com](https://demo.consolemeoss.com) and click "ConsoleMeUserRoleA" in the Recent Roles view on the top left of the page
4. Visit [https://demo.consolemeoss.com/role/**usera**](https://demo.consolemeoss.com/role/usera) to log in to ConsoleMeUserRoleA directly. This works because you only have one eligible role matching the substring `usera`
5. Visit [https://demo.consolemeoss.com/role/usera?r=**eu-west-1**](https://demo.consolemeoss.com/role/usera?r=eu-west-1)**.** You will be logged in to the  eu-west-1 region
6. Visit [https://demo.consolemeoss.com/role/usera?**redirect=https://console.aws.amazon.com/dynamodb/home?region=us-east-1**](https://demo.consolemeoss.com/role/usera?redirect=https://console.aws.amazon.com/dynamodb/home?region=us-east-1) to be taken directly to the DynamoDB console in us-east-1. Try this for other services.

### Use ConsoleMe's Policy View to be redirected to a specific resource in the AWS Console

1. Click "Roles and Policies" followed by "Policies" in ConsoleMe's header

![](.gitbook/assets/image%20%2812%29.png)

1. Add a filter to the "Tech" field for "ec2"

![](.gitbook/assets/image%20%287%29.png)

1. Click on one of the resource links.
2. You should be redirected to a page with with an error stating that you're eligible for more than one role on the account, and presenting you with a list of roles to select on the account with the resource. Click **Sign**-**In** for one of these roles
3. Voila! You've been taken to the resource, or as close to it as we can get. You won't be able to see much in the AWS console due to the limited permissions provided by the role.

### Walk through ConsoleMe's Self-Service IAM flow

1. Click "Roles and Policies" followed by "Self Service Permissions" in ConsoleMe's header

![](.gitbook/assets/image%20%2811%29.png)

1. Type the name of a role to request permission changes for. For example, if you started typing `consolemeusera`, you'd observe typeahead hints for all roles matching your query
2. Select a role by clicking on the role ARN in the dropdown

![](.gitbook/assets/image%20%2810%29%20%281%29%20%281%29%20%281%29%20%281%29%20%282%29%20%282%29%20%282%29.png)

1. Information about the role should appear in the right pane. Observe this information, and then click **Next** to proceed to Step 2
2. Add multiple sets of permissions here. Most fields should support typeahead.

{% hint style="info" %}
The "**Other**" option in the permissions selection dropdown will allow you to request permissions for different AWS services that we don't have default permission templates for.
{% endhint %}

1. Once you're satisfied with your selections, click **Next**
2. Now you're at Step 3 of the wizard. Click on the **JSON Editor** to review the policy that ConsoleMe has generated for your request. Unfortunately, you won't see any auto-generated cross-account resource policies until the Policy Review page.
3. The next step is to submit your policy for review. As an administrator, you could submit and apply the policy to your resources without an approval. In this restricted demo, neither of these buttons will work due to the limited permissions on the role that ConsoleMe is using.

### Walk through ConsoleMe's Role Cloning feature

1. Click "Roles and Policies" followed by "Create Role" in ConsoleMe's header

![](.gitbook/assets/image%20%289%29.png)

1. Click the "Clone Role" radio button
2. Type "usera" under the source role option. ConsoleMe will provide a typeahead based on the existing roles it knows about.
3. Under "Account ID", start typing in the name or ID of an account ConsoleMe knows about
4. Under "Role name", type in the name of the new role you'd like to create
5. Submit, and rejoice as it spectacularly fails because ConsoleMe is operating in read-only mode. Imagine the feeling you would have gotten if that operation succeeded.

### Use ConsoleMe's policy editor on a role and resource

1. Click "Roles and Policies" followed by "Policies" in ConsoleMe's header
2. Under the "Tech" field, filter for "iam". 
3. Select an IAM role. Observe its inline policies \(If the role you selected has any\), assume role trust policy, managed policies, tags, and issues. 
4. On the inline policies page, try creating a new inline policy. Select different templates from the dropdown menu.

{% hint style="info" %}
ConsoleMe's inline policy templates can be customized to fit the needs of your users.
{% endhint %}

### Download Weep. List your eligible roles, and use Weep to serve credentials locally

1. Download Weep for your platform with an embedded configuration pointing to [https://demo.consolemeoss.com](https://demo.consolemeoss.com) :  [Win](https://demo.consolemeoss.com/static/files/windows/weep.exe), [Linux](https://demo.consolemeoss.com/static/files/linux/weep), [Mac](https://demo.consolemeoss.com/static/files/darwin/weep)
2. Use Weep to list your eligible roles. You'll be required to authenticate to ConsoleMe the first time you do this.

```text
weep list
```

Write credentials to the ~/.aws/credentials file. Note: This will overwrite your default profile credentials if you have that set.

```text
weep file -p default ConsoleMeAppA
# Confirm credentials were written to in ~/.aws/credentials
aws sts get-caller-identity
```

Run Weep in ECS Credential Provider mode, and in another shell, retrieve credentials

Shell 1:

```text
weep ecs_credential_provider
```

Shell 2:

```text
AWS_CONTAINER_CREDENTIALS_FULL_URI=http://localhost:9091/ecs/consolemeappa \
aws sts get-caller-identity
```

Export credentials as environment variables to your current shell

```text
eval $(weep export ConsoleMeAppA)
```

Generate a credential process configuration \(Caution: This will mutate your ~/.aws/config file if you've customized it\)

```text
weep generate_credential_process_config
# Observe changes to your ~/.aws/config file
cat ~/.aws/config
# Test credential usage with a profile name
AWS_PROFILE=arn:aws:iam::844240725092:role/ConsoleMeAppA aws sts get-caller-identity
# Revert your ~/.aws/config file to its previous state
```

