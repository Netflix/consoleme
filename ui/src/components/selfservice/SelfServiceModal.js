import "./SelfService.css";
import { Button, Divider, Header, Message, Modal } from "semantic-ui-react";
import React, { Component } from "react";
import "brace";
import "brace/ext/language_tools";
import "brace/theme/monokai";
import "brace/mode/json";
import MonacoEditor from "react-monaco-editor";
import * as monaco from "monaco-editor/esm/vs/editor/editor.api.js";

const editor_options = {
  selectOnLineNumbers: true,
  readOnly: false,
  quickSuggestions: true,
  scrollbar: {
    alwaysConsumeMouseWheel: false,
  },
  scrollBeyondLastLine: false,
  automaticLayout: true,
};

const blank_statement = `{
    "Version": "2012-10-17",
      "Statement": [
        {
          "Action": [],
          "Effect": "Allow",
          "Resource": []
        }
      ]
  }`;

class SelfServiceModal extends Component {
  constructor(props) {
    super(props);
    this.state = {
      activeIndex: 0,
      isError: false,
      isLoading: false,
      isSuccess: false,
      messages: [],
      requestId: null,
      admin_bypass_approval_enabled: this.props.admin_bypass_approval_enabled,
      export_to_terraform_enabled: this.props.export_to_terraform_enabled,
      admin_auto_approve: false,
      payloadPermissions: [],
    };
    this.inlinePolicyEditorRef = React.createRef();
    this.onChange = this.onChange.bind(this);
    this.editorDidMount = this.editorDidMount.bind(this);
    this.updateStatement = this.updateStatement.bind(this);
  }

  async updateStatement() {
    const { role, permissions } = this.props;
    const payload = {
      changes: [],
    };

    payload.changes = permissions.map((permission) => {
      const change = {
        principal: {
          principal_arn: role.arn,
          principal_type: "AwsResource",
        },
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

    const response = await this.props.sendRequestCommon(
      payload,
      "/api/v2/generate_changes"
    );
    if (response.status != null && response.status === 400) {
      return this.setState({
        isError: true,
        messages: [response.message],
      });
    }

    if ("changes" in response && response.changes.length > 0) {
      const policy_name = response.changes[0].policy_name;
      const statement = JSON.stringify(
        response.changes[0].policy.policy_document,
        null,
        4
      );
      return this.setState({
        custom_statement: statement,
        isError: false,
        messages: [],
        policy_name,
        statement,
      });
    }
    return this.setState({
      custom_statement: blank_statement,
      isError: false,
      messages: [],
    });
  }

  addToPolicy() {
    const value = monaco.editor.getModels()[0].getValue();
    const parseValue = JSON.parse(value);
  }

  addToPolicy() {
    const value = monaco.editor.getModels()[0].getValue();
    const parseValue = JSON.parse(value);
    const payload = parseValue.Statement;
    let payloadPermissions = [];

    payload.forEach((item) => {
      let service = item.Action[0];
      const regex = new RegExp(`([^x$:]+)`);
      const bucketRegex = new RegExp(`[^/]*$`);
      let result = regex.exec(service);
      let bucketPrefix = bucketRegex.exec(item.Resource[1]);
      let serviceType = result[0];
      let permission = {};
      let permissions = [];

      let actions = this.getAllActionItems(item.Action, serviceType);
      console.log(`serviceType == ${serviceType}`);
      if (serviceType === "s3") {
        console.log(`s3 actions - ${actions}`);
        permission = {
          actions: actions,
          bucket_prefix: `/${bucketPrefix}`,
          condition: "",
          resource_arn: item.Resource[0],
          service: serviceType,
        };
        permissions.push(permission);
      } else if (serviceType === "iam") {
        console.log(`other actions - ${actions}`);
        permission = {
          actions: actions,
          condition: "",
          resource_arn: item.Resource[0],
          service: "rds",
        };
        permissions.push(permission);
      } else {
        console.log(`other actions - ${actions}`);
        permission = {
          actions: actions,
          condition: "",
          resource_arn: item.Resource[0],
          service: serviceType,
        };
        permissions.push(permission);
      }

      payloadPermissions.push(permission);
    });

    if (payloadPermissions.length > 0) {
      payloadPermissions.forEach((item) =>
        this.props.updatePayloadPermissions(item)
      );
    }
  }

  getAllActionItems(actions, serviceType) {
    switch (serviceType) {
      case "s3":
        const s3Regex = /^.*(get|put|list|delete).*$/gm;
        const s3Results = [];

        for (let i = 0, l = actions.length; i < l; i++) {
          let s3Result = s3Regex.exec(actions[i]);

          if (s3Result !== null) {
            s3Results.push(s3Result[1]);
          }
        }
        return [...new Set(s3Results)];
        break;
      case "sqs":
        const sqsResults = [];

        for (let i = 0, l = actions.length; i < l; i++) {
          if (actions[i] === "sqs:sendmessage") {
            sqsResults.push("send_messages");
          } else if (actions[i] === "sqs:receivemessage") {
            sqsResults.push("receive_messages");
          } else if (actions[i] === "sqs:setqueueattributes") {
            sqsResults.push("set_queue_attributes");
          } else if (actions[i] === "sqs:purgequeue") {
            sqsResults.push("purge_messages");
          }
        }
        return [...new Set(sqsResults)];
        break;

      case "sns":
        const snsResults = [];

        for (let i = 0, l = actions.length; i < l; i++) {
          if (actions[i] === "sns:getendpointattributes") {
            snsResults.push("get_topic_attributes");
          } else if (actions[i] === "sns:publish") {
            snsResults.push("publish");
          } else if (actions[i] === "sns:subscribe") {
            snsResults.push("subscribe");
          } else if (actions[i] === "sns:unsubscribe") {
            snsResults.push("unsubscribe");
          }
        }
        return [...new Set(snsResults)];
        break;

      case "rds":
        const rdsResults = [];

        for (let i = 0, l = actions.length; i < l; i++) {
          if (actions[i] === "iam:passrole") {
            rdsResults.push("iam:passrole");
          }
        }
        return [...new Set(rdsResults)];
        break;

      case "ec2":
        const ec2Results = [];

        for (let i = 0, l = actions.length; i < l; i++) {
          if (actions[i] === "ec2:assignipv6addresses") {
            ec2Results.push("ipv6");
          } else if (actions[i] === "ec2:attachvolume") {
            ec2Results.push("volmount");
          }
        }
        return [...new Set(ec2Results)];
        break;

      case "route53":
        const route53Regex = /^.*(list|change).*$/gm;
        const route53Results = [];

        for (let i = 0, l = actions.length; i < l; i++) {
          let route53Result = route53Regex.exec(actions[i]);

          if (route53Result !== null) {
            if (route53Result === ["list"]) {
              route53Results.push("list_records");
            } else if (route53Result === ["change"]) {
              route53Results.push("change_records");
            }
          }
        }
        return [...new Set(route53Results)];
        break;

      case "sts":
        const stsRegex = /^.*(assumerole).*$/gm;
        const stsResults = [];

        for (let i = 0, l = actions.length; i < l; i++) {
          let stsResult = stsRegex.exec(actions[i]);

          if (stsResult !== null) {
            stsResults.push("assume_role");
          }
        }
        return [...new Set(stsResults)];
        break;

      default:
        return;
    }
  }

  editorDidMount(editor) {
    editor.onDidChangeModelDecorations(() => {
      const model = editor.getModel();

      if (model === null || model.getModeId() !== "json") {
        return;
      }

      const owner = model.getModeId();
      const uri = model.uri;
      const markers = monaco.editor.getModelMarkers({ owner, resource: uri });
      this.onLintError(
        markers.map(
          (marker) =>
            `Lint error on line ${marker.startLineNumber} columns ${marker.startColumn}-${marker.endColumn}:
               ${marker.message}`
        )
      );
    });
  }

  buildMonacoEditor(custom_statement) {
    return (
      <MonacoEditor
        height="500px"
        language="json"
        width="100%"
        theme="vs-dark"
        value={custom_statement}
        onChange={this.onChange}
        options={editor_options}
        editorDidMount={this.editorDidMount}
        textAlign="center"
      />
    );
  }

  onChange(newValue, e) {
    this.setState({
      custom_statement: newValue,
    });
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
      isError,
      messages,
      statement,
    } = this.state;

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
      <Modal.Actions>
        <Button
          content="Submit and apply without approval"
          disabled={isError}
          onClick={this.handleAdminSubmit}
          positive
          fluid
        />
        <Button
          content="Submit"
          disabled={isError}
          onClick={this.handleSubmit}
          primary
          fluid
        />
      </Modal.Actions>
    ) : (
      <Modal.Actions>
        <Button>Cancel</Button>
        <Button
          content="Add to Policy"
          labelPosition="right"
          icon="checkmark"
          primary
          onClick={this.addToPolicy.bind(this)}
        />
      </Modal.Actions>
    );

    const jsonEditor = this.buildMonacoEditor(custom_statement);

    return (
      <Modal
        closeIcon
        trigger={<a onClick={this.updateStatement}>Advanced Editor</a>}
      >
        <Header>Advanced Editor</Header>
        <Message info>
          <Message.Header>Edit your permissions in JSON format.</Message.Header>
          <p>
            Helpful text about how to use the Advanced Editor, JSON syntax, etc.
          </p>
        </Message>
        <Modal.Content>
          {jsonEditor}
          <Divider />
          {messagesToShow}
          {submission_buttons}
        </Modal.Content>
      </Modal>
    );
  }
}

export default SelfServiceModal;
