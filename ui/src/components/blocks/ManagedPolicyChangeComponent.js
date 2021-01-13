import React, { useState, useEffect } from "react";
import {
  Button,
  Grid,
  Header,
  Message,
  Table,
  Segment,
  Loader,
  Dimmer,
} from "semantic-ui-react";
import { sendProposedPolicy } from "../../helpers/utils";

const ManagedPolicyChangeComponent = (props) => {
  const initialState = {
    isLoading: false,
    messages: [],
    buttonResponseMessage: [],
    change: props.change,
    config: props.config,
    requestID: props.requestID,
    requestReadOnly: props.requestReadOnly,
  };
  const [state, setState] = useState(initialState);

  const reloadDataFromBackend = props.reloadDataFromBackend;

  useEffect(() => {
    setState({
      ...state,
      isLoading: true,
    });
    const callAfterStateChange = () => {
      const { change, config, requestReadOnly } = props;
      setState({
        ...state,
        change,
        config,
        requestReadOnly,
        isLoading: false,
      });
    };
    callAfterStateChange();
  }, [props.change, props.requestReadOnly]);

  const onSubmitChange = () => {
    sendProposedPolicy(state, setState, reloadDataFromBackend, "apply_change");
  };

  const onCancelChange = () => {
    sendProposedPolicy(state, setState, reloadDataFromBackend, "cancel_change");
  };

  const {
    change,
    config,
    requestReadOnly,
    isLoading,
    buttonResponseMessage,
  } = state;

  const action =
    change.action === "detach" ? (
      <span style={{ color: "red" }}>Detach</span>
    ) : (
      <span style={{ color: "green" }}>Attach</span>
    );

  const headerContent = (
    <Header size="large">
      Managed Policy Change - {action} {change.policy_name}
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
          onClick={() => onSubmitChange()}
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
          onClick={() => onCancelChange()}
        />
      </Grid.Column>
    ) : null;

  const viewOnlyInfo =
    requestReadOnly && change.status === "not_applied" ? (
      <Grid.Column>
        <Message info>
          <Message.Header>View only</Message.Header>
          <p>This change is view only and can no longer be modified.</p>
        </Message>
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

  const requestDetailsContent = change ? (
    <Table celled definition striped>
      <Table.Body>
        <Table.Row>
          <Table.Cell>Policy ARN</Table.Cell>
          <Table.Cell>{change.arn}</Table.Cell>
        </Table.Row>
        <Table.Row>
          <Table.Cell>Action</Table.Cell>
          {change.action === "detach" ? (
            <Table.Cell negative>Detach</Table.Cell>
          ) : (
            <Table.Cell positive>Attach</Table.Cell>
          )}
        </Table.Row>
        <Table.Row>
          <Table.Cell>Role ARN</Table.Cell>
          <Table.Cell>{change.principal_arn}</Table.Cell>
        </Table.Row>
      </Table.Body>
    </Table>
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

  const policyChangeContent = change ? (
    <Grid fluid>
      <Grid.Row columns="equal">
        <Grid.Column>{requestDetailsContent}</Grid.Column>
      </Grid.Row>
      <Grid.Row columns="equal">
        <Grid.Column>{responseMessagesToShow}</Grid.Column>
      </Grid.Row>
      <Grid.Row columns="equal">
        {applyChangesButton}
        {cancelChangesButton}
        {viewOnlyInfo}
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
      {policyChangeContent}
    </Segment>
  );
};

export default ManagedPolicyChangeComponent;
