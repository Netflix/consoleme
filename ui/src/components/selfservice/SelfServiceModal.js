import "./SelfService.css";
import {
  Button,
  Divider,
  Form,
  Grid,
  GridColumn,
  Header,
  Message,
  Modal,
  TextArea,
} from "semantic-ui-react";
import React, { Component } from "react";
import "brace";
import "brace/ext/language_tools";
import "brace/theme/monokai";
import "brace/mode/json";
import MonacoEditor from "react-monaco-editor";
import * as monaco from "monaco-editor/esm/vs/editor/editor.api.js";
import SelfServiceComponent from "./SelfServiceComponent";

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

const base_template = `{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [

            ],
            "Effect": "Allow",
            "Resource": [

            ]
        }
    ]
}`;

class SelfServiceModal extends Component {
  constructor(props) {
    super(props);
    this.state = {
      open: false,
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
      values: {},
    };
    this.inlinePolicyEditorRef = React.createRef();
    this.onChange = this.onChange.bind(this);
    this.editorDidMount = this.editorDidMount.bind(this);
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

  buildMonacoEditor(base_template) {
    return (
      <MonacoEditor
        height="500px"
        language="json"
        width="100%"
        theme="vs-dark"
        value={base_template}
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
    let { open, setOpen } = this.props;
    const {
      admin_bypass_approval_enabled,
      custom_statement,
      isError,
      justification,
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
        />
      </Modal.Actions>
    );

    const jsonEditor = this.buildMonacoEditor(base_template);

    return (
      <Modal trigger={<a>Advanced Editor</a>}>
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
        </Modal.Content>
      </Modal>
    );
  }
}

export default SelfServiceModal;
