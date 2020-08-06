import React, { Component } from 'react';
import {
  Button, Grid, Header, Message, Table, Segment,
} from 'semantic-ui-react';

class ManagedPolicyChangeComponent extends Component {
  constructor(props) {
    super(props);
    this.state = {
      isLoading: false,
      messages: [],
      change: this.props.change,
      config: this.props.config,
    };
  }

  render() {
    const { change, config } = this.state;

    const action = change.action === 'detach'
      ? (
        <span style={{ color: 'red' }}>
          Detach
        </span>
      )
      : (
        <span style={{ color: 'green' }}>
          Attach
        </span>
      );

    const headerContent = (
      <Header size="large">
        Managed Policy Change - {action} {change.policy_name}
      </Header>
    );

    const applyChangesButton = config.can_approve_reject && change.status === 'not_applied'
      ? (
        <Grid.Column>
          <Button
            content="Apply Change"
            positive
            fluid
          />
        </Grid.Column>
      )
      : null;

    const changesAlreadyAppliedContent = (change.status === 'applied')
      ? (
        <Grid.Column>
          <Message info>
            <Message.Header>Change already applied</Message.Header>
            <p>This change has already been applied and cannot be modified.</p>
          </Message>
        </Grid.Column>
      )
      : null;

    const requestDetailsContent = (change)
      ? (
        <Table celled definition striped>
          <Table.Body>
            <Table.Row>
              <Table.Cell>
                Policy ARN
              </Table.Cell>
              <Table.Cell>
                {change.arn}
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>
                Action
              </Table.Cell>
              {change.action === 'detach'
                ? (
                  <Table.Cell negative>
                    Detach
                  </Table.Cell>
                )
                : (
                  <Table.Cell positive>
                    Attach
                  </Table.Cell>
                )}
            </Table.Row>
            <Table.Row>
              <Table.Cell>
                Role ARN
              </Table.Cell>
              <Table.Cell>
                {change.principal_arn}
              </Table.Cell>
            </Table.Row>
          </Table.Body>
        </Table>
      )
      : null;

    const policyChangeContent = (change)
      ? (
        <Grid fluid>
          <Grid.Row columns="equal">
            <Grid.Column>
              {requestDetailsContent}
            </Grid.Column>
          </Grid.Row>
          <Grid.Row columns="equal">
            {applyChangesButton}
            {changesAlreadyAppliedContent}
          </Grid.Row>
        </Grid>
      )
      : null;

    return (
      <Segment>
        {headerContent}
        {policyChangeContent}
      </Segment>
    );
  }
}

export default ManagedPolicyChangeComponent;
