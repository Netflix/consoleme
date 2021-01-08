import _ from "lodash";
import React, { useState, useEffect } from "react";
import {
  Button,
  Dimmer,
  Divider,
  Form,
  Grid,
  Header,
  Label,
  Message,
  Tab,
  Table,
  TextArea,
} from "semantic-ui-react";
import AceEditor from "react-ace";
import "brace";
import ace from "brace";
import { getCompletions, sendRequestCommon } from "../../helpers/utils";
import "brace/ext/language_tools";
import "brace/theme/monokai";
import "brace/mode/json";

const SelfServiceStep3 = (props) => {
  const initialState = {
    activeIndex: 0,
    custom_statement: "",
    isError: false,
    isLoading: false,
    isSuccess: false,
    justification: "",
    messages: [],
    requestId: null,
    statement: "",
    admin_bypass_approval_enabled: props.admin_bypass_approval_enabled,
    admin_auto_approve: false,
  };
  const [state, setState] = useState(initialState);

  const inlinePolicyEditorRef = React.createRef();

  useEffect(async () => {
    const langTools = ace.require("ace/ext/language_tools");
    langTools.setCompleters([{ getCompletions }]);
    const { role, permissions } = props;
    const payload = {
      changes: [],
    };
    payload.changes = permissions.map((permission) => {
      const change = {
        principal_arn: role.arn,
        generator_type: permission.service,
        action_groups: permission.actions,
        condition: permission.condition,
        effect: "Allow",
        ...permission,
      };
      delete change.service;
      delete change.actions;
      return change;
    });

    const response = await sendRequestCommon(
      payload,
      "/api/v2/generate_changes"
    );
    if (response.status != null && response.status === 400) {
      return setState({
        ...state,
        isError: true,
        messages: [response.message],
      });
    }

    if ("changes" in response && response.changes.length > 0) {
      const statement = JSON.stringify(
        response.changes[0].policy.policy_document,
        null,
        4
      );
      return setState({
        ...state,
        custom_statement: statement,
        isError: false,
        messages: [],
        statement,
      });
    }
    return setState({
      ...state,
      isError: true,
      messages: ["Unknown Exception raised. Please reach out for support"],
    });
  }, []);

  const handleJSONEditorValidation = (lintErrors) => {
    const { activeIndex } = state;
    const messages = [];
    if (lintErrors.length > 0) {
      for (let i = 0; i < lintErrors.length; i++) {
        messages.push(
          "Lint Error - Row: " +
            lintErrors[i].row +
            ", Column: " +
            lintErrors[i].column +
            ", Error: " +
            lintErrors[i].text
        );
      }
      setState({
        ...state,
        isError: true,
        messages,
      });
    } else if (activeIndex === 1) {
      setState({
        ...state,
        isError: false,
        messages: [],
      });
    }
  };

  const buildAceEditor = (custom_statement) => {
    return (
      <AceEditor
        mode="json"
        theme="monokai"
        width="100%"
        showPrintMargin={false}
        ref={inlinePolicyEditorRef}
        tabSize={4}
        onChange={() => handleJSONEditorChange()}
        onValidate={() => handleJSONEditorValidation()}
        value={custom_statement}
        name="json_editor"
        editorProps={{
          $blockScrolling: true,
        }}
        setOptions={{
          enableBasicAutocompletion: true,
          enableLiveAutocompletion: true,
          wrapBehavioursEnabled: true,
          wrap: true,
          useSoftTabs: true,
        }}
      />
    );
  };

  const buildPermissionsTable = () => {
    const { permissions, services } = props;
    const permissionRows = permissions.map((permission) => {
      const serviceDetail = _.find(services, { key: permission.service });
      return (
        <Table.Row>
          <Table.Cell>{serviceDetail.text}</Table.Cell>
          <Table.Cell collapsing textAlign="left">
            {Object.keys(permission).map((key) => {
              if (
                key === "actions" ||
                key === "service" ||
                key === "condition"
              ) {
                return null;
              }
              return (
                <Label as="a">
                  {key}
                  <Label.Detail>{permission[key]}</Label.Detail>
                </Label>
              );
            })}
          </Table.Cell>
          <Table.Cell>
            {permission.actions.map((action) => {
              const actionDetail = _.find(serviceDetail.actions, {
                name: action,
              });
              return (
                <Label as="a" color="olive">
                  {actionDetail.text}
                </Label>
              );
            })}
          </Table.Cell>
        </Table.Row>
      );
    });

    const permissionTable = (
      <Table celled striped selectable>
        <Table.Header>
          <Table.HeaderCell>Service</Table.HeaderCell>
          <Table.HeaderCell>Resource</Table.HeaderCell>
          <Table.HeaderCell>Actions</Table.HeaderCell>
        </Table.Header>
        <Table.Body>{permissionRows}</Table.Body>
      </Table>
    );

    return permissionTable;
  };

  const handleAdminSubmit = () => {
    setState({
      ...state,
      admin_auto_approve: true,
    });
    handleSubmit();
  };

  const handleSubmit = () => {
    const { role } = props;
    const { custom_statement, justification, admin_auto_approve } = state;
    if (!justification) {
      return setState({
        ...state,
        messages: ["No Justification is Given"],
      });
    }

    const { arn } = role;
    const requestV2 = {
      justification,
      admin_auto_approve,
      changes: {
        changes: [
          {
            principal_arn: arn,
            change_type: "inline_policy",
            action: "attach",
            policy: {
              policy_document: JSON.parse(custom_statement),
            },
          },
        ],
      },
    };

    setState({
      ...state,
      isLoading: true,
    });
    const cb = async () => {
      const response = await sendRequestCommon(requestV2, "/api/v2/request");

      const messages = [];
      if (response) {
        const { request_created, request_id } = response;
        if (request_created === true) {
          return setState({
            ...state,
            isLoading: false,
            isSuccess: true,
            messages,
            requestId: request_id,
          });
        }
        messages.push(
          "Server reported an error with the request: " +
            JSON.stringify(response)
        );
      } else {
        messages.push("Failed to submit request");
      }
      setState({
        ...state,
        isLoading: false,
        messages,
      });
    };
    cb();
  };

  const handleJustificationChange = (e) => {
    setState({
      ...state,
      justification: e.target.value,
    });
  };

  const handleJSONEditorChange = (custom_statement) => {
    const editor = inlinePolicyEditorRef.current.editor;
    if (editor.completer && editor.completer.popup) {
      const popup = editor.completer.popup;
      popup.container.style.width = "600px";
      popup.resize();
    }
    setState({
      ...state,
      custom_statement,
    });
  };

  const { role } = props;
  const {
    admin_bypass_approval_enabled,
    custom_statement,
    isError,
    isLoading,
    isSuccess,
    justification,
    messages,
    requestId,
    statement,
  } = state;

  const active = custom_statement !== statement;
  const messagesToShow =
    messages.length > 0 ? (
      <Message negative>
        <Message.Header>
          We found some problems for this request.
        </Message.Header>
        <Message.List>
          {messages.map((message) => (
            <Message.Item>{message}</Message.Item>
          ))}
        </Message.List>
      </Message>
    ) : null;

  const submission_buttons = admin_bypass_approval_enabled ? (
    <Grid columns={2}>
      <Grid.Row>
        <Grid.Column>
          <Button
            content="Submit and apply without approval"
            disabled={isError}
            onClick={() => handleAdminSubmit()}
            positive
            fluid
          />
        </Grid.Column>
        <Grid.Column>
          <Button
            content="Submit"
            disabled={isError}
            onClick={() => handleSubmit()}
            primary
            fluid
          />
        </Grid.Column>
      </Grid.Row>
    </Grid>
  ) : (
    <Button
      content="Submit"
      disabled={isError}
      fluid
      onClick={() => handleSubmit()}
      primary
    />
  );
  const panes = [
    {
      menuItem: "Review",
      render: () => (
        <Tab.Pane loading={isLoading}>
          <Header>
            Please Review Permissions
            <Header.Subheader>
              You can customize your request using the JSON Editor for advanced
              permissions.
            </Header.Subheader>
          </Header>
          <p>
            Your new permissions will be attached to the role{" "}
            <a
              href={`/policies/edit/${role.account_id}/iamrole/${role.name}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              {role.arn}
            </a>{" "}
            with the following statements:
          </p>
          <Dimmer.Dimmable dimmed={active}>
            {buildPermissionsTable()}
            <Dimmer active={active}>
              <Header as="h2" inverted>
                Your changes made from the JSON Editor will override these
                permissions.
              </Header>
            </Dimmer>
          </Dimmer.Dimmable>
          <Divider />
          <Header>Justification</Header>
          <Form>
            <TextArea
              onChange={() => handleJustificationChange()}
              placeholder="Your Justification"
              value={justification}
            />
          </Form>
          <Divider />
          {messagesToShow}
          {submission_buttons}
        </Tab.Pane>
      ),
    },
    {
      menuItem: "JSON Editor",
      render: () => {
        const jsonEditor = buildAceEditor(custom_statement);
        return (
          <Tab.Pane loading={isLoading}>
            <Header>Edit your permissions in JSON format.</Header>
            <br />
            {jsonEditor}
            <Divider />
            <Header>Justification</Header>
            <Form>
              <TextArea
                onChange={() => handleJustificationChange()}
                placeholder="Your Justification"
                value={justification}
              />
            </Form>
            <Divider />
            {messagesToShow}
            {submission_buttons}
          </Tab.Pane>
        );
      },
    },
  ];

  const tabContent = isSuccess ? (
    <Message positive>
      <Message.Header>Your request was successful.</Message.Header>
      You can check your request status from{" "}
      <a
        href={`/policies/request/${requestId}`}
        target="_blank"
        rel="noopener noreferrer"
      >
        here
      </a>
      .
    </Message>
  ) : (
    <>
      <Tab
        onTabChange={(event, data) =>
          setState({
            ...state,
            activeIndex: data.activeIndex,
          })
        }
        panes={panes}
      />
      <br />
    </>
  );
  return tabContent;
};

export default SelfServiceStep3;
