# Sending email through SES

ConsoleMe can be configured to send e-mails when policy requests are created, or their status is updated.

The following configuration should be added to your Configuration YAML to enable this feature:

```yaml
ses:
  support_reference: "Please contact us at consoleme@example.com if you have any questions or concerns."
  arn: "arn:aws:ses:us-east-1:123456789012:identity/example.com"
  consoleme:
    name: ConsoleMe
    sender: consoleme_test@example.com
```

`support_reference` \(Optional\) A string that is appended to the bottom of the e-mail ConsoleMe sends to users. This is where you'd give the user a call-to-action for further follow-up, such as chatting or sending an e-mail to your team.

`arn` \(Optional\) Optional Source ARN field. This is used only for sending authorization. It is the ARN of the identity that is associated with the sending authorization policy that permits you to send email through the desired e-mail address. You can read more about SourceArn [here](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ses.html#SES.Client.send_email).

`consoleme.name` \(Optional\) Specifies the name of the sender, and is used in the subject of the e-mail.

`consoleme.sender` The email address that is sending the email from ConsoleMe. This email address must be either individually verified with Amazon SES, or from a domain that has been verified with Amazon SES.

