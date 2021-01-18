import React, { useState, useEffect } from "react";
import {
  Button,
  Dimmer,
  Divider,
  Grid,
  Header,
  Loader,
  Message,
  Segment,
} from "semantic-ui-react";
import MonacoDiffComponent from "./MonacoDiffComponent";
import {
  sendProposedPolicy,
  sortAndStringifyNestedJSONObject,
} from "../../helpers/utils";

const InlinePolicyChangeComponent = (props) => {
  const oldPolicyDoc =
    props.change.old_policy && props.change.old_policy.policy_document
      ? props.change.old_policy.policy_document
      : {};

  const newPolicyDoc =
    props.change.policy.policy_document && props.change.policy.policy_document
      ? props.change.policy.policy_document
      : {};
  const new_Statement = sortAndStringifyNestedJSONObject(newPolicyDoc);

  const [newStatement, setNewStatement] = useState(new_Statement);
  const [lastSavedStatement, setLastSavedStatement] = useState(new_Statement);
  const [isError, setIsError] = useState(false);
  const [messages, setMessages] = useState([]);
  const [buttonResponseMessage, setButtonResponseMessage] = useState([]);
  const [oldStatement, setOldStatement] = useState(
    sortAndStringifyNestedJSONObject(oldPolicyDoc)
  );
  const [change, setChange] = useState(props.change);
  const [config, setConfig] = useState(props.config);
  const [requestReadOnly, setRequestReadOnly] = useState(props.requestReadOnly);
  // eslint-disable-next-line
  const [requestID, setRequestID] = useState(props.requestID);
  const [isLoading, setIsLoading] = useState(false);

  const { updatePolicyDocument, reloadDataFromBackend } = props;

  useEffect(() => {
    setIsLoading(true);
    const cb = () => {
      const oldPolicyDoc =
        change.old_policy && change.old_policy.policy_document
          ? change.old_policy.policy_document
          : {};

      const newPolicyDoc =
        change.policy.policy_document && change.policy.policy_document
          ? change.policy.policy_document
          : {};
      const new_Statement = sortAndStringifyNestedJSONObject(newPolicyDoc);
      setNewStatement(new_Statement);
      setLastSavedStatement(new_Statement);
      setOldStatement(sortAndStringifyNestedJSONObject(oldPolicyDoc));
      setChange(props.change);
      setConfig(props.config);
      setRequestReadOnly(props.requestReadOnly);
      setIsLoading(false);
    };
    cb();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [change, requestReadOnly]);

  const onLintError = (lintErrors) => {
    if (lintErrors) {
      if (lintErrors.length > 0) {
        setMessages(lintErrors);
        setIsError(true);
      }
    } else {
      setMessages([]);
      setIsError(false);
    }
  };

  const onValueChange = (newValue) => {
    setNewStatement(newValue);
    setButtonResponseMessage([]);
    updatePolicyDocument(change.id, newValue);
  };

  const onSubmitChange = () => {
    sendProposedPolicy(
      change,
      newStatement,
      requestID,
      setIsLoading,
      setButtonResponseMessage,
      reloadDataFromBackend,
      "apply_change"
    );
  };

  const newPolicy = change.new ? (
    <span style={{ color: "red" }}>- New Policy</span>
  ) : null;

  const headerContent = (
    <Header size="large">
      Inline Policy Change - {change.policy_name} {newPolicy}
    </Header>
  );

  const applyChangesButton =
    config.can_approve_reject &&
    change.status === "not_applied" &&
    !requestReadOnly ? (
      <Grid.Column>
        <Button
          content="Apply Change"
          positive
          fluid
          disabled={isError}
          onClick={() => onSubmitChange()}
        />
      </Grid.Column>
    ) : null;

  const noChangesDetected = lastSavedStatement === newStatement;

  const updateChangesButton =
    config.can_update_cancel &&
    change.status === "not_applied" &&
    !requestReadOnly ? (
      <Grid.Column>
        <Button
          content="Update Change"
          positive
          fluid
          disabled={isError || noChangesDetected}
          onClick={() =>
            sendProposedPolicy(
              change,
              newStatement,
              requestID,
              setIsLoading,
              setButtonResponseMessage,
              reloadDataFromBackend,
              "update_change"
            )
          }
        />
      </Grid.Column>
    ) : null;

  const cancelChangesButton =
    (config.can_approve_reject || config.can_update_cancel) &&
    change.status === "not_applied" &&
    !requestReadOnly ? (
      <Grid.Column>
        <Button
          content="Cancel Change"
          negative
          fluid
          disabled={isError}
          onClick={() =>
            sendProposedPolicy(
              change,
              newStatement,
              requestID,
              setIsLoading,
              setButtonResponseMessage,
              reloadDataFromBackend,
              "cancel_change"
            )
          }
        />
      </Grid.Column>
    ) : null;

  const readOnlyInfo =
    requestReadOnly && change.status === "not_applied" ? (
      <Grid.Column>
        <Message info>
          <Message.Header>View only</Message.Header>
          <p>This change is view only and can no longer be modified.</p>
        </Message>
      </Grid.Column>
    ) : null;

  const messagesToShow =
    messages.length > 0 ? (
      <Message negative>
        <Message.Header>There was a problem with your request</Message.Header>
        <Message.List>
          {messages.map((message) => (
            <Message.Item>{message}</Message.Item>
          ))}
        </Message.List>
      </Message>
    ) : null;

  const responseMessagesToShow =
    buttonResponseMessage.length > 0 ? (
      <Grid.Column>
        {buttonResponseMessage.map((message) =>
          message.status === "error" ? (
            <Message negative>
              <Message.Header>An error occurred</Message.Header>
              <Message.Content>{message.message}</Message.Content>
            </Message>
          ) : (
            <Message positive>
              <Message.Header>Success</Message.Header>
              <Message.Content>{message.message}</Message.Content>
            </Message>
          )
        )}
      </Grid.Column>
    ) : null;

  const changesAlreadyAppliedContent =
    change.status === "applied" ? (
      <Grid.Column>
        <Message positive>
          <Message.Header>Change already applied</Message.Header>
          <p>This change has already been applied and cannot be modified.</p>
        </Message>
      </Grid.Column>
    ) : null;

  const changesAlreadyCancelledContent =
    change.status === "cancelled" ? (
      <Grid.Column>
        <Message negative>
          <Message.Header>Change cancelled</Message.Header>
          <p>This change has been cancelled and cannot be modified.</p>
        </Message>
      </Grid.Column>
    ) : null;

  const changeReadOnly =
    requestReadOnly ||
    change.status === "applied" ||
    change.status === "cancelled";

  const policyChangeContent = change ? (
    <Grid fluid>
      <Grid.Row columns="equal">
        <Grid.Column>
          <Header
            size="medium"
            content="Current Policy"
            subheader="This is a read-only view of the current policy in AWS."
          />
        </Grid.Column>
        <Grid.Column>
          <Header
            size="medium"
            content="Proposed Policy"
            subheader="This is an editable view of the proposed policy.
              An approver can modify the proposed policy before approving and applying it."
          />
        </Grid.Column>
      </Grid.Row>
      <Grid.Row>
        <Grid.Column>
          <MonacoDiffComponent
            oldValue={oldStatement}
            newValue={newStatement}
            readOnly={
              (!config.can_update_cancel && !config.can_approve_reject) ||
              changeReadOnly
            }
            onLintError={onLintError}
            onValueChange={onValueChange}
          />
        </Grid.Column>
      </Grid.Row>
      <Grid.Row columns="equal">
        <Grid.Column>{messagesToShow}</Grid.Column>
      </Grid.Row>
      <Grid.Row columns="equal">
        <Grid.Column>{responseMessagesToShow}</Grid.Column>
      </Grid.Row>
      <Grid.Row columns="equal">
        {applyChangesButton}
        {updateChangesButton}
        {cancelChangesButton}
        {readOnlyInfo}
        {changesAlreadyAppliedContent}
        {changesAlreadyCancelledContent}
      </Grid.Row>
    </Grid>
  ) : null;

  return (
    <Segment>
      <Dimmer active={isLoading} inverted>
        <Loader />
      </Dimmer>
      {headerContent}
      <Divider hidden />
      {policyChangeContent}
    </Segment>
  );
};

export default InlinePolicyChangeComponent;
