import _ from "lodash";
import React, { Component } from "react";
import {
  Button,
  Dimmer,
  Divider,
  Form,
  Grid,
  Header,
  Icon,
  Label,
  Message,
  Popup,
  Tab,
  Table,
  TextArea,
} from "semantic-ui-react";
import "brace";
import "brace/ext/language_tools";
import "brace/theme/monokai";
import "brace/mode/json";
import * as monaco from "monaco-editor/esm/vs/editor/editor.api.js";
import { MonacoDiffEditor } from "react-monaco-editor";

class SelfServiceStep3 extends Component {
  constructor(props) {
    super(props);
    this.state = {
      activeIndex: 0,
      custom_statement: "",
      isError: false,
      isLoading: false,
      isSuccess: false,
      justification: "",
      messages: [],
      requestId: null,
      statement: "",
      admin_bypass_approval_enabled: this.props.admin_bypass_approval_enabled,
      export_to_terraform_enabled: this.props.export_to_terraform_enabled,
      admin_auto_approve: false,
      policy_name: "",
    };
    this.inlinePolicyEditorRef = React.createRef();
    this.onChange = this.onChange.bind(this);
    this.editorDidMount = this.editorDidMount.bind(this);
    this.handleJustificationChange = this.handleJustificationChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
    this.handleAdminSubmit = this.handleAdminSubmit.bind(this);
  }

  editorDidMount(editor) {
    editor.modifiedEditor.onDidChangeModelDecorations(() => {
      const { modifiedEditor } = this.state;
      const model = modifiedEditor.getModel();
      if (model === null || model.getModeId() !== "json") {
        return;
      }

      const owner = model.getModeId();
      const uri = model.uri;
      const markers = monaco.editor.getModelMarkers({ owner, resource: uri });
      this.onLintError(
        markers.map(
          (marker) =>
            `Lint error on line ${marker.startLineNumber} columns ${marker.startColumn}-${marker.endColumn}: ${marker.message}`
        )
      );
    });
    this.setState({
      modifiedEditor: editor.modifiedEditor,
    });
  }

  buildMonacoEditor() {
    const { oldValue, newValue, readOnly, updated_policy } = this.props;
    const options = {
      selectOnLineNumbers: true,
      renderSideBySide: true,
      enableSplitViewResizing: false,
      quickSuggestions: true,
      scrollbar: {
        alwaysConsumeMouseWheel: false,
      },
      scrollBeyondLastLine: false,
      automaticLayout: true,
      readOnly,
    };
    return (
      <MonacoDiffEditor
        language="json"
        width="100%"
        height="500"
        original={oldValue}
        value={updated_policy}
        editorWillMount={this.editorWillMount}
        editorDidMount={this.editorDidMount}
        options={options}
        onChange={this.onChange}
        theme="vs-light"
        alwaysConsumeMouseWheel={false}
      />
    );
  }

  buildPermissionsTable() {
    const { permissions, services } = this.props;
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
  }

  handleAdminSubmit() {
    this.setState(
      {
        admin_auto_approve: true,
      },
      () => {
        this.handleSubmit();
      }
    );
  }

  handleSubmit() {
    const { role } = this.props;
    const { custom_statement, justification, admin_auto_approve } = this.state;
    if (!justification) {
      return this.setState((state) => ({
        messages: ["No Justification is Given"],
      }));
    }

    const { arn } = role;
    const requestV2 = {
      justification,
      admin_auto_approve,
      changes: {
        changes: [
          {
            principal: {
              principal_arn: arn,
              principal_type: "AwsResource",
            },
            change_type: "inline_policy",
            action: "attach",
            policy: {
              policy_document: JSON.parse(custom_statement),
            },
          },
        ],
      },
    };

    this.setState(
      {
        isLoading: true,
      },
      async () => {
        const response = await this.props.sendRequestCommon(
          requestV2,
          "/api/v2/request"
        );

        const messages = [];
        if (response) {
          const { request_created, request_id } = response;
          if (request_created === true) {
            return this.setState({
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
        this.setState({
          isLoading: false,
          messages,
        });
      }
    );
  }

  handleJustificationChange(e) {
    this.setState({
      justification: e.target.value,
    });
  }

  onChange(newValue, e) {
    this.onValueChange(newValue);
  }

  onLintError = (lintErrors) => {
    if (lintErrors.length > 0) {
      this.setState({
        messages: lintErrors,
        isError: true,
      });
    } else {
      this.setState({
        messages: [],
        isError: false,
      });
    }
  };

  render() {
    const { role } = this.props;
    const {
      admin_bypass_approval_enabled,
      custom_statement,
      export_to_terraform_enabled,
      isError,
      isLoading,
      isSuccess,
      justification,
      messages,
      requestId,
      statement,
    } = this.state;

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
              onClick={this.handleAdminSubmit}
              positive
              fluid
            />
          </Grid.Column>
          <Grid.Column>
            <Button
              content="Submit"
              disabled={isError}
              onClick={this.handleSubmit}
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
        onClick={this.handleSubmit}
        primary
      />
    );

    const jsonEditor = this.buildMonacoEditor();
    return (
       <div>
         <Header size={'huge'}>Review Changes & Submit</Header>
         <p>Use the following editor to review the changes you've modified before submitting for team review.</p>
         {jsonEditor}
         <Divider />
         <Header>Justification</Header>
         <Form>
           <TextArea
              onChange={this.handleJustificationChange}
              placeholder="Your Justification"
              value={justification}
           />
         </Form>
         <Divider />
         {messagesToShow}
         {submission_buttons}
       </div>
    );

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
            this.setState({
              activeIndex: data.activeIndex,
            })
          }
        />
        <br />
      </>
    );
    return tabContent;
  }
}

export default SelfServiceStep3;
