import React, { useEffect, useState, useRef } from "react";
import { Button, Form, Icon, Message, Segment } from "semantic-ui-react";
import MonacoEditor from "react-monaco-editor";
import * as monaco from "monaco-editor/esm/vs/editor/editor.api.js";
import {
  getMonacoCompletions,
  getMonacoTriggerCharacters,
} from "../../helpers/utils";
import { usePolicyContext } from "./hooks/PolicyProvider";
import { useAuth } from "../../auth/AuthProviderDefault";
import "./PolicyMonacoEditor.css";

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

const INFO_ERRORS = ["MUTE", "INFO", "LOW"];
const WARNING_ERRORS = ["MEDIUM"];
const CRITICAL_ERRORS = ["HIGH", "CRITICAL"];

const lintingErrorMapping = {
  MUTE: "infoError",
  INFO: "infoError",
  LOW: "infoError",
  MEDIUM: "warningError",
  HIGH: "criticalError",
  CRITICAL: "criticalError",
};

const LintingErrors = ({ policyErrors }) => (
  <Message>
    <Message.Header>Errors</Message.Header>
    {policyErrors.map((policyError, index) => (
      <Message
        key={index}
        info={INFO_ERRORS.includes(policyError.severity)}
        warning={WARNING_ERRORS.includes(policyError.severity)}
        error={CRITICAL_ERRORS.includes(policyError.severity)}
      >
        <Message.Header style={{ marginBottom: "5px" }}>
          {policyError.severity}{" "}
          {policyError.location &&
            policyError.location.line &&
            `- line ${policyError.location.line}`}
        </Message.Header>
        {policyError.title} <br />
        {policyError.detail && (
          <>
            <b>Detail:</b> {policyError.detail}
            <br />
          </>
        )}
        {policyError.description && (
          <>
            <b>Description:</b> {policyError.description}
            <br />
          </>
        )}
      </Message>
    ))}
  </Message>
);

const clearEditorDecorations = ({ editor }) => {
  editor
    .getModel()
    .getAllDecorations()
    .filter((el) =>
      ["criticalError", "warningError", "infoError"].includes(
        el.options.className
      )
    )
    .map((el) => el.reset());
};

const addEditorDecorations = ({ editor, errors }) => {
  editor.deltaDecorations(
    [],
    errors
      .filter((error) => error.location && error.location.line)
      .map((error) => ({
        range: new monaco.Range(
          error.location.line,
          1,
          error.location.line,
          100
        ),
        options: {
          isWholeLine: true,
          className: lintingErrorMapping[error.severity],
          marginClassName: "warningIcon",
          hoverMessage: {
            value: error.detail,
          },
        },
      }))
  );
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
  const { user, sendRequestCommon } = useAuth();
  const { setModalWithAdminAutoApprove } = usePolicyContext();
  const [policyErrors, setPolicyErrors] = useState([]);
  const [hasBeenChecked, setChecked] = useState(false);
  const editorRef = useRef();

  const policyDocumentOriginal = JSON.stringify(
    policy.PolicyDocument,
    null,
    "\t"
  );
  const [policyDocument, setPolicyDocument] = useState(policyDocumentOriginal);
  const [error, setError] = useState("");

  useEffect(() => {
    setPolicyDocument(policyDocumentOriginal);
    setPolicyErrors([]);
  }, [policyDocumentOriginal]);

  const onEditChange = (value) => {
    clearEditorDecorations({ editor: editorRef.current.editor });
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

  const handlePolicyCheck = async () => {
    const errors = await sendRequestCommon(
      policyDocument,
      "/api/v2/policies/check",
      "post"
    );
    if (errors) {
      setChecked(true);
      setPolicyErrors(errors);

      // Clear all existing decorations otherwise they will add up
      clearEditorDecorations({ editor: editorRef.current.editor });
      addEditorDecorations({ editor: editorRef.current.editor, errors });
    }
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
          paddingRight: 0,
          paddingLeft: 0,
        }}
      >
        <MonacoEditor
          ref={editorRef}
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
      {!!policyErrors.length && <LintingErrors policyErrors={policyErrors} />}
      {policyErrors.length === 0 && hasBeenChecked && (
        <Message positive>No errors</Message>
      )}
      <Button.Group attached="bottom">
        <Button
          positive
          icon="check"
          content="Check"
          onClick={handlePolicyCheck}
          disabled={error || !policyDocument}
        />
        <Button.Or />
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
          context === "inline_policy" &&
          user?.authorization?.can_edit_policies ? (
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
  const { user, sendRequestCommon } = useAuth();
  const { setModalWithAdminAutoApprove } = usePolicyContext();
  const [policyErrors, setPolicyErrors] = useState([]);
  const [hasBeenChecked, setHasBeenChecked] = useState(false);
  const editorRef = useRef();

  const [newPolicyName, setNewPolicyName] = useState("");
  const [templateOptions, setTemplateOptions] = useState([
    { key: "default", text: "", value: "{}" },
  ]);
  const [templateDefaultKey, setTemplateDefaultKey] = useState(
    "Default Policy"
  );

  const [policyDocument, setPolicyDocument] = useState("");
  const [error, setError] = useState("");
  const [policyNameError, setpolicyNameError] = useState(false);
  const policyNameRegex = /^[\w+=,.@-]+$/;

  const onEditChange = (value) => {
    clearEditorDecorations({ editor: editorRef.current.editor });
    setPolicyDocument(value);
  };

  useEffect(() => {
    (async () => {
      const data = await sendRequestCommon(
        null,
        "/api/v2/permission_templates/",
        "get"
      );
      if (!data) {
        return;
      }
      setTemplateOptions(data.permission_templates);
      setPolicyDocument(
        JSON.stringify(JSON.parse(templateOptions[0].value), null, "\t")
      );
      setTemplateDefaultKey(templateOptions[0].key);
    })();
  }, []); // eslint-disable-line

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

  const handlePolicyCheck = async () => {
    const errors = await sendRequestCommon(
      policyDocument,
      "/api/v2/policies/check",
      "post"
    );
    if (errors) {
      setHasBeenChecked(true);
      setPolicyErrors(errors);

      // Clear all existing decorations otherwise they will add up
      clearEditorDecorations({ editor: editorRef.current.editor });
      addEditorDecorations({ editor: editorRef.current.editor, errors });
    }
  };

  const handlePolicySubmit = () => {
    addPolicy({
      PolicyName: newPolicyName,
      PolicyDocument: JSON.parse(policyDocument),
    });
    setModalWithAdminAutoApprove(false);
  };

  const onTemplateChange = (e, { value }) => {
    clearEditorDecorations({ editor: editorRef.current.editor });
    setPolicyErrors([]);
    setHasBeenChecked(false);
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
              defaultValue={templateDefaultKey}
            />
          </Form.Group>
        </Form>
      </Segment>
      <Segment
        attached
        style={{
          border: 0,
          paddingRight: 0,
          paddingLeft: 0,
        }}
      >
        <MonacoEditor
          ref={editorRef}
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
      {!!policyErrors.length && <LintingErrors policyErrors={policyErrors} />}
      {policyErrors.length === 0 && hasBeenChecked && (
        <Message positive>No errors</Message>
      )}
      <Button.Group attached="bottom">
        <Button
          positive
          icon="check"
          content="Check"
          onClick={handlePolicyCheck}
          disabled={error || policyNameError || !policyDocument}
        />
        <Button.Or />
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
