import React, { useState } from "react";
import {
  Button,
  Dimmer,
  Form,
  Loader,
  Message,
  Modal,
  TextArea,
} from "semantic-ui-react";
import ReactMarkdown from "react-markdown";
import { usePolicyContext } from "./hooks/PolicyProvider";

const StatusMessage = ({ message, isSuccess }) => {
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
  } else {
    return null;
  }
};

export const JustificationModal = ({ handleSubmit }) => {
  const {
    adminAutoApprove = false,
    context = "inline_policy",
    isSuccess = false,
    resource = {},
    togglePolicyModal = false,
    setTogglePolicyModal,
    isPolicyEditorLoading,
    setIsPolicyEditorLoading,
    setIsSuccess,
  } = usePolicyContext();

  const [message, setMessage] = useState("");
  const [justification, setJustification] = useState("");

  const handleJustificationUpdate = (e) => {
    setJustification(e.target.value);
  };

  // TODO, there are too many state updates happening here. try do more in the reducer.
  const handleJustificationSubmit = async () => {
    if (!justification) {
      setMessage("No empty justification is allowed.");
      setIsSuccess(false);
      return;
    }
    setIsPolicyEditorLoading(true);

    const { message, request_created } = await handleSubmit({
      arn: resource.arn,
      adminAutoApprove,
      context,
      justification,
    });

    setMessage(message);
    setIsPolicyEditorLoading(false);
    setIsSuccess(request_created);
    setJustification("");
  };

  const handleOk = () => {
    setMessage("");
    setIsSuccess(false);
    setTogglePolicyModal(false);
  };

  const handleCancel = () => {
    setMessage("");
    setIsSuccess(false);
    setTogglePolicyModal(false);
  };

  return (
      <Modal
          onClose={() => setTogglePolicyModal(false)}
          onOpen={() => setTogglePolicyModal(true)}
          open={togglePolicyModal}
          closeOnDimmerClick={false}
      >
        <Modal.Header>Please enter in your justification</Modal.Header>
        <Modal.Content>
          <Dimmer.Dimmable dimmed={isPolicyEditorLoading}>
            <StatusMessage isSuccess={isSuccess} message={message} />
            {!isSuccess && (
                <Form>
                  <TextArea
                      placeholder="Tell us why you need this change"
                      onChange={handleJustificationUpdate}
                      style={{ width: "fluid" }}
                      defaultValue={justification}
                  />
                </Form>
            )}

            <Dimmer active={isPolicyEditorLoading} inverted>
              <Loader />
            </Dimmer>
          </Dimmer.Dimmable>
        </Modal.Content>
        <Modal.Actions>
          {isSuccess ? (
              <Button
                  content="Done"
                  labelPosition="left"
                  icon="arrow right"
                  onClick={handleOk}
                  positive
                  disabled={isPolicyEditorLoading}
              />
          ) : (
              <>
                <Button
                    content="Submit"
                    labelPosition="left"
                    icon="arrow right"
                    onClick={handleJustificationSubmit}
                    positive
                    disabled={isPolicyEditorLoading}
                />
                <Button
                    content="Cancel"
                    onClick={handleCancel}
                    icon="cancel"
                    negative
                    disabled={isPolicyEditorLoading}
                />
              </>
          )}
        </Modal.Actions>
      </Modal>
  );
};

export const DeleteResourceModel = () => {
  const { toggleDeleteRole = false, resource = {}, setToggleDeleteRole } = usePolicyContext();

  return (
      <Modal
          onClose={() => setToggleDeleteRole(false)}
          onOpen={() => setToggleDeleteRole(true)}
          open={toggleDeleteRole}
      >
        <Modal.Header>Deleting the role {resource.name}</Modal.Header>
        <Modal.Content image>
          <Modal.Description>
            <p>Are you sure to delete this role?</p>
          </Modal.Description>
        </Modal.Content>
        <Modal.Actions>
          <Button
              content="Delete"
              labelPosition="left"
              icon="remove"
              onClick={() => setToggleDeleteRole(false)}
              negative
          />
          <Button onClick={() => setToggleDeleteRole(false)}>Cancel</Button>
        </Modal.Actions>
      </Modal>
  );
};
