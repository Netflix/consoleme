import React, { useEffect, useState } from "react";
import { Button, Form, Icon, Message, Segment } from "semantic-ui-react";
import MonacoEditor from "react-monaco-editor";
import {
  getMonacoCompletions,
  getMonacoTriggerCharacters,
} from "../../helpers/utils";
import * as monaco from "monaco-editor";
import { templateOptions } from "./policyTemplates";
import { usePolicyContext } from "./hooks/PolicyProvider";

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

const onLintError = (lintErrors) => {
  // TODO: heewonk - Display these lint errors if they exist
  console.log("LintErrors: " + JSON.stringify(lintErrors));
  // const [lintErrors, setLintErrors] = useState([])
  // const [isError, setIsError] = useState(false)
  // if (lintErrors.length > 0) {
  //     setLintErrors(lintErrors)
  //     setIsError(true)
  // } else {
  //   setLintErrors([])
  //   setIsError(false)
  // }
};

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

export const PolicyMonacoEditor = ({ policy, policyType }) => {
  const {
    deletePolicy,
    updatePolicy,
    setAdminAutoApprove,
    setTogglePolicyModal,
    setPolicyType,
  } = usePolicyContext();

  const [policyDocument, setPolicyDocument] = useState(
    JSON.stringify(policy.PolicyDocument, null, "\t")
  );

  const onEditChange = (value) => {
    setPolicyDocument(value);
  };

  const handlePolicyAdminSave = (e) => {
    updatePolicy({
      ...policy,
      PolicyDocument: JSON.parse(policyDocument),
    });
    setAdminAutoApprove(true);
    setTogglePolicyModal(true);
    setPolicyType(policyType);
  };

  const handlePolicySubmit = (e) => {
    updatePolicy({
      ...policy,
      PolicyDocument: JSON.parse(policyDocument),
    });
    setAdminAutoApprove(false);
    setTogglePolicyModal(true);
    setPolicyType(policyType);
  };

  const handleDelete = (e) => {
    deletePolicy({
      ...policy,
      PolicyDocument: JSON.parse(policyDocument),
    });
    setAdminAutoApprove(true);
    setTogglePolicyModal(true);
    setPolicyType(policyType);
  };

  return (
    <>
      <Message warning attached="top">
        <Icon name="warning" />
        {`You are editing the policy ${policy.PolicyName}.`}
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
        <Button
          positive
          icon="save"
          content="Save"
          onClick={handlePolicyAdminSave}
        />
        <Button.Or />
        <Button
          primary
          icon="send"
          content="Submit"
          onClick={handlePolicySubmit}
        />
        {
          // Show delete button for inline policies only
          policyType === "inline_policy" ? (
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

export const NewPolicyMonacoEditor = (policyType) => {
  const {
    addPolicy,
    setIsNewPolicy,
    setAdminAutoApprove,
    setTogglePolicyModal,
    setPolicyType,
  } = usePolicyContext();

  const [newPolicyName, setNewPolicyName] = useState("");
  const [policyDocument, setPolicyDocument] = useState(
    JSON.stringify(JSON.parse(templateOptions[0].value), null, "\t")
  );

  const onEditChange = (value) => {
    try {
      setPolicyDocument(JSON.stringify(JSON.parse(value), null, "\t"));
    } catch {}
  };

  const handleChangeNewPolicyName = (e) => {
    // TODO, make sure there is no duplicate policy names
    setNewPolicyName(e.target.value);
  };

  const handlePolicyAdminSave = (e) => {
    addPolicy({
      PolicyName: newPolicyName,
      PolicyDocument: JSON.parse(policyDocument),
    });
    setAdminAutoApprove(true);
    setTogglePolicyModal(true);
    setPolicyType(policyType);
  };

  const handlePolicySubmit = (e) => {
    addPolicy({
      PolicyName: newPolicyName,
      PolicyDocument: JSON.parse(policyDocument),
    });
    setAdminAutoApprove(false);
    setTogglePolicyModal(true);
    setPolicyType(policyType);
  };

  const onTemplateChange = (e, { value }) => {
    onEditChange(value);
  };

  return (
    <>
      <Segment attached="top" color="green">
        <Form>
          <Form.Group widths="equal">
            <Form.Input
              id="inputNew"
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
        <Button
          positive
          icon="save"
          content="Save"
          onClick={handlePolicyAdminSave}
        />
        <Button.Or />
        <Button
          primary
          icon="send"
          content="Submit"
          onClick={handlePolicySubmit}
        />
        <Button.Or />
        <Button
          negative
          icon="remove"
          content="Cancel"
          onClick={setIsNewPolicy}
        />
      </Button.Group>
    </>
  );
};
