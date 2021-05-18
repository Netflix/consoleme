# Okta

Here are step-by-step directions for configuring Okta as an identity provider in ConsoleMe:

1. Sign up for an Okta account, or sign in to your existing account
2. Visit Applications -&gt; "Create App Integration"

![](../../../.gitbook/assets/image%20%2818%29.png)

3. Create the integration with redirect URIs \(for local testing\) of http://localhost:3000/auth and http://localhost:8081/auth and save. 

![](../../../.gitbook/assets/image%20%2814%29.png)

4. Click **Okta API Scopes** and add **okta.groups.read** and **okta.users.read.self**

![](../../../.gitbook/assets/image%20%2816%29.png)

5. Make a ConsoleMe configuration. You can do this by copying [example\_config/example\_config\_oidc\_all\_in\_one.yaml](https://github.com/Netflix/consoleme/blob/master/example_config/example_config_oidc_all_in_one.yaml) to a directory of your choice and changing the various values in that file to suit your needs. The key values to change are:

* oidc\_secrets.client\_id = Client ID in Okta
* oidc\_secrets.secret = Client Secret in Okta
* oidc\_secrets.client\_scope = List of Scopes granted to the App integration in Okta
* get\_user\_by\_oidc\_settings.resource = Name of the App Resource in Okta
* get\_user\_by\_oidc\_settings.metadata\_url = The metadata URL of your Okta App Integration. Usually this is one of the following:
  * https://YOURDOMAIN.okta.com/oauth2/default/.well-known/oauth-authorization-server
  * https://YOURDOMAIN.okta.com/oauth2/default/.well-known/openid-configuration

6. Start yarn or build the Frontend files for Tornado to serve

* In the `consoleme/ui` directory, run `yarn`
* Run `yarn start` to have the frontend served by Yarn on `http://localhost:3000`. The backend API endpoints will be served by Python \(Tornado\) on `http://localhost:8081`. 
* Run `yarn build:prod` to build the frontend files and put them in a location for the backend to serve. ConsoleMe will be accessible on `http://localhost:8081`.

7. Start ConsoleMe by setting the CONFIG\_LOCATION environment variable and running `consoleme/__main__.py` with Python in your virtualenv \(This was created in the [Local Quick Start guide](../../../quick-start/local-development.md)\)

```text
export CONFIG_LOCATION=/location/to/your/config.yaml
python /location/to/consoleme/__main__.py
```

8. Visit http://localhost:3000 \(if serving via Yarn\), or http://localhost:8081 \(If you built the frontend files to serve via Tornado\) to test.

