/* eslint-disable */
export const questions_json = {
  calculatedValues: [],
  clearInvisibleValues: "onHidden",
  questions: [
    {
      isRequired: true,
      name: "application_admin",
      title:
        "What should the value be for Adminstrator of ConsoleMe (Enter your team's (or just your) username/email here. This user (or members of the group) will have full admin capabilities in ConsoleMe,\nand be used as the default approvers of IAM policy requests.)?",
      type: "text",
    },
    {
      defaultValue: false,
      name: "tornado.debug",
      title:
        "Do you want to enable Tornado Debug mode (Warning: if running in production, don't set debug on!)?",
      type: "boolean",
    },
    {
      choices: [
        "Single account mode (ConsoleMe only gathers information an permits changes to the account it has credentials for. No further configuration needed)",
        "Configuration File",
        "AWS Organizations",
        "Swag (https://github.com/Netflix-Skunkworks/swag-api)",
      ],
      colCount: 1,
      isRequired: true,
      name: "__accounts_choice",
      title:
        "Which of the following should be used for retrieving AWS accounts (knowledge about your AWS accounts is needed)?",
      type: "radiogroup",
    },
    {
      __extra_details: "list_dict",
      isRequired: true,
      name: "account_ids_to_name",
      title:
        "Please provide a comma-seperated list of accounts IDs to name mapping (this will be accounts that ConsoleMe should cache information for, for example: 1234: prod, 5678: test)",
      type: "text",
      visibleIf: "{__accounts_choice} = 'Configuration File'",
    },
    {
      isRequired: true,
      name:
        "cache_accounts_from_aws_organizations.organizations_master_account_id",
      title:
        "What should the value be for account ID for the organization (account ID of your AWS organizations master)?",
      type: "text",
      visibleIf: "{__accounts_choice} = 'AWS Organizations'",
    },
    {
      isRequired: true,
      name:
        "cache_accounts_from_aws_organizations.organizations_master_role_to_assume",
      title:
        "What should the value be for role for the organization master account (name of the role that consoleme will attempt to assume on your Organizations master account to retrieve account information)?",
      type: "text",
      visibleIf: "{__accounts_choice} = 'AWS Organizations'",
    },
    {
      isRequired: true,
      name: "retrieve_accounts_from_swag.base_url",
      title:
        "What should the value be for swag URL (Base URL for swag from where to retrieve account information)?",
      type: "text",
      visibleIf:
        "{__accounts_choice} = 'Swag (https://github.com/Netflix-Skunkworks/swag-api)'",
    },
    {
      defaultValue: "ConsoleMe",
      isRequired: true,
      name: "policies.role_name",
      title:
        "What should the value be for multi-account support (ConsoleMe's multi-account support works with a hub and spoke design. Your central (hub) AWS account will need an\nIAM role on all of your (spoke) accounts that it can assume to gather resource information and make changes on the\naccount. (Yes, this role will be needed on the central account as well. If configured, ConsoleMe will always\nattempt to assume a role when attempting operations on a different account).)?",
      type: "text",
      visibleIf:
        "{__accounts_choice} = 'Configuration File' or {__accounts_choice} = 'AWS Organizations' or {__accounts_choice} = 'Swag (https://github.com/Netflix-Skunkworks/swag-api)'",
    },
    {
      choices: [
        "ALB Auth - Cognito",
        "ALB Auth - Google",
        "ALB Auth - Okta",
        "ALB Auth - Generic",
        "OIDC/OAuth2 - Other",
        "Header Authentication (I have trusted headers that identify the authenticated user and their groups)",
      ],
      colCount: 1,
      isRequired: true,
      name: "__auth_choice",
      title:
        "Which of the following should be used for auth mechanism (method of Web App Authentication and Authorization)?",
      type: "radiogroup",
    },
    {
      isRequired: true,
      name: "auth.user_header_name",
      title:
        "What should the value be for Name of header specifying username (Name of trusted header specifying username)?",
      type: "text",
      visibleIf:
        "{__auth_choice} = 'Header Authentication (I have trusted headers that identify the authenticated user and their groups)'",
    },
    {
      isRequired: true,
      name: "auth.groups_header_name",
      title:
        "What should the value be for Name of header specifying comma-separated list of user's groups (Name of trusted header specifying comma-separated list of user's groups)?",
      type: "text",
      visibleIf:
        "{__auth_choice} = 'Header Authentication (I have trusted headers that identify the authenticated user and their groups)'",
    },
    {
      isRequired: true,
      name:
        "get_user_by_aws_alb_auth_settings.access_token_validation.metadata_url",
      title:
        "What should the value be for cognito pool ID (Amazon Cognito user pool ID)?",
      type: "text",
      visibleIf: "{__auth_choice} = 'ALB Auth - Cognito'",
    },
    {
      __extra_details: "list",
      name:
        "get_user_by_aws_alb_auth_settings.access_token_validation.jwks_uri",
      title:
        "Please provide a comma-seperated list of jwks_uri (Only required if your metadata URL doesn't return jwks_uri within the JSON)",
      type: "text",
      visibleIf: "{__auth_choice} = 'ALB Auth - Cognito'",
    },
    {
      defaultValue: "cognito:groups",
      isRequired: true,
      name: "get_user_by_aws_alb_auth_settings.jwt_groups_key",
      title: "What should the value be for jwt_groups_key (jwt_groups_key)?",
      type: "text",
      visibleIf: "{__auth_choice} = 'ALB Auth - Cognito'",
    },
    {
      defaultValue:
        "https://accounts.google.com/.well-known/openid-configuration",
      isRequired: true,
      name:
        "get_user_by_aws_alb_auth_settings.access_token_validation.metadata_url",
      title: "What should the value be for metadata URL (Google metadata URL)?",
      type: "text",
      visibleIf: "{__auth_choice} = 'ALB Auth - Google'",
    },
    {
      name:
        "get_user_by_aws_alb_auth_settings.access_token_validation.jwks_uri",
      title:
        "What should the value be for jwks_uri (Only required if your metadata URL doesn't return jwks_uri within the JSON)?",
      type: "text",
      visibleIf: "{__auth_choice} = 'ALB Auth - Google'",
    },
    {
      isRequired: true,
      name:
        "get_user_by_aws_alb_auth_settings.access_token_validation.metadata_url",
      title:
        "What should the value be for Okta Domain (the domain for your Okta, https://<DOMAIN>.okta.com)?",
      type: "text",
      visibleIf: "{__auth_choice} = 'ALB Auth - Okta'",
    },
    {
      name:
        "get_user_by_aws_alb_auth_settings.access_token_validation.jwks_uri",
      title:
        "What should the value be for jwks_uri (Only required if your metadata URL doesn't return jwks_uri within the JSON)?",
      type: "text",
      visibleIf: "{__auth_choice} = 'ALB Auth - Okta'",
    },
    {
      isRequired: true,
      name:
        "get_user_by_aws_alb_auth_settings.access_token_validation.client_id",
      title: "What should the value be for client ID (Okta Client ID)?",
      type: "text",
      visibleIf: "{__auth_choice} = 'ALB Auth - Okta'",
    },
    {
      isRequired: true,
      name:
        "get_user_by_aws_alb_auth_settings.access_token_validation.metadata_url",
      title:
        "What should the value be for Metadata URL (The URL to your IDP's .well-known/oauth-authorization-server or .well-known/openid-configuration file)?",
      type: "text",
      visibleIf: "{__auth_choice} = 'ALB Auth - Generic'",
    },
    {
      defaultValue: "email",
      isRequired: true,
      name: "get_user_by_aws_alb_auth_settings.jwt_email_key",
      title: "What should the value be for jwt_email_key (jwt_email_key)?",
      type: "text",
      visibleIf:
        "{__auth_choice} = 'ALB Auth - Cognito' or {__auth_choice} = 'ALB Auth - Google' or {__auth_choice} = 'ALB Auth - Okta' or {__auth_choice} = 'ALB Auth - Generic'",
    },
    {
      defaultValue: "groups",
      isRequired: true,
      name: "get_user_by_aws_alb_auth_settings.jwt_groups_key",
      title: "What should the value be for jwt_groups_key (jwt_groups_key)?",
      type: "text",
      visibleIf:
        "{__auth_choice} = 'ALB Auth - Google' or {__auth_choice} = 'ALB Auth - Okta' or {__auth_choice} = 'ALB Auth - Generic'",
    },
    {
      isRequired: true,
      name: "get_user_by_oidc_settings.metadata_url",
      title:
        "What should the value be for IDP metadata URL (Your (not so) well-known IDP metadata URL. This can be tricky to find. Here are a few common ones we've seen:\nActive Directory Azure - https://login.microsoftonline.com/<APP_OBJECT_ID>/v2.0/.well-known/openid-configuration\nGoogle (User only) - https://accounts.google.com/.well-known/openid-configuration\nCognito - https://cognito-idp.us-east-1.amazonaws.com/{COGNITO_POOL_ID}/.well-known/openid-configuration\nOkta - https://{YOURSERVER}.okta.com/oauth2/default/.well-known/oauth-authorization-server\nOkta alternative: https://{YOURSERVER}.okta.com/oauth2/default/.well-known/openid-configuration)?",
      type: "text",
      visibleIf: "{__auth_choice} = 'OIDC/OAuth2 - Other'",
    },
    {
      defaultValue: "email",
      isRequired: true,
      name: "get_user_by_oidc_settings.jwt_email_key",
      title:
        "What should the value be for Email key in the ID token (The key of the user's identity/email in the ID token JWT\nActive Directory Azure - upn\nGoogle (User only) - email\nCognito - email\nOkta - email)?",
      type: "text",
      visibleIf: "{__auth_choice} = 'OIDC/OAuth2 - Other'",
    },
    {
      defaultValue: "groups",
      isRequired: true,
      name: "get_user_by_oidc_settings.jwt_groups_key",
      title:
        "What should the value be for Groups key in either the ID or Access token (The key of the user's groups in the ID or Access token JWT)?",
      type: "text",
      visibleIf: "{__auth_choice} = 'OIDC/OAuth2 - Other'",
    },
    {
      defaultValue: true,
      name: "get_user_by_oidc_settings.get_groups_from_userinfo_endpoint",
      title:
        "Do you want to enable getting groups from OIDC userinfo endpoint? (If we can't find the user's groups in their ID or Access tokens, we can try to get groups from the OIDC userinfo\nendpoint. Should we? (We're desperate at this point!))?",
      type: "boolean",
      visibleIf: "{__auth_choice} = 'OIDC/OAuth2 - Other'",
    },
    {
      isRequired: true,
      name: "get_user_by_oidc_settings.user_info_groups_key",
      title:
        "What should the value be for What is the group key in the userinfo response? (We got a lovely JSON response from the OIDC userinfo endpoint. What key, oh master, should I expect to find the\ngroups in?)?",
      type: "text",
      visibleIf:
        "{get_user_by_oidc_settings.get_groups_from_userinfo_endpoint} = 'True'",
    },
    {
      isRequired: true,
      name: "consoleme_s3_bucket",
      title:
        "What should the value be for ConsoleMe's S3 bucket (a (preferably versioned) S3 bucket that I can cache and retrieve data from? The role that ConsoleMe runs\nas must have access to this bucket)?",
      type: "text",
    },
    {
      defaultValue: "localhost",
      name: "redis.host.global",
      title:
        "What should the value be for the redis host I can use? Elasticache Redis is preferred in production (Don't use localhost in production, you monster!)?",
      type: "text",
    },
    {
      defaultValue: "redis://{redis-host-global}:6379/1",
      name: "celery.broker.global",
      title:
        "What should the value be for the redis host and database that ConsoleMe can use as the Celery broker? Elasticache Redis is preferred. This time, please enter a\nfully qualified redis URL because Celery expects it. (Is there a redis host ConsoleMe can use as the Celery backend? Fully qualified URL required this time. If you want to\nreuse an existing endpoint, please select a different database than the one you used before (The default is /0,\nso just add /1 to the end of your url))?",
      type: "text",
    },
    {
      defaultValue: "redis://{redis-host-global}:6379/2",
      name: "celery.broker.global",
      title:
        "What should the value be for Is there a redis host ConsoleMe can use as the Celery backend? Fully qualified URL required this time. If you want to\nreuse an existing endpoint, please select a different database than the one you used before (change /1 to /2) (Is there a redis host ConsoleMe can use as the Celery broker? Elasticache cluster preferred.)?",
      type: "text",
    },
    {
      defaultValue: "us-west-2",
      name: "celery.active_region",
      title:
        "What should the value be for Celery active region (Some celery jobs should only run in one region. You should define your primary region here.)?",
      type: "text",
    },
    {
      defaultValue: true,
      name: "challenge_url.enabled",
      title:
        "Do you want to enable Challenge URL authentication (Challenge URL authentication is used to authenticate users from CLI clients (like Weep).)?",
      type: "boolean",
    },
    {
      isRequired: true,
      name: "ses.arn",
      title:
        "What should the value be for SES ARN (SES configuration is necessary for ConsoleMe to send e-mails to your users. ConsoleMe sends e-mails to notify\nadministrators and requesters about policy requests applicable to them.)?",
      type: "text",
    },
    {
      defaultValue: "us-west-2",
      isRequired: true,
      name: "ses.region",
      title:
        "What should the value be for SES region (SES configuration is necessary for ConsoleMe to send e-mails to your users. ConsoleMe sends e-mails to notify\nadministrators and requesters about policy requests applicable to them.)?",
      type: "text",
    },
    {
      autoComplete: "email",
      inputType: "email",
      isRequired: true,
      name: "ses.consoleme.sender",
      title:
        "Which email should be used for the SES email address ConsoleMe sends mail from (SES configuration is necessary for ConsoleMe to send e-mails to your users. ConsoleMe sends e-mails to notify\nadministrators and requesters about policy requests applicable to them.)?",
      type: "text",
      validators: [
        {
          type: "email",
        },
      ],
    },
    {
      autoComplete: "email",
      inputType: "email",
      name: "support_contact",
      title:
        "Which email should be used for the support contact (This information is displayed in ConsoleMe's sidebar)?",
      type: "text",
      validators: [
        {
          type: "email",
        },
      ],
    },
    {
      defaultValue: "https://www.example.com/slack/channel",
      name: "support_chat_url",
      title:
        "What should the value be for support chat URL (This information is displayed in ConsoleMe's sidebar)?",
      type: "text",
    },
    {
      defaultValue:
        "Please contact us at {support_contact} if you have any questions or concerns.",
      name: "ses.support_reference",
      title:
        "What should the value be for support reference added to the bottom of ConsoleMe emails that are sent to end-users (When ConsoleMe sends e-mail, the end of the message will contain this string.)?",
      type: "text",
    },
    {
      defaultValue: "https://hawkins.gitbook.io/consoleme/",
      name: "documentation_page",
      title:
        "What should the value be for documentation page for more information (This information is displayed in ConsoleMe's sidebar)?",
      type: "text",
    },
    {
      choices: ["No Metrics", "CloudWatch Metrics"],
      colCount: 1,
      isRequired: true,
      name: "__metrics_choice",
      title:
        "Which of the following should be used for Your Metrics Provider (Should we enable metrics)?",
      type: "radiogroup",
    },
    {
      __extra_details: "list",
      defaultValue: "consoleme-authorized",
      name:
        "cloud_credential_authorization_mapping.role_tags.authorized_groups_tags",
      title:
        "Please provide a comma-seperated list of the tags on an IAM role that indicate the users/groups authorized to get credentials for a role\nin both the ConsoleMe UI and via CLI. You must prevent non-administrative users from modifying\nthese tags via an AWS Service Control Policy on your Organizations Master account. (ConsoleMe uses IAM role tags to determine who gets access to a role. Read more about this feature\nhere: https://hawkins.gitbook.io/consoleme/configuration/role-credential-authorization/role-tagging-recommended)",
      type: "text",
    },
    {
      __extra_details: "list",
      defaultValue: "consoleme-owner-dl,consoleme-authorized-cli-only",
      name:
        "cloud_credential_authorization_mapping.role_tags.authorized_groups_cli_only_tags",
      title:
        "Please provide a comma-seperated list of the tags on an IAM role that indicate the users/groups authorized to get credentials for a role\nvia the CLI only. You must prevent non-administrative users from modifying\nthese tags via an AWS Service Control Policy on your Organizations Master account. (ConsoleMe uses IAM role tags to determine who gets access to a role. Read more about this feature\nhere: https://hawkins.gitbook.io/consoleme/configuration/role-credential-authorization/role-tagging-recommended)",
      type: "text",
    },
  ],
};
