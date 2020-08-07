import React, { Component } from "react";
import ReactDOM from "react-dom";
import { Button, Icon, Message, Segment, Step } from "semantic-ui-react";
import ReactMarkdown from "react-markdown";
import SelfServiceStep1 from "./SelfServiceStep1";
import SelfServiceStep2 from "./SelfServiceStep2";
import SelfServiceStep3 from "./SelfServiceStep3";
import { SelfServiceStepEnum } from "./SelfServiceEnums";

class SelfService extends Component {
  state = {
    config: null,
    currStep: SelfServiceStepEnum.STEP1,
    messages: null,
    permissions: [],
    role: null,
    services: [],
    admin_bypass_approval_enabled: false,
  };

  componentDidMount() {
    fetch("/api/v2/self_service_config").then((resp) => {
      resp.text().then((resp) => {
        const config = JSON.parse(resp);
        const { services } = this.state;
        Object.keys(config.permissions_map).forEach((name) => {
          const service = config.permissions_map[name];
          services.push({
            actions: service.action_map,
            key: name,
            text: service.text,
            value: name,
          });
        });
        this.setState({
          config,
          services,
          admin_bypass_approval_enabled: config.admin_bypass_approval_enabled,
        });
      });
    });
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

  handlePermissionsUpdate(permissions) {
    this.setState({ permissions });
  }

  getCurrentSelfServiceStep() {
    const { currStep } = this.state;

    let SelfServiceStep = null;
    switch (currStep) {
      case SelfServiceStepEnum.STEP1:
        SelfServiceStep = (
          <SelfServiceStep1
            config={this.state.config}
            role={this.state.role}
            handleRoleUpdate={this.handleRoleUpdate.bind(this)}
          />
        );
        break;
      case SelfServiceStepEnum.STEP2:
        SelfServiceStep = (
          <SelfServiceStep2
            config={this.state.config}
            role={this.state.role}
            services={this.state.services}
            permissions={this.state.permissions}
            handlePermissionsUpdate={this.handlePermissionsUpdate.bind(this)}
          />
        );
        break;
      case SelfServiceStepEnum.STEP3:
        SelfServiceStep = (
          <SelfServiceStep3
            config={this.state.config}
            role={this.state.role}
            services={this.state.services}
            permissions={this.state.permissions}
            admin_bypass_approval_enabled={
              this.state.admin_bypass_approval_enabled
            }
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
          <Step active={currStep === SelfServiceStepEnum.STEP1}>
            <Icon name="search" />
            <Step.Content>
              <Step.Title>Step 1.</Step.Title>
              <Step.Description>Search and Select Resource</Step.Description>
            </Step.Content>
          </Step>
          <Step active={currStep === SelfServiceStepEnum.STEP2}>
            <Icon name="search plus" />
            <Step.Content>
              <Step.Title>Step 2.</Step.Title>
              <Step.Description>Provide Permission Details</Step.Description>
            </Step.Content>
          </Step>
          <Step active={currStep === SelfServiceStepEnum.STEP3}>
            <Icon name="handshake" />
            <Step.Content>
              <Step.Title>Step 3.</Step.Title>
              <Step.Description>Review and Submit</Step.Description>
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
            primary
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
