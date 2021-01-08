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

const AssumeRolePolicyChangeComponent = (props) => {
  // const { change, config, requestReadOnly, requestID } = props;

  const oldPolicyDoc =
    props.change.old_policy && props.change.old_policy.policy_document
      ? props.change.old_policy.policy_document
      : {};
  const newPolicyDoc =
    props.change.policy.policy_document && props.change.policy.policy_document
      ? props.change.policy.policy_document
      : {};
  const new_Statement = sortAndStringifyNestedJSONObject(newPolicyDoc);

  const initialState = {
    newStatement: new_Statement,
    lastSavedStatement: new_Statement,
    isError: false,
    messages: [],
    buttonResponseMessage: [],
    oldStatement: sortAndStringifyNestedJSONObject(oldPolicyDoc),
    change: props.change,
    config: props.config,
    requestReadOnly: props.requestReadOnly,
    requestID: props.requestID,
    isLoading: false,
  };

  const [state, setState] = useState(initialState);

  const updatePolicyDocument = props.updatePolicyDocument;
  const reloadDataFromBackend = props.reloadDataFromBackend;

  useEffect(() => {
    setState({
      ...state,
      isLoading: true,
    });
    const cb = () => {
      const { change, config, requestReadOnly } = props;
      const oldPolicyDoc =
        change.old_policy && change.old_policy.policy_document
          ? change.old_policy.policy_document
          : {};

      const newPolicyDoc =
        change.policy.policy_document && change.policy.policy_document
          ? change.policy.policy_document
          : {};
      const newStatement = sortAndStringifyNestedJSONObject(newPolicyDoc);
      setState({
        ...state,
        newStatement,
        lastSavedStatement: newStatement,
        oldStatement: sortAndStringifyNestedJSONObject(oldPolicyDoc),
        change,
        config,
        requestReadOnly,
        isLoading: false,
      });
    };
    cb();
  }, [props.change, props.requestReadOnly]);

  const onLintError = (lintErrors) => {
    if (lintErrors.length > 0) {
      setState({
        ...state,
        messages: lintErrors,
        isError: true,
      });
    } else {
      setState({
        ...state,
        messages: [],
        isError: false,
      });
    }
  };

  const onValueChange = (newValue) => {
    const { change } = state;
    setState({
      ...state,
      newStatement: newValue,
      buttonResponseMessage: [],
    });
    updatePolicyDocument(change.id, newValue);
  };

  const onSubmitChange = () => {
    sendProposedPolicy(state, setState, reloadDataFromBackend, "apply_change");
  };

  const {
    oldStatement,
    newStatement,
    change,
    config,
    isError,
    messages,
    requestReadOnly,
    lastSavedStatement,
    isLoading,
    buttonResponseMessage,
  } = state;

  const headerContent = <Header size="large">Assume Role Policy Change</Header>;

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
          content="Update Proposed Policy"
          positive
          fluid
          disabled={isError || noChangesDetected}
          onClick={() =>
            sendProposedPolicy(
              state,
              setState,
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
              state,
              setState,
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
            onLintError={() => onLintError()}
            onValueChange={() => onValueChange()}
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

export default AssumeRolePolicyChangeComponent;
