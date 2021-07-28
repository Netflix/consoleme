import React, { Component } from "react";
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
import { sortAndStringifyNestedJSONObject } from "../../helpers/utils";

class InlinePolicyChangeComponent extends Component {
  constructor(props) {
    super(props);
    const { change, config, requestReadOnly, requestID } = props;
    const oldPolicyDoc =
      change.old_policy && change.old_policy.policy_document
        ? change.old_policy.policy_document
        : {};

    const newPolicyDoc =
      change.policy.policy_document && change.policy.policy_document
        ? change.policy.policy_document
        : {};
    const newStatement = sortAndStringifyNestedJSONObject(newPolicyDoc);
    this.state = {
      newStatement,
      lastSavedStatement: newStatement,
      isError: false,
      messages: [],
      buttonResponseMessage: [],
      oldStatement: sortAndStringifyNestedJSONObject(oldPolicyDoc),
      change,
      config,
      requestReadOnly,
      requestID,
      isLoading: false,
    };

    this.onLintError = this.onLintError.bind(this);
    this.onValueChange = this.onValueChange.bind(this);
    this.onSubmitChange = this.onSubmitChange.bind(this);
    this.updatePolicyDocument = props.updatePolicyDocument;
    this.reloadDataFromBackend = props.reloadDataFromBackend;
  }

  componentDidUpdate(prevProps) {
    if (
      JSON.stringify(prevProps.change) !== JSON.stringify(this.props.change) ||
      prevProps.requestReadOnly !== this.props.requestReadOnly
    ) {
      this.setState(
        {
          isLoading: true,
        },
        () => {
          const { change, config, requestReadOnly } = this.props;
          const oldPolicyDoc =
            change.old_policy && change.old_policy.policy_document
              ? change.old_policy.policy_document
              : {};

          const newPolicyDoc =
            change.policy.policy_document && change.policy.policy_document
              ? change.policy.policy_document
              : {};
          const newStatement = sortAndStringifyNestedJSONObject(newPolicyDoc);
          this.setState({
            newStatement,
            lastSavedStatement: newStatement,
            oldStatement: sortAndStringifyNestedJSONObject(oldPolicyDoc),
            change,
            config,
            requestReadOnly,
            isLoading: false,
          });
        }
      );
    }
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
    const { change } = this.state;
    this.setState({
      newStatement: newValue,
      buttonResponseMessage: [],
    });
    this.updatePolicyDocument(change.id, newValue);
  }

  onSubmitChange() {
    const applyChange = this.props.sendProposedPolicy.bind(
      this,
      "apply_change"
    );
    applyChange();
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
      lastSavedStatement,
      isLoading,
      buttonResponseMessage,
    } = this.state;

    const newPolicy = change.new ? (
      <span style={{ color: "red" }}>- New Policy</span>
    ) : null;

    const headerContent = () => {
      if (change.change_type === "inline_policy") {
        return (
          <Header size="large">
            Inline Policy Change - {change.policy_name} {newPolicy}
          </Header>
        );
      } else {
        return <Header size="large">Managed Policy Change</Header>;
      }
    };

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
            onClick={this.onSubmitChange}
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
            onClick={this.props.sendProposedPolicy.bind(this, "update_change")}
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
            onClick={this.props.sendProposedPolicy.bind(this, "cancel_change")}
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
              onLintError={this.onLintError}
              onValueChange={this.onValueChange}
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
        {headerContent()}
        <Divider hidden />
        {policyChangeContent}
      </Segment>
    );
  }
}

export default InlinePolicyChangeComponent;
