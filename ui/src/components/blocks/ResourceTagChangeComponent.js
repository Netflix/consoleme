import React from "react";
import {
  Button,
  Grid,
  Header,
  Message,
  Table,
  Segment,
} from "semantic-ui-react";
import { sendProposedPolicy } from "../../helpers/utils";

const ResourceTagChangeComponent = (props) => {
  const change = props.change;

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
        <Button content="Apply Change" positive fluid />
      </Grid.Column>
    ) : null;

  const cancelChangesButton =
    props.config.can_approve_reject &&
    change.status === "not_applied" &&
    !props.requestReadOnly ? (
      <Grid.Column>
        <Button content="Cancel Change" negative fluid />
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

  const changesAlreadyAppliedContent =
    change.status === "applied" ? (
      <Grid.Column>
        <Message info>
          <Message.Header>Change already applied</Message.Header>
          <p>This change has already been applied and cannot be modified.</p>
        </Message>
      </Grid.Column>
    ) : null;

  const originalTagKey = change.original_key ? (
    <Table.Row>
      <Table.Cell>
        Previous Tag Key Name (Approving will rename the tag)
      </Table.Cell>
      <Table.Cell>{change.original_key}</Table.Cell>
    </Table.Row>
  ) : null;

  const originalTagValue = change.original_value ? (
    <Table.Row>
      <Table.Cell>
        Previous Tag Value (Approving will change the value)
      </Table.Cell>
      <Table.Cell>{change.original_value}</Table.Cell>
    </Table.Row>
  ) : null;

  const requestDetailsContent = change ? (
    <Table celled definition striped>
      <Table.Body>
        {originalTagKey}
        <Table.Row>
          <Table.Cell>Desired Tag Key</Table.Cell>
          <Table.Cell>{change.key}</Table.Cell>
        </Table.Row>
        {originalTagValue}
        change.value ? (
        <Table.Row>
          <Table.Cell>Desired Tag Value</Table.Cell>
          <Table.Cell>{change.value}</Table.Cell>
        </Table.Row>{" "}
        ) : null;
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
          <Table.Cell>Role ARN</Table.Cell>
          <Table.Cell>{change.principal_arn}</Table.Cell>
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
        {applyChangesButton}
        {cancelChangesButton}
        {viewOnlyInfo}
        {changesAlreadyAppliedContent}
      </Grid.Row>
    </Grid>
  ) : null;

  return (
    <Segment>
      {headerContent}
      {policyChangeContent}
    </Segment>
  );
};

export default ResourceTagChangeComponent;
