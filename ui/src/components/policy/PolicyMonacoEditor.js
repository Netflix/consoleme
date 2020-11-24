import React, { useEffect, useState } from "react";
import { Button, Form, Icon, Message, Segment } from "semantic-ui-react";
import MonacoEditor from "react-monaco-editor";
import * as monaco from "monaco-editor/esm/vs/editor/editor.api.js";
import {
  getMonacoCompletions,
  getMonacoTriggerCharacters,
} from "../../helpers/utils";
import templateOptions from "./policyTemplates";
import { usePolicyContext } from "./hooks/PolicyProvider";
import { useAuth } from "../../auth/AuthProvider";

monaco.languages.registerCompletionItemProvider("json", {
  triggerCharacters: getMonacoTriggerCharacters(),
  async provideCompletionItems(model, position) {
    return await getMonacoCompletions(model, position, monaco);
  },
});

const editorOptions = {
  selectOnLineNumbers: true,
  quickSuggestions: true,
  scrollbar: {
    alwaysConsumeMouseWheel: false,
  },
  scrollBeyondLastLine: false,
  automaticLayout: true,
};

// Stub lint error callback, will be setup later
let onLintError = () => {};

const editorDidMount = (editor) => {
  editor.onDidChangeModelDecorations(() => {
    const model = editor.getModel();
    if (model === null || model.getModeId() !== "json") {
      return;
    }

    const owner = model.getModeId();
    const uri = model.uri;
    const markers = monaco.editor.getModelMarkers({ owner, resource: uri });
    onLintError(
      markers.map(
        (marker) =>
          `Lint error on line ${marker.startLineNumber} columns ${marker.startColumn}-${marker.endColumn}: ${marker.message}`
      )
    );
  });
};

export const PolicyMonacoEditor = ({
  context,
  policy,
  updatePolicy,
  deletePolicy,
}) => {
  const { user } = useAuth();
  const { setModalWithAdminAutoApprove } = usePolicyContext();

  const policyDocumentOriginal = JSON.stringify(
    policy.PolicyDocument,
    null,
    "\t"
  );
  const [policyDocument, setPolicyDocument] = useState(policyDocumentOriginal);
  const [error, setError] = useState("");

  useEffect(() => {
    setPolicyDocument(policyDocumentOriginal);
  }, [policyDocumentOriginal]);

  const onEditChange = (value) => {
    setPolicyDocument(value);
  };

  onLintError = (lintErrors) => {
    if (lintErrors.length > 0) {
      setError(`LintErrors: ${JSON.stringify(lintErrors)}`);
    } else {
      setError("");
    }
  };

  const handlePolicyAdminSave = () => {
    updatePolicy({
      ...policy,
      PolicyDocument: JSON.parse(policyDocument),
    });
    setModalWithAdminAutoApprove(true);
  };

  const handlePolicySubmit = () => {
    updatePolicy({
      ...policy,
      PolicyDocument: JSON.parse(policyDocument),
    });
    setModalWithAdminAutoApprove(false);
  };

  const handleDelete = () => {
    deletePolicy({
      ...policy,
      PolicyDocument: JSON.parse(policyDocument),
    });
    setModalWithAdminAutoApprove(true);
  };

  return (
    <>
      <Message warning attached="top">
        <Icon name="warning" />
        {error || `You are editing the policy ${policy.PolicyName}.`}
      </Message>
      <Segment
        attached
        style={{
          border: 0,
          padding: 0,
        }}
      >
        <MonacoEditor
          height="540px"
          language="json"
          theme="vs-dark"
          value={policyDocument}
          onChange={onEditChange}
          options={editorOptions}
          editorDidMount={editorDidMount}
          textAlign="center"
        />
      </Segment>
      <Button.Group attached="bottom">
        {user?.authorization?.can_edit_policies ? (
          <>
            <Button
              positive
              icon="save"
              content="Save"
              onClick={handlePolicyAdminSave}
              disabled={
                error ||
                !policyDocument ||
                policyDocumentOriginal === policyDocument
              }
            />
            <Button.Or />
          </>
        ) : null}
        <Button
          primary
          icon="send"
          content="Submit"
          onClick={handlePolicySubmit}
          disabled={
            error ||
            !policyDocument ||
            policyDocumentOriginal === policyDocument
          }
        />
        {
          // Show delete button for inline policies only
          context === "inline_policy" ? (
            <>
              <Button.Or />
              <Button
                negative
                icon="remove"
                content="Delete"
                onClick={handleDelete}
              />{" "}
            </>
          ) : null
        }
      </Button.Group>
    </>
  );
};

export const NewPolicyMonacoEditor = ({ addPolicy, setIsNewPolicy }) => {
  const { user } = useAuth();
  const { setModalWithAdminAutoApprove } = usePolicyContext();

  const [newPolicyName, setNewPolicyName] = useState("");
  const [policyDocument, setPolicyDocument] = useState(
    JSON.stringify(JSON.parse(templateOptions[0].value), null, "\t")
  );
  const [error, setError] = useState("");
  const [policyNameError, setpolicyNameError] = useState(false);
  const policyNameRegex = /^[\w+=,.@-]+$/;

  const onEditChange = (value) => {
    setPolicyDocument(value);
  };

  onLintError = (lintErrors) => {
    if (lintErrors.length > 0) {
      setError(`LintErrors: ${JSON.stringify(lintErrors)}`);
    } else {
      setError("");
    }
  };

  const handleChangeNewPolicyName = (e) => {
    const policyName = e.target.value;
    if (policyName && !policyNameRegex.test(policyName)) {
      setpolicyNameError(true);
      return;
    }
    setpolicyNameError(false);
    setNewPolicyName(policyName);
  };

  const handlePolicyAdminSave = () => {
    addPolicy({
      PolicyName: newPolicyName,
      PolicyDocument: JSON.parse(policyDocument),
    });
    setModalWithAdminAutoApprove(true);
  };

  const handlePolicySubmit = () => {
    addPolicy({
      PolicyName: newPolicyName,
      PolicyDocument: JSON.parse(policyDocument),
    });
    setModalWithAdminAutoApprove(false);
  };

  const onTemplateChange = (e, { value }) => {
    setPolicyDocument(JSON.stringify(JSON.parse(value || ""), null, "\t"));
  };

  return (
    <>
      <Segment attached="top" color="green">
        <Form>
          <Form.Group widths="equal">
            <Form.Input
              id="inputNew"
              error={policyNameError}
              label="Policy Name"
              placeholder="(Optional) Enter a Policy Name"
              onChange={handleChangeNewPolicyName}
            />
            <Form.Dropdown
              label="Template"
              placeholder="Choose a template to add."
              selection
              onChange={onTemplateChange}
              options={templateOptions}
              defaultValue={templateOptions[0].key}
            />
          </Form.Group>
        </Form>
      </Segment>
      <Segment
        attached
        style={{
          border: 0,
          padding: 0,
        }}
      >
        <MonacoEditor
          height="540px"
          language="json"
          theme="vs-dark"
          value={policyDocument}
          onChange={onEditChange}
          options={editorOptions}
          editorDidMount={editorDidMount}
          textAlign="center"
        />
      </Segment>
      <Button.Group attached="bottom">
        {user?.authorization?.can_edit_policies ? (
          <>
            <Button
              positive
              icon="save"
              content="Save"
              onClick={handlePolicyAdminSave}
              disabled={error || policyNameError || !policyDocument}
            />
            <Button.Or />
          </>
        ) : null}
        <Button
          primary
          icon="send"
          content="Submit"
          onClick={handlePolicySubmit}
          disabled={error || policyNameError || !policyDocument}
        />
        <Button.Or />
        <Button
          negative
          icon="remove"
          content="Cancel"
          onClick={() => setIsNewPolicy(false)}
        />
      </Button.Group>
    </>
  );
};
