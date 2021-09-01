# Slack Notifications

ConsoleMe can be configured to send slack notifications when policy requests are created.

The following configuration should be added to your Configuration YAML to enable this feature:

```yaml
slack:
  notifications_enabled: true
  webhook_url: https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
```

Note that the webhook\_url should be replaced with the actual webhook URL, and treated as a secret.

`notifications_enabled` ConsoleMe will only send notifications if this is set to true.

`webhook_url` \(Required\) ConsoleMe needs the webhook URL in order to send messages to Slack. This can easily be created by following steps 1-3 [here](https://api.slack.com/messaging/webhooks). Note that depending on your workspace settings, you may need admin approval in order to create the app / generate the webhook URL. The app name that you use will be shown with all messages sent to slack, so choose the app name to be meaningful!

