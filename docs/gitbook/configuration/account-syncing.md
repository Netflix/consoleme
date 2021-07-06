# Account Syncing

ConsoleMe will use the AWS credentials you provide to sync your accounts. We currently support syncing accounts from **AWS Organizations,** [**SWAG**](https://github.com/Netflix-Skunkworks/swag-api)**, local Configuration,** and if none of these is configured, ConsoleMe will attempt to **Sync the current account.**

## **Sync Accounts from AWS Organizations**

ConsoleMe can sync accounts from your AWS Organizations master account. To configure this option, you must have a role on your AWS Organization master account that ConsoleMe can assume with **sts:AssumeRole**.

To configure this option, the following configuration values should be set in your ConsoleMe yaml configuration file:

```text
cache_accounts_from_aws_organizations:
  # This is a list of the account IDs of your AWS organizations master(s)
  - organizations_master_account_id: "123456789012"
    # This is the name of the role that consoleme will attempt to assume on
    # your Organizations master account to call organizations:listaccounts.
    organizations_master_role_to_assume: "ConsoleMe"
```

## **Sync Accounts from** SWAG

ConsoleMe can sync your organization's accounts from [SWAG](https://github.com/Netflix-Skunkworks/swag-api)'s API url. If you're storing 3rd party accounts in SWAG that you do not wish for ConsoleMe to sync, you can use the **expected\_owners** configuration to sync only the desired accounts.

ConsoleMe needs the following configuration values to sync accounts from SWAG:

```text
retrieve_accounts_from_swag:
  base_url: 'https://swag.example.com/'
  # Optional
  expected_owners:
    - exampleOrg
```

## **Sync Accounts from** Configuration

You can also optionally provide configuration that explicitly provides ConsoleMe with a mapping of your account IDs to account names. You can provide this list either in your local configuration, or \(as an administrator\) your dynamic configuration at [https://your\_consoleme\_url/config](https://your_consoleme_url/config).

> Account IDs should be quoted in YAML so that they are interpreted as strings. Account IDs can start with the number 0, and the first number would be dropped if interpreted as an integer.

Here is the required configuration:

```text
account_ids_to_name:
  "123456789012":
    - default_account
  "123456789013":
    - prod
  "123456789014":
    - test
```

## **Fallback: Sync the** Current Account

As a fallback mechanism, ConsoleMe will attempt to sync the current account using **sts:getCallerIdentity** and **iam:listAccountAliases**. ConsoleMe attempts to do this during initial installation if no other configuration has been provided.

