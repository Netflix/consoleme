import React, { useEffect, useRef, useState, useCallback } from "react";
import {
  Accordion,
  Button,
  Form,
  Icon,
  Header,
  Message,
  Ref,
  Segment,
  Modal,
  Dimmer,
  TextArea,
} from "semantic-ui-react";
import MonacoEditor from "react-monaco-editor";
import { Link } from "react-router-dom";

import { templateOptions } from "./policyTemplates";
import { sendRequestCommon } from "../../helpers/utils";
import ReactMarkdown from "react-markdown";

import {
  getMonacoCompletions,
  getMonacoTriggerCharacters,
} from "../../helpers/utils";
import * as monaco from "monaco-editor";

monaco.languages.registerCompletionItemProvider("json", {
  triggerCharacters: getMonacoTriggerCharacters(),
  async provideCompletionItems(model, position) {
    const response = await getMonacoCompletions(model, position, monaco);
    return response;
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

const InlinePolicy = ({ arn = "", policies = [], setIsLoaderActive }) => {
  const [activeIndex, setActiveIndex] = useState([]);
  const [panels, setPanels] = useState([]);
  const [newPolicy, setNewPolicy] = useState(
    JSON.parse(templateOptions[0].value)
  );
  const [newPolicyName, setNewPolicyName] = useState("");
  const [isNewPolicy, setIsNewPolicy] = useState(false);
  const [adminAutoApprove, setAdminAutoApprove] = useState(false);
  const [justification, setJustification] = useState("");
  const [justificationError, setJustificationError] = useState("");
  const [loading, setLoading] = useState(true);
  const [event, setEvent] = useState(null);
  const [isSuccess, setIsSuccess] = useState(false);
  const [message, setMessage] = useState("");
  const [requestId, setRequestId] = useState("");
  const inputNewRef = useRef(null);
  const [openJustification, setOpenJustification] = useState(false);
  const [openResultMessage, setOpenResultMessage] = useState(false);

  const handleJustificationUpdate = (e) => {
    setJustification(e.target.value);
  };

  const ResultModal = () => {
    return (
      <Modal
        basic
        onClose={() => setOpenResultMessage(false)}
        onOpen={() => setOpenResultMessage(true)}
        open={openResultMessage}
        size="small"
      >
        <Modal.Content>{generateStatusMessage()}</Modal.Content>
      </Modal>
    );
  };

  const JustificationErrorMessage = () => {
    if (justificationError) {
      return (
        <Message negative>
          <Message.Header>Oops! There was a problem.</Message.Header>
          <p>{justificationError}</p>
        </Message>
      );
    }
    return null;
  };

  const JustificationModal = (
    <Modal
      onClose={() => setOpenJustification(false)}
      onOpen={() => setOpenJustification(true)}
      open={openJustification}
    >
      <Modal.Header>Please enter in your justification</Modal.Header>
      <Modal.Content>
        <Form>
          <TextArea
            placeholder="Tell us why you need this change"
            onChange={handleJustificationUpdate}
            style={{ width: "fluid" }}
            defaultValue={justification}
          />
        </Form>
        {JustificationErrorMessage()}
      </Modal.Content>
      <Modal.Actions>
        <Button
          content="Submit"
          labelPosition="left"
          icon="arrow right"
          onClick={() => {
            setOpenJustification(false);
            handleSubmitRequestToBackend(event);
          }}
          positive
        />
        <Button
          content="Cancel"
          onClick={() => setOpenJustification(false)}
          icon="cancel"
          negative
        ></Button>
      </Modal.Actions>
    </Modal>
  );
  const handlePolicyAdminSave = (e) => {
    setAdminAutoApprove(true);
    setEvent(e);
    setOpenJustification(true);
  };

  const handlePolicySubmit = (e) => {
    setAdminAutoApprove(false);
    setEvent(e);
    setOpenJustification(true);
  };

  const handleChangeNewPolicyName = (e) => {
    setNewPolicyName(e.target.value);
    console.log(newPolicyName);
  };

  const handleDelete = (e) => {
    console.log(e);
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
      this.onLintError(
        markers.map(
          (marker) =>
            `Lint error on line ${marker.startLineNumber} columns ${marker.startColumn}-${marker.endColumn}: ${marker.message}`
        )
      );
    });
  };

  const handleSubmitRequestToBackend = useCallback(
    async (e) => {
      if (!justification) {
        setJustificationError("Justification cannot be empty");
        setOpenJustification(true);
        return;
      }
      setJustificationError("");
      const requestV2 = {
        justification,
        admin_auto_approve: adminAutoApprove,
        changes: {
          changes: [
            {
              principal_arn: arn,
              change_type: "inline_policy",
              policy_name: newPolicyName,
              action: "attach",
              policy: {
                policy_document: newPolicy,
              },
            },
          ],
        },
      };

      setLoading(true);
      const response = await sendRequestCommon(requestV2, "/api/v2/request");

      if (response) {
        const { request_created, request_id, request_url } = response;
        if (request_created === true) {
          setLoading(false);
          setIsSuccess(true);
          setRequestId(request_id);
          if (adminAutoApprove) {
            setMessage(
              "Successfully created and applied request: [" +
                request_id +
                "](" +
                request_url +
                ")."
            );
          } else {
            setMessage(
              "Successfully created request: [" +
                request_id +
                "](" +
                request_url +
                ")."
            );
          }
          setOpenResultMessage(true);
          return;
        }
        setMessage(
          "Server reported an error with the request: " +
            JSON.stringify(response)
        );
        setIsSuccess(false);
        setOpenResultMessage(true);
      } else {
        setMessage("Failed to submit request: " + JSON.stringify(response));
        setIsSuccess(false);
        setOpenResultMessage(true);
      }
      setLoading(false);
    },
    [adminAutoApprove, arn, justification, newPolicy, newPolicyName]
  );

  // side effect for setting the loader
  // useEffect( () => {
  //   setIsLoaderActive(loading)
  // }, [loading, setIsLoaderActive])

  // side effect for rendering policies as Accordion
  useEffect(() => {
    const generatedPanels = policies.map((policy) => {
      return {
        key: policy.PolicyName,
        active: true,
        title: {
          content: policy.PolicyName,
        },
        content: {
          content: (
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
                  language="yaml"
                  theme="vs-dark"
                  value={JSON.stringify(policy.PolicyDocument, null, "\t")}
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
                  content="Delete"
                  onClick={handleDelete}
                />
              </Button.Group>
            </>
          ),
        },
      };
    });
    setPanels(generatedPanels);
  }, [policies, message]); //eslint-disable-line

  // side effect for adding a new policy
  useEffect(() => {
    if (!isNewPolicy) {
      setPanels([...panels.filter((panel) => panel.key !== "new_policy")]);
      return;
    }

    const panel = {
      key: "new_policy",
      active: true,
      title: "New Policy",
      content: {
        content: (
          <>
            <Segment color="green" attached="top">
              <Form>
                <Form.Group widths="equal">
                  <Ref innerRef={inputNewRef}>
                    <Form.Input
                      id="inputNew"
                      label="Policy Name"
                      placeholder="(Optional) Enter a Policy Name"
                      onChange={handleChangeNewPolicyName}
                    />
                  </Ref>
                  <Form.Dropdown
                    label="Template"
                    placeholder="Choose a template to add."
                    selection
                    onChange={onTemplateChange}
                    options={templateOptions}
                    defaultValue={templateOptions[0].value}
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
                language="yaml"
                theme="vs-dark"
                value={JSON.stringify(newPolicy, null, "\t")}
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
                onClick={removeInlinePolicy}
              />
            </Button.Group>
          </>
        ),
      },
    };

    // prepend the new policy editor
    setPanels([panel, ...panels.filter((panel) => panel.key !== "new_policy")]);
  }, [isNewPolicy, newPolicy]); //eslint-disable-line

  // TODO(heewonk): This changes the focus whenever we change text in the code editor, so I commented it out.
  // useEffect(() => {
  //   if (isNewPolicy && inputNewRef.current) {
  //     // Here, we are trying to focus the nested input element in the Form.Input component.
  //     const inputNewEl = inputNewRef.current.querySelector("#inputNew");
  //     inputNewEl.focus();
  //   }
  //   setActiveIndex([...Array(panels.length).keys()]);
  // }, [panels]); //eslint-disable-line

  const onTitleClick = (e, { index }) => {
    if (activeIndex.includes(index)) {
      setActiveIndex(activeIndex.filter((i) => i !== index));
    } else {
      setActiveIndex([...activeIndex, index]);
    }
  };

  const onEditChange = (e, d) => {
    try {
      setNewPolicy(JSON.parse(e));
    } catch {}
  };

  const onTemplateChange = (e, { value }) => {
    console.log(value);
    setNewPolicy(JSON.parse(value));
  };

  const addInlinePolicy = () => {
    setIsNewPolicy(true);
  };

  const removeInlinePolicy = () => {
    setIsNewPolicy(false);
  };

  const generateStatusMessage = () => {
    if (message && isSuccess) {
      return (
        <Message positive>
          <Message.Header>Success</Message.Header>
          <Message.Content>
            <ReactMarkdown linkTarget="_blank" source={message} />
          </Message.Content>
        </Message>
      );
    } else if (message && !isSuccess) {
      return (
        <Message negative>
          <Message.Header>Oops! There was a problem.</Message.Header>
          <Message.Content>
            <ReactMarkdown linkTarget="_blank" source={message} />
          </Message.Content>
        </Message>
      );
    }
  };

  return (
    <>
      <Segment
        basic
        clearing
        style={{
          padding: 0,
        }}
      >
        <Header as="h2" floated="left">
          Inline Policies
          <Header.Subheader>
            You can add/edit/delete inline policies for this role from here.
            Please create a new policy by using the buttons on the right.
          </Header.Subheader>
        </Header>
        <Button.Group floated="right">
          <Button disabled={false} onClick={addInlinePolicy} positive>
            Create New Inline Policy
          </Button>
          <Button.Or />
          <Button
            as={Link}
            disabled={false}
            to={`/ui/selfservice?arn=${encodeURIComponent(arn)}`}
            primary
          >
            Policy Wizard
          </Button>
        </Button.Group>
      </Segment>
      {JustificationModal}
      {ResultModal()}
      <Accordion
        activeIndex={activeIndex}
        exclusive={false}
        fluid
        onTitleClick={onTitleClick}
        panels={panels}
        styled
      />
    </>
  );
};

export default InlinePolicy;
