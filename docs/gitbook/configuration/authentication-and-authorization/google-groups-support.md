# Retrieving Google Groups

ConsoleMe can retrieve your google groups information and use it to authorize roles for an entire group. But unfortunately, google doesn't provide groups information via access tokens. To get google groups to work you will need to complete a few extra steps.

> These steps have been tested to work with ALB auth + google workflow for ConsoleMe.

## Setup a service account in GCP

1. Login to the google account in which the GCP app for consoleme was setup
2. Go to the [service accounts](https://console.cloud.google.com/iam-admin/serviceaccounts) page and select your consoleme project
3. Click on **create service account** option
4. Fill in the details but skip the optional steps
5. Click **Done**

## Enable Domain wide delegation for the service account

1. Click on the name of the service account created above
2. Check the box which says **Enable Google Domain-wide Delegation**

This will assign a unique client ID for the service account which will be used in a later step.

## Generate service account keys

1. On the service account page, go to the **Keys** tab
2. Click on **Create new key** under the **Add key** dropdown
3. Select the **JSON** type key option and click **Create**

This will generate a public-private key pair which will be used for establishing the identity of the service account outside of Google cloud, in our case ConsoleMe. The service account key file will be downloaded to your computer automatically.

Sample structure is shown below:

```javascript
{
  "type": "service_account",
  "project_id": "<project-id>",
  "private_key_id": "<key-id>",
  "private_key": "-----BEGIN PRIVATE KEY-----\n<private-key>\n-----END PRIVATE KEY-----\n",
  "client_email": "<service-account-email>",
  "client_id": "<client-id>",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://accounts.google.com/o/oauth2/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/<service-account-email>"
}
```

## Enable Admin SDK API for ConsoleMe

1. Visit [Admin SDK](https://console.cloud.google.com/apis/library/admin.googleapis.com) link and select the consoleme project
2. Enable the **Admin SDK API**

## Delegate domain-wide authority to your service account

> The following steps require google admin account access. This may/maynot be the google account that you have setup consoleme in.

1. Go to the [admin console](http://admin.google.com/) for your google workspace domain
2. In the **Domain wide delegation** pane, select **Manage Domain Wide Delegation**
3. Click **Add new**
4. In the **Client ID** field, enter the client ID obtained from the service account creation steps above
5. In the **OAuth Scopes** field, enter a comma-delimited list of the following scopes

```text
https://www.googleapis.com/auth/admin.directory.group
https://www.googleapis.com/auth/admin.reports.audit.readonly
```

## ConsoleMe static config changes

1. Add the contents of the key file that was downloaded while generating service account keys as a dictionary in your consoleme static config.
2. There are newline characters in the private\_key inside the service account key. You have to split the line on the newline character when you paste it into the YAML file.
3. If you're using the Google Workspace then make sure that credential\_subject is the email of workspace admin.

Your static config should look similar to this:

```yaml
google:
  credential_subject:
    <yourdomain.com>: <admin.email@yourdomain.com>
  service_key_dict:
    type: service_account
    project_id: <project-id>
    private_key_id: <key-id>
    private_key: |-
      -----BEGIN PRIVATE KEY-----
              <private-key>
      -----END PRIVATE KEY-----
    client_email: <service-account-email>
    client_id: <client-id>
    auth_uri: https://accounts.google.com/o/oauth2/auth
    token_uri: https://oauth2.googleapis.com/token
    auth_provider_x509_cert_url: https://www.googleapis.com/oauth2/v1/certs
    client_x509_cert_url: https://www.googleapis.com/robot/v1/metadata/x509/<service-account-email>

auth:
  get_user_by_aws_alb_auth: true
  get_groups_from_google: true
  set_auth_cookie: true
  extra_auth_cookies:
    - AWSELBAuthSessionCookie-0
```

1. Re-deploy your consoleme instance \(if you have **static config reload** option enabled then re-deployment is not needed\)
2. Clear your existing browser cookies.

ConsoleMe should now be able to get groups info from Google IDP.

## Check if group info is properly retrieved

One way to check is by decoding the JWT in the **consoleme\_auth** cookie.

1. Copy the contents of the **consoleme\_auth** cookie from your consoleme domain
2. Go to [jwt.io](https://github.com/Netflix/consoleme/tree/6423fcfc7f089b5f021608c48e7c04f9d1435221/docs/gitbook/configuration/authentication-and-authorization/jwt.io) and paste in the contents of the cookie
3. It will decode the JWT and you can validate the groups information as seen by ConsoleMe

