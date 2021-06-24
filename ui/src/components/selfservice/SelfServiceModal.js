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
      modal_statement: this.props.updated_policy,
      open: false,
    };
    this.inlinePolicyEditorRef = React.createRef();
    this.onChange = this.onChange.bind(this);
    this.editorDidMount = this.editorDidMount.bind(this);
  }

  addToPolicy() {
    const value = this.state.modal_statement;
    this.props.updateStatement(value);
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

  buildMonacoEditor(modal_statement) {
    if (modal_statement === "") {
      modal_statement = blank_statement;
    }

    return (
      <MonacoEditor
        height="500px"
        language="json"
        width="100%"
        theme="vs-dark"
        value={modal_statement}
        onChange={this.onChange}
        options={editor_options}
        editorDidMount={this.editorDidMount}
        textAlign="center"
      />
    );
  }

  onChange(newValue, e) {
    this.setState({
      modal_statement: newValue,
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
    const {
      admin_bypass_approval_enabled,
      isError,
      messages,
      modal_statement,
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
        <Button onClick={() => this.setState({open:false})}>Cancel</Button>
        <Button
          content="Add to Policy"
          labelPosition="right"
          icon="checkmark"
          primary
          onClick={this.addToPolicy.bind(this)}
        />
      </Modal.Actions>
    );

    const jsonEditor = this.buildMonacoEditor(modal_statement);

    return (
      // TODO: Resolve lint error with the following line
      <Modal closeIcon onOpen={() => this.setState({open:true})} onClose={() => this.setState({open:false})}
             open={this.state.open} trigger={<a>Advanced Editor</a>}>
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
