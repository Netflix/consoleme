import qs from "qs";
import React, { useState, useEffect } from "react";
import ReactDOM from "react-dom";
import { Button, Icon, Message, Segment, Step } from "semantic-ui-react";
import ReactMarkdown from "react-markdown";
import SelfServiceStep1 from "./SelfServiceStep1";
import SelfServiceStep2 from "./SelfServiceStep2";
import SelfServiceStep3 from "./SelfServiceStep3";
import { SelfServiceStepEnum } from "./SelfServiceEnums";
import { sendRequestCommon } from "../../helpers/utils";

const arnRegex = /^arn:aws:iam::(?<accountId>\d{12}):role\/(.+\/)?(?<roleName>(.+))/;

const SelfService = () => {
  const initialState = {
    config: null,
    currStep: SelfServiceStepEnum.STEP1,
    messages: null,
    permissions: [],
    role: null,
    services: [],
    admin_bypass_approval_enabled: false,
  };

  const [state, setState] = useState(initialState);

  useEffect(async () => {
    const config = await sendRequestCommon(
      null,
      "/api/v2/self_service_config",
      "get"
    );
    const { services } = state;
    Object.keys(config.permissions_map).forEach((name) => {
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

      setState({
        ...state,
        admin_bypass_approval_enabled: config.admin_bypass_approval_enabled,
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
    } else {
      setState({
        ...state,
        config,
        services,
        admin_bypass_approval_enabled: config.admin_bypass_approval_enabled,
      });
    }
  }, []);

  const handleStepClick = (dir) => {
    const { currStep } = state;

    let nextStep = null;
    switch (currStep) {
      case SelfServiceStepEnum.STEP1:
        // TODO, change dir to ENUM
        if (dir === "next" && state.role != null) {
          nextStep = SelfServiceStepEnum.STEP2;
        } else {
          return setState({
            ...state,
            messages: "Please select a role from the list of applications.",
          });
        }
        break;
      case SelfServiceStepEnum.STEP2:
        if (dir === "next" && state.permissions.length > 0) {
          nextStep = SelfServiceStepEnum.STEP3;
        } else if (dir === "previous") {
          nextStep = SelfServiceStepEnum.STEP1;
        } else {
          return setState({
            ...state,
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
        return setState({
          ...state,
          messages: "Unknown Errors. Please reach out to #security-help",
        });
    }

    setState({
      ...state,
      currStep: nextStep,
      messages: null,
    });
  };

  const handleRoleUpdate = (role) => {
    setState({ ...state, role });
  };

  const handlePermissionsUpdate = (permissions) => {
    setState({ ...state, permissions });
  };

  const getCurrentSelfServiceStep = () => {
    const {
      admin_bypass_approval_enabled,
      config,
      currStep,
      permissions,
      role,
      services,
    } = state;

    let SelfServiceStep = null;
    switch (currStep) {
      case SelfServiceStepEnum.STEP1:
        SelfServiceStep = (
          <SelfServiceStep1
            config={config}
            role={role}
            handleRoleUpdate={() => handleRoleUpdate()}
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
            handlePermissionsUpdate={() => handlePermissionsUpdate()}
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
          />
        );
        break;
      default:
        SelfServiceStep = <div />;
    }

    return SelfServiceStep;
  };

  const { currStep, messages } = state;
  const SelfServiceStep = getCurrentSelfServiceStep();
  const messagesToShow =
    messages != null ? (
      <Message negative>
        <Message.Header>There are some missing parameters</Message.Header>
        <p>{messages}</p>
      </Message>
    ) : null;

  const headerMessage =
    state.config != null && state.config.custom_header_message != null ? (
      <Message success>
        <ReactMarkdown
          linkTarget="_blank"
          source={state.config.custom_header_message}
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
          onClick={() => handleStepClick("previous")}
        >
          Previous
        </Button>
      ) : null}
      {currStep !== SelfServiceStepEnum.STEP3 ? (
        <Button
          disabled={currStep === SelfServiceStepEnum.STEP3}
          floated="right"
          primary
          onClick={() => handleStepClick("next")}
        >
          Next
        </Button>
      ) : null}
    </Segment>
  );
};

export function renderIAMSelfServiceWizard() {
  ReactDOM.render(
    <SelfService />,
    document.getElementById("new_policy_wizard")
  );
}

export default SelfService;
