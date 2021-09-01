# Cognito

Here are step-by-step directions for configuring Cognito as an identity provider in ConsoleMe:

1. Sign in to AWS, visit Cognito, and create a new User Pool

![](../../../.gitbook/assets/image%20%2817%29%20%281%29%20%281%29%20%281%29%20%281%29.png)

2. Under App Clients, click "Add an app client"

3. We've selected `ALLOW_USER_PASSWORD_AUTH`, and left the other settings as defaults

![](../../../.gitbook/assets/image%20%2815%29.png)

4. Click "Review", give your pool a name if you haven't already, and click "Create Pool". 

5. Go back to "App Integration" -&gt; "App Client Settings", enable "Cognito Identity Pool" as a valid Identity Provider, and configure the following urls under callback urls:

http://localhost:8081/auth, http://localhost:8081/oauth2/idpresponse,http://localhost:3000/auth, http://localhost:3000/oauth2/idpresponse

6. Under `Allowed OAuth flows`, select `Authorization code grant`

7. Under `Allowed OAuth Scopes` , select `email`, `openid`, and `profile`.

8. Create a test user and test group under `Users and Groups`.

9. Change other settings as needed to satisfy your security and authorization needs.

10. Make a ConsoleMe configuration. You can do this by copying [example\_config/example\_config\_oidc\_cognito\_all\_in\_one.yaml](https://github.com/Netflix/consoleme/blob/master/example_config/example_config_oidc_cognito_all_in_one.yaml) to a directory of your choice and changing the various values in that file to suit your needs. The key values to change are:

* oidc\_secrets.client\_id = Client ID in Cognito \(App Clients -&gt; App Client ID\)
* oidc\_secrets.secret = Client Secret in Cognito \(App Clients -&gt; App Client Secret\)
* oidc\_secrets.client\_scope = List of Scopes granted to the App integration in Cognito. Usually email and openid,
* get\_user\_by\_oidc\_settings.jwt\_groups\_key = 'cognito:groups\`
* get\_user\_by\_oidc\_settings.metadata\_url = The metadata URL of your Cognito Pool. Usually this is the following \(Replace `{user_pool_id}` with your own pool ID\):
  * [https://cognito-idp.us-east-1.amazonaws.com/{user\_pool\_id}/.well-known/openid-configuration](https://cognito-idp.us-east-1.amazonaws.com/{user_pool_id}/.well-known/openid-configuration)
* get\_user\_by\_oidc\_settings.access\_token\_audience = This must be set to `null`, because the access token provided by Cognito does not include an audience.

11. Start yarn or build the Frontend files for Tornado to serve

* In the `consoleme/ui` directory, run `yarn`
* Run `yarn start` to have the frontend served by Yarn on `http://localhost:3000`. The backend API endpoints will be served by Python \(Tornado\) on `http://localhost:8081`. 
* Run `yarn build:prod` to build the frontend files and put them in a location for the backend to serve. ConsoleMe will be accessible on `http://localhost:8081`.

12. Start ConsoleMe by setting the CONFIG\_LOCATION environment variable and running `consoleme/__main__.py` with Python in your virtualenv \(This was created in the [Local Quick Start guide](../../../quick-start/local-development.md)\)

```text
export CONFIG_LOCATION=/location/to/your/config.yaml
python /location/to/consoleme/__main__.py
```

6. Visit http://localhost:3000 \(if serving via Yarn\), or http://localhost:8081 \(If you built the frontend files to serve via Tornado\) to test.

