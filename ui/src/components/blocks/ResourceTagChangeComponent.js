import React, { useState } from "react";
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
import { useAuth } from "../../auth/AuthProviderDefault";

const ResourceTagChangeComponent = (props) => {
  const change = props.change;
  const [isLoading, setIsLoading] = useState(false);
  const [buttonResponseMessage, setButtonResponseMessage] = useState([]);
  const { sendProposedPolicyWithHooks } = useAuth();

  const getTagActionSpan = () => {
    if (change.tag_action === "create") {
      return <span style={{ color: "green" }}>Create</span>;
    }
    if (change.tag_action === "update") {
      return <span style={{ color: "green" }}>Update</span>;
    }
    if (change.tag_action === "delete") {
      return <span style={{ color: "red" }}>Delete</span>;
    }
  };
  const action = getTagActionSpan(change);

  const handleTaggingApprove = async () => {
    await sendProposedPolicyWithHooks(
      "apply_change",
      change,
      null,
      props.requestID,
      setIsLoading,
      setButtonResponseMessage,
      props.reloadDataFromBackend
    );
  };

  const handleTaggingCancel = async () => {
    await sendProposedPolicyWithHooks(
      "cancel_change",
      change,
      null,
      props.requestID,
      setIsLoading,
      setButtonResponseMessage,
      props.reloadDataFromBackend
    );
  };

  const headerContent = (
    <Header size="large">
      Tag Change - {action} {change.key}
    </Header>
  );

  const applyChangesButton =
    props.config.can_approve_reject &&
    change.status === "not_applied" &&
    !props.requestReadOnly ? (
      <Grid.Column>
        <Button
          content="Apply Change"
          onClick={handleTaggingApprove}
          positive
          fluid
        />
      </Grid.Column>
    ) : null;

  const cancelChangesButton =
    props.config.can_approve_reject &&
    change.status === "not_applied" &&
    !props.requestReadOnly ? (
      <Grid.Column>
        <Button
          content="Cancel Change"
          onClick={handleTaggingCancel}
          negative
          fluid
        />
      </Grid.Column>
    ) : null;

  const viewOnlyInfo =
    props.requestReadOnly && change.status === "not_applied" ? (
      <Grid.Column>
        <Message info>
          <Message.Header>View only</Message.Header>
          <p>This change is view only and can no longer be modified.</p>
        </Message>
      </Grid.Column>
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
        <Message info>
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

  const originalTagKey =
    change.original_key && change.original_key !== change.key ? (
      <Table.Row>
        <Table.Cell>
          Previous Tag Key Name (Approving will rename the tag)
        </Table.Cell>
        <Table.Cell>{change.original_key}</Table.Cell>
      </Table.Row>
    ) : null;

  const desiredTagKey = change.key ? (
    <Table.Row>
      <Table.Cell>Key</Table.Cell>
      <Table.Cell positive>{change.key}</Table.Cell>
    </Table.Row>
  ) : null;

  const originalTagValue =
    change.value &&
    change.original_value &&
    change.original_value !== change.value ? (
      <Table.Row>
        <Table.Cell>
          Previous Tag Value (Approving will change the value)
        </Table.Cell>
        <Table.Cell>{change.original_value}</Table.Cell>
      </Table.Row>
    ) : null;

  const desiredTagValue = change.value ? (
    <Table.Row>
      <Table.Cell>Value</Table.Cell>
      <Table.Cell positive>{change.value}</Table.Cell>
    </Table.Row>
  ) : null;

  const requestDetailsContent = change ? (
    <Table celled definition striped>
      <Table.Body>
        {originalTagKey}
        {desiredTagKey}
        {originalTagValue}
        {desiredTagValue}
        <Table.Row>
          <Table.Cell>Action</Table.Cell>
          {change.tag_action === "create" ? (
            <Table.Cell positive>Create</Table.Cell>
          ) : null}
          {change.tag_action === "update" ? (
            <Table.Cell positive>Update</Table.Cell>
          ) : null}
          {change.tag_action === "delete" ? (
            <Table.Cell negative>Delete</Table.Cell>
          ) : null}
        </Table.Row>
        <Table.Row>
          <Table.Cell>ARN</Table.Cell>
          <Table.Cell>{change.principal.principal_arn}</Table.Cell>
        </Table.Row>
      </Table.Body>
    </Table>
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

export default ResourceTagChangeComponent;
