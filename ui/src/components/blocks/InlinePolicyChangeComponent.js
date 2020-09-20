import React, { Component } from "react";
import {
  Button,
  Divider,
  Grid,
  Header,
  Message,
  Segment,
} from "semantic-ui-react";
import MonacoDiffComponent from "./MonacoDiffComponent";

class InlinePolicyChangeComponent extends Component {
  constructor(props) {
    super(props);
    const { change, config, requestReadOnly } = props;
    const oldPolicyDoc =
      change.old_policy && change.old_policy.policy_document
        ? change.old_policy.policy_document
        : {};
    const allOldKeys = [];
    JSON.stringify(oldPolicyDoc, (key, value) => {
      allOldKeys.push(key);
      return value;
    });

    const newPolicyDoc =
      change.policy.policy_document && change.policy.policy_document
        ? change.policy.policy_document
        : {};
    const allnewKeys = [];
    JSON.stringify(newPolicyDoc, (key, value) => {
      allnewKeys.push(key);
      return value;
    });

    this.state = {
      newStatement: JSON.stringify(newPolicyDoc, allnewKeys.sort(), 4),
      isError: false,
      isLoading: false,
      messages: [],
      oldStatement: JSON.stringify(oldPolicyDoc, allOldKeys.sort(), 4),
      change,
      config,
      requestReadOnly,
    };

    this.onLintError = this.onLintError.bind(this);
    this.onValueChange = this.onValueChange.bind(this);
  }

  onLintError(lintErrors) {
    if (lintErrors.length > 0) {
      this.setState({
        messages: lintErrors,
        isError: true,
      });
    } else {
      this.setState({
        messages: [],
        isError: false,
      });
    }
  }

  onValueChange(newValue) {
    this.setState({
      newStatement: newValue,
    });
  }

  render() {
    const {
      oldStatement,
      newStatement,
      change,
      config,
      isError,
      messages,
      requestReadOnly,
    } = this.state;

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
          <Button content="Apply Change" positive fluid disabled={isError} />
        </Grid.Column>
      ) : null;

    const updateChangesButton =
      config.can_update_cancel &&
      change.status === "not_applied" &&
      !requestReadOnly ? (
        <Grid.Column>
          <Button content="Update Change" positive fluid disabled={isError} />
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

    const changesAlreadyAppliedContent =
      change.status === "applied" ? (
        <Grid.Column>
          <Message info>
            <Message.Header>Change already applied</Message.Header>
            <p>This change has already been applied and cannot be modified.</p>
          </Message>
        </Grid.Column>
      ) : null;

    const changeReadOnly = requestReadOnly || change.status === "applied";

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
              onLintError={this.onLintError}
              onValueChange={this.onValueChange}
            />
          </Grid.Column>
        </Grid.Row>
        <Grid.Row columns="equal">
          <Grid.Column>{messagesToShow}</Grid.Column>
        </Grid.Row>
        <Grid.Row columns="equal">
          {applyChangesButton}
          {updateChangesButton}
          {readOnlyInfo}
          {changesAlreadyAppliedContent}
        </Grid.Row>
      </Grid>
    ) : null;

    return (
      <Segment>
        {headerContent}
        <Divider hidden />
        {policyChangeContent}
      </Segment>
    );
  }
}

export default InlinePolicyChangeComponent;
