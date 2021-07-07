# CLI Authentication

ConsoleMe's CLI \([Weep](https://github.com/Netflix/weep)\) authenticates to the ConsoleMe backend through one of two methods: Mutual TLS \(This is currently not supported in the open source code\), or standalone challenge authentication response.

The challenge authentication flow is as follows:

1. Client sends a GET request to ConsoleMe's unauthenticated challenge endpoint. The server generates and stores a temporary token for the authentication request. A token is scoped to the username sent in the request and expires after a couple of minutes. ConsoleMe tells the client where the user should authenticate it in their browser \(`challenge_url`\), and where to poll \(`polling_url`\).
2. Client starts polling the unauthenticated **polling\_url** every couple of seconds until the token expires after a couple of minutes.
3. The user is redirected to the **Challenge Validator** endpoint, which will authenticate them. After they've been successfully authenticated, the ConsoleMe backend will mark the user's request as successful in its cache.
4. After the user has authenticated, the client \(which is polling the `challenge_poller` endpoint every couple of seconds\) should receive a success status with the super secret encoded JWT that it can use to authenticate the user for credential requests to ConsoleMe.

{% api-method method="get" host="https://consoleme.example.com" path="/noauth/v1/challenge\_generator/:userName" %}
{% api-method-summary %}
Challenge Generator
{% endapi-method-summary %}

{% api-method-description %}
Client requests a challenge URL to authenticate a user.
{% endapi-method-description %}

{% api-method-spec %}
{% api-method-request %}
{% api-method-path-parameters %}
{% api-method-parameter name="" type="string" required=false %}

{% endapi-method-parameter %}
{% endapi-method-path-parameters %}
{% endapi-method-request %}

{% api-method-response %}
{% api-method-response-example httpCode=200 %}
{% api-method-response-example-description %}
Endpoint that returns an authentication challenge \(challenge\_url\), and a URL for the CLI to poll for credentials.
{% endapi-method-response-example-description %}

```text
{
  "challenge_url": "https://consoleme.example.com/challenge_validator/f82e6492-36a3-477d-9dab-98df1a0753a3",
  "polling_url": "https://consoleme.example.com/noauth/v1/challenge_poller/f82e6492-36a3-477d-9dab-98df1a0753a3"
}
```
{% endapi-method-response-example %}
{% endapi-method-response %}
{% endapi-method-spec %}
{% endapi-method %}

{% api-method method="get" host="https://consoleme.example.com" path="/noauth/v1/challenge\_poller/:challengeToken" %}
{% api-method-summary %}
Challenge Poller
{% endapi-method-summary %}

{% api-method-description %}
Endpoint that the CLI polls every few seconds to determine if the user has successfully authenticated. While the challenge is pending, `status` is the only attribute returned in the response. Once the user has successfully authenticated to the Challenge Validator endpoint, `status` will be updated, and the rest of the attributes will be returned in the next response.
{% endapi-method-description %}

{% api-method-spec %}
{% api-method-request %}
{% api-method-path-parameters %}
{% api-method-parameter name="" type="string" required=false %}

{% endapi-method-parameter %}
{% endapi-method-path-parameters %}
{% endapi-method-request %}

{% api-method-response %}
{% api-method-response-example httpCode=200 %}
{% api-method-response-example-description %}
Pending response
{% endapi-method-response-example-description %}

```text
{
    "status": "pending|success",
    "cookie_name": "consoleme_auth",
    "expiration": 1604524944,
    "encoded_jwt": "eyJ0eXAi....",
    "user": "user@example.com"
}
```
{% endapi-method-response-example %}
{% endapi-method-response %}
{% endapi-method-spec %}
{% endapi-method %}

{% api-method method="get" host="https://consoleme.example.com" path="/challenge\_validator/:challengeToken" %}
{% api-method-summary %}
Challenge Validator
{% endapi-method-summary %}

{% api-method-description %}
Endpoint that user visits in their browser to authenticate to ConsoleMe through SSO.
{% endapi-method-description %}

{% api-method-spec %}
{% api-method-request %}
{% api-method-path-parameters %}
{% api-method-parameter name="" type="string" required=false %}

{% endapi-method-parameter %}
{% endapi-method-path-parameters %}
{% endapi-method-request %}

{% api-method-response %}
{% api-method-response-example httpCode=200 %}
{% api-method-response-example-description %}

{% endapi-method-response-example-description %}

```text
You've successfully authenticated to ConsoleMe and may now close this page.
```
{% endapi-method-response-example %}
{% endapi-method-response %}
{% endapi-method-spec %}
{% endapi-method %}

