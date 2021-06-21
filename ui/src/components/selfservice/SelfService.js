import qs from "qs";
import React, { Component } from "react";
import ReactDOM from "react-dom";
import { Button, Icon, Message, Segment, Step } from "semantic-ui-react";
import ReactMarkdown from "react-markdown";
import SelfServiceStep1 from "./SelfServiceStep1";
import SelfServiceStep2 from "./SelfServiceStep2";
import SelfServiceStep3 from "./SelfServiceStep3";
import { SelfServiceStepEnum } from "./SelfServiceEnums";

const arnRegex = /^arn:aws:iam::(?<accountId>\d{12}):role\/(.+\/)?(?<roleName>(.+))/;
const honeyBee = "honeybee";

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
      const match = arnRegex.exec(paramSearch.arn);
      const { accountId, roleName } = match.groups;

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
          arn: `arn:aws:iam::${accountId}:role/${roleName}`,
          name: roleName,
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
    } else if (paramSearch.template_language === "honeybee") {
      const match = honeyBee.exec(paramSearch.template_language);
      const { accountId, roleName } = match.groups;
      this.setState({
        admin_bypass_approval_enabled: config.admin_bypass_approval_enabled,
        export_to_terraform_enabled: config.export_to_terraform_enabled,
        config,
        currStep: SelfServiceStepEnum.STEP2,
        // TODO(heewonk), define the role type
        role: {
          name: "ConsoleMe",
          owner: "infrasec@netflix.com",
          include_accounts: ["*"],
          exclude_accounts: [],
          number_of_accounts: 2,
          resource: "iamrole/consoleme.yaml",
          resource_type: "iam_role",
          repository_name: "honeybee-templates",
          template_language: "honeybee",
          web_path:
            "https://stash.corp.netflix.com/projects/CLDSEC/repos/honeybee-templates/browse/iamrole/consoleme.yaml",
          file_path: "honeybee-templates/iamrole/consoleme.yaml",
          content: null,
        },
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

  handleStepClick(dir) {
    const { currStep } = this.state;

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
        if (dir === "next" && this.state.permissions.length > 0) {
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

  getCurrentSelfServiceStep() {
    const {
      admin_bypass_approval_enabled,
      config,
      currStep,
      export_to_terraform_enabled,
      permissions,
      role,
      services,
    } = this.state;

    let SelfServiceStep = null;
    switch (currStep) {
      case SelfServiceStepEnum.STEP1:
        SelfServiceStep = (
          <SelfServiceStep1
            config={config}
            role={role}
            handleRoleUpdate={this.handleRoleUpdate.bind(this)}
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
            handlePermissionsUpdate={this.handlePermissionsUpdate.bind(this)}
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
    const { currStep, messages } = this.state;
    const SelfServiceStep = this.getCurrentSelfServiceStep();
    const messagesToShow =
      messages != null ? (
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
            source={this.state.config.custom_header_message}
          />
        </Message>
      ) : null;

    return (
      <Segment basic>
        {headerMessage}
        <Step.Group fluid>
          <Step
            active={currStep === SelfServiceStepEnum.STEP1}
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
            className={`${
              currStep === SelfServiceStepEnum.STEP3 ? "complete" : ""
            } step2`}
          >
            <Icon
              name="search plus"
              disabled={currStep === SelfServiceStepEnum.STEP1}
            />
            <Step.Content>
              <Step.Title>Modify Policy</Step.Title>
              <Step.Description>Provide Permission Details</Step.Description>
            </Step.Content>
          </Step>
          <Step
            active={currStep === SelfServiceStepEnum.STEP3}
            className={"step3"}
          >
            <Icon
              name="handshake"
              disabled={currStep !== SelfServiceStepEnum.STEP3}
            />
            <Step.Content>
              <Step.Title>Review and Submit</Step.Title>
              <Step.Description>Review and Submit Permissions</Step.Description>
            </Step.Content>
          </Step>
        </Step.Group>
        {messagesToShow}
        {SelfServiceStep}
        {currStep !== SelfServiceStepEnum.STEP1 ? (
          <Button
            disabled={currStep === SelfServiceStepEnum.STEP1}
            floated="left"
            primary
            onClick={this.handleStepClick.bind(this, "previous")}
          >
            Previous
          </Button>
        ) : null}
        {currStep !== SelfServiceStepEnum.STEP3 ? (
          <Button
            disabled={currStep === SelfServiceStepEnum.STEP3}
            floated="right"
            positive
            onClick={this.handleStepClick.bind(this, "next")}
          >
            Next
          </Button>
        ) : null}
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
