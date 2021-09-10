import qs from "qs";
import React, { Component } from "react";
import ReactDOM from "react-dom";
import { Icon, Message, Segment, Step } from "semantic-ui-react";
import ReactMarkdown from "react-markdown";
import SelfServiceStep1 from "./SelfServiceStep1";
import SelfServiceStep2 from "./SelfServiceStep2";
import SelfServiceStep3 from "./SelfServiceStep3";
import { SelfServiceStepEnum } from "./SelfServiceEnums";

import { DateTime } from "luxon";

import { arnRegex } from "../../helpers/utils";

class SelfService extends Component {
  constructor(props) {
    super(props);
    this.state = {
      config: null,
      currStep: SelfServiceStepEnum.STEP1,
      messages: null,
      permissions: [],
      role: null,
      services: [],
      admin_bypass_approval_enabled: false,
      export_to_terraform_enabled: false,
      extraActions: [],
      includeAccounts: [],
      excludeAccounts: [],
      updated_policy: "",
      expiration_date: null,
    };
  }

  async componentDidMount() {
    const config = await this.props.sendRequestCommon(
      null,
      "/api/v2/self_service_config",
      "get"
    );
    if (!config) {
      return;
    }
    const { services } = this.state;
    Object.keys(config.permissions_map || []).forEach((name) => {
      const service = config.permissions_map[name];
      services.push({
        actions: service.action_map,
        key: name,
        text: service.text,
        value: name,
      });
    });

    // If Self Service page is redirected with account and role information
    // TODO(heewonk), revisit following redirection once move to SPA
    const paramSearch = qs.parse(window.location.search, {
      ignoreQueryPrefix: true,
    });

    if (arnRegex.test(paramSearch.arn)) {
      // TODO(ccastrapel): Make backend request to get formal principal, since it may be a template
      const match = arnRegex.exec(paramSearch.arn);
      const { accountId, resourceType, resourceName } = match.groups;
      this.setState({
        admin_bypass_approval_enabled: config.admin_bypass_approval_enabled,
        export_to_terraform_enabled: config.export_to_terraform_enabled,
        config,
        currStep: SelfServiceStepEnum.STEP2,
        // TODO(heewonk), define the role type
        role: {
          account_id: accountId,
          account_name: "",
          apps: {
            app_details: [],
          },
          arn: `arn:aws:iam::${accountId}:${resourceType}/${resourceName}`,
          principal: {
            principal_type: "AwsResource",
            principal_arn: `arn:aws:iam::${accountId}:${resourceType}/${resourceName}`,
          },
          name: resourceName,
          owner: "",
          tags: [],
          templated: false,
          cloudtrail_details: {
            error_url: "",
            errors: {
              cloudtrail_errors: [],
            },
          },
          s3_details: {
            error_url: "",
            errors: {
              s3_errors: [],
            },
          },
        },
        services,
      });
    } else if (paramSearch?.encoded_request) {
      const { role, updated_policy } = JSON.parse(
        Buffer.from(paramSearch.encoded_request, "base64").toString()
      );
      this.setState({
        admin_bypass_approval_enabled: config.admin_bypass_approval_enabled,
        export_to_terraform_enabled: config.export_to_terraform_enabled,
        config,
        currStep: SelfServiceStepEnum.STEP3,
        role: role,
        updated_policy: updated_policy,
        services,
      });
    } else {
      this.setState({
        config,
        services,
        admin_bypass_approval_enabled: config.admin_bypass_approval_enabled,
        export_to_terraform_enabled: config.export_to_terraform_enabled,
      });
    }
  }

  handleSetPolicyExpiration(event, data) {
    // Convert epoch milliseconds to epoch seconds
    if (!data?.value) {
      return;
    }
    const dateObj = DateTime.fromJSDate(data.value);
    const dateString = dateObj.toFormat("yyyyMMdd");
    this.setState({
      expiration_date: parseInt(dateString),
    });
  }

  handleStepClick(dir) {
    const { currStep, updated_policy } = this.state;

    let nextStep = null;
    switch (currStep) {
      case SelfServiceStepEnum.STEP1:
        // TODO, change dir to ENUM
        if (dir === "next" && this.state.role != null) {
          nextStep = SelfServiceStepEnum.STEP2;
        } else {
          return this.setState({
            messages: "Please select a role from the list of applications.",
          });
        }
        break;
      case SelfServiceStepEnum.STEP2:
        if (
          (dir === "next" && this.state.permissions.length > 0) ||
          updated_policy !== ""
        ) {
          nextStep = SelfServiceStepEnum.STEP3;
        } else if (dir === "previous") {
          nextStep = SelfServiceStepEnum.STEP1;
        } else {
          return this.setState({
            messages: "Please add policy.",
          });
        }
        break;
      case SelfServiceStepEnum.STEP3:
        if (dir === "previous") {
          nextStep = SelfServiceStepEnum.STEP2;
        }
        break;
      default:
        return this.setState({
          messages: "Unknown Errors. Please reach out to #security-help",
        });
    }

    this.setState({
      currStep: nextStep,
      messages: null,
    });
  }

  updatePolicy(value) {
    this.setState({
      updated_policy: value,
    });
  }

  handleRoleUpdate(role) {
    this.setState({ role });
  }

  handleExtraActionsUpdate(extraActions) {
    this.setState({ extraActions });
  }

  handleIncludeAccountsUpdate(includeAccounts) {
    this.setState({ includeAccounts });
  }

  handleExcludeAccountsUpdate(excludeAccounts) {
    this.setState({ excludeAccounts });
  }

  handlePermissionsUpdate(permissions) {
    this.setState({ permissions });
  }

  handleResetUserChoices() {
    // This function is called after a user has added a permission set
    // to their "shopping cart". It will reset advanced settings so they
    // are not carried over to additional permission sets they add to their
    // "shopping cart".
    this.setState({
      extraActions: [],
      includeAccounts: [],
      excludeAccounts: [],
    });
  }

  getCurrentSelfServiceStep() {
    const {
      admin_bypass_approval_enabled,
      config,
      currStep,
      export_to_terraform_enabled,
      permissions,
      extraActions,
      includeAccounts,
      excludeAccounts,
      role,
      services,
      updated_policy,
      expiration_date,
    } = this.state;

    let SelfServiceStep = null;
    switch (currStep) {
      case SelfServiceStepEnum.STEP1:
        SelfServiceStep = (
          <SelfServiceStep1
            config={config}
            role={role}
            handleStepClick={this.handleStepClick.bind(this)}
            handleRoleUpdate={this.handleRoleUpdate.bind(this)}
            handleSetPolicyExpiration={this.handleSetPolicyExpiration.bind(
              this
            )}
            {...this.props}
          />
        );
        break;
      case SelfServiceStepEnum.STEP2:
        SelfServiceStep = (
          <SelfServiceStep2
            config={config}
            role={role}
            services={services}
            permissions={permissions}
            extraActions={extraActions}
            includeAccounts={includeAccounts}
            excludeAccounts={excludeAccounts}
            updated_policy={updated_policy}
            expiration_date={expiration_date}
            handleStepClick={this.handleStepClick.bind(this)}
            updatePolicy={this.updatePolicy.bind(this)}
            handlePermissionsUpdate={this.handlePermissionsUpdate.bind(this)}
            handleResetUserChoices={this.handleResetUserChoices.bind(this)}
            handleExtraActionsUpdate={this.handleExtraActionsUpdate.bind(this)}
            handleIncludeAccountsUpdate={this.handleIncludeAccountsUpdate.bind(
              this
            )}
            handleExcludeAccountsUpdate={this.handleExcludeAccountsUpdate.bind(
              this
            )}
            {...this.props}
          />
        );
        break;
      case SelfServiceStepEnum.STEP3:
        SelfServiceStep = (
          <SelfServiceStep3
            config={config}
            role={role}
            services={services}
            permissions={permissions}
            updated_policy={updated_policy}
            expiration_date={expiration_date}
            handleStepClick={this.handleStepClick.bind(this)}
            admin_bypass_approval_enabled={admin_bypass_approval_enabled}
            export_to_terraform_enabled={export_to_terraform_enabled}
            {...this.props}
          />
        );
        break;
      default:
        SelfServiceStep = <div />;
    }

    return SelfServiceStep;
  }

  render() {
    const { currStep, messages, updated_policy } = this.state;
    const SelfServiceStep = this.getCurrentSelfServiceStep();
    const messagesToShow =
      messages != null && updated_policy === "" ? (
        <Message negative>
          <Message.Header>There are some missing parameters</Message.Header>
          <p>{messages}</p>
        </Message>
      ) : null;

    const headerMessage =
      this.state.config != null &&
      this.state.config.custom_header_message != null ? (
        <Message success>
          <ReactMarkdown
            linkTarget="_blank"
            children={this.state.config.custom_header_message}
          />
        </Message>
      ) : null;

    return (
      <Segment basic>
        {headerMessage}
        <Step.Group fluid>
          <Step
            active={currStep === SelfServiceStepEnum.STEP1}
            onClick={() => {
              if (
                [SelfServiceStepEnum.STEP2, SelfServiceStepEnum.STEP3].includes(
                  currStep
                )
              ) {
                this.setState({ currStep: SelfServiceStepEnum.STEP1 });
              }
            }}
            className={`${
              currStep !== SelfServiceStepEnum.STEP1 ? "complete" : ""
            } step1`}
          >
            <Icon name="handshake" />
            <Step.Content>
              <Step.Title>Select Role</Step.Title>
              <Step.Description>Search and Select Role</Step.Description>
            </Step.Content>
          </Step>
          <Step
            active={currStep === SelfServiceStepEnum.STEP2}
            onClick={() => {
              if ([SelfServiceStepEnum.STEP3].includes(currStep)) {
                this.setState({ currStep: SelfServiceStepEnum.STEP2 });
              }
            }}
            className={`${
              currStep === SelfServiceStepEnum.STEP3 ? "complete" : ""
            } step2`}
          >
            <Icon name="search plus" />
            <Step.Content>
              <Step.Title>Modify Policy</Step.Title>
              <Step.Description>Provide Permission Details</Step.Description>
            </Step.Content>
          </Step>
          <Step
            active={currStep === SelfServiceStepEnum.STEP3}
            className={"step3"}
          >
            <Icon name="handshake" />
            <Step.Content>
              <Step.Title>Review and Submit</Step.Title>
              <Step.Description>Review and Submit Permissions</Step.Description>
            </Step.Content>
          </Step>
        </Step.Group>
        {messagesToShow}
        {SelfServiceStep}
      </Segment>
    );
  }
}

export function renderIAMSelfServiceWizard() {
  ReactDOM.render(
    <SelfService />,
    document.getElementById("new_policy_wizard")
  );
}

export default SelfService;
