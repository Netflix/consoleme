import ReactDOM from 'react-dom';

import React, { Component } from 'react';
import {
  Button, Dimmer, Grid, Header, Icon, Image, Loader, Message, Segment, Table,
} from 'semantic-ui-react';
import CommentsFeedBlockComponent from './blocks/CommentsFeedBlockComponent';
import InlinePolicyChangeComponent from './blocks/InlinePolicyChangeComponent';
import ManagedPolicyChangeComponent from './blocks/ManagedPolicyChangeComponent';
import AssumeRolePolicyChangeComponent from './blocks/AssumeRolePolicyChangeComponent';

class PolicyRequestReview extends Component {
  constructor(props) {
    super(props);
    const { requestID } = props;
    this.state = {
      requestID,
      loading: false,
      extendedRequest: {},
      messages: [],
      isSubmitting: false,
      lastUpdated: null,
      requestConfig: {},
    };
  }

  async componentDidMount() {
    const { requestID } = this.state;
    this.setState({
      loading: true,
    }, () => {
      fetch(`/api/v2/requests/${requestID}`).then((resp) => {
        resp.text().then((responseString) => {
          const response = JSON.parse(responseString);
          if (response.status === 404 || response.status === 500) {
            this.setState({
              loading: false,
              messages: [response.message],
            });
          } else {
            this.setState({
              extendedRequest: JSON.parse(response.request),
              requestConfig: response.request_config,
              lastUpdated: response.last_updated,
              loading: false,
            });
          }
        });
      });
    });
  }

  render() {
    const {
      lastUpdated, extendedRequest, messages, isSubmitting, requestConfig, loading,
    } = this.state;
    const extendedInfo = (extendedRequest.requester_info
        && extendedRequest.requester_info.extended_info)
      ? (extendedRequest.requester_info.extended_info)
      : null;
    const messagesToShow = (messages.length > 0)
      ? (
        <Message negative>
          <Message.Header>
            There was a problem with your request
          </Message.Header>
          <Message.List>
            {
              messages.map((message) => <Message.Item>{message}</Message.Item>)
            }
          </Message.List>
        </Message>
      ) : null;
    console.log(extendedRequest);
    console.log(requestConfig);
    const requestDetails = (extendedRequest)
      ? (
        <Table celled definition striped>
          <Table.Body>
            <Table.Row>
              <Table.Cell>
                User
              </Table.Cell>
              <Table.Cell>
                {extendedInfo
                  ? (
                    <Header size="medium">
                      {(extendedInfo.name && `${extendedInfo.name.fullName} - `) || ''}
                      {extendedRequest.requester_info.details_url
                        ? (
                          <a
                            href={extendedRequest.requester_info.details_url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            {extendedRequest.requester_email}
                          </a>
                        )
                        : (
                          <span>
                            {extendedRequest.requester_email}
                          </span>
                        )}
                      {extendedInfo.thumbnailPhotoUrl
                        ? (<Image src={extendedInfo.thumbnailPhotoUrl} size="small" inline />)
                        : null}
                    </Header>
                  )
                  : (
                    <span>
                      {extendedRequest.requester_info && extendedRequest.requester_info.details_url
                        ? (
                          <a
                            href={extendedRequest.requester_info.details_url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            {extendedRequest.requester_email}
                          </a>
                        )
                        : (
                          <span>
                            {extendedRequest.requester_email}
                          </span>
                        )}
                    </span>
                  )}
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>Request Time</Table.Cell>
              <Table.Cell>{new Date(extendedRequest.timestamp).toLocaleString()}</Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>Title</Table.Cell>
              <Table.Cell>
                {extendedInfo
                  ? (
                    <p>
                      {(extendedInfo.customAttributes && extendedInfo.customAttributes.title) || ''}
                    </p>
                  )
                  : null}
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>Manager</Table.Cell>
              <Table.Cell>
                {extendedInfo
                  ? (
                    <p>
                      {(extendedInfo.customAttributes && `${extendedInfo.customAttributes.manager} - `) || ''}
                      {extendedInfo.relations && extendedInfo.relations.length > 0
                      && extendedInfo.relations[0].value
                        ? <a href={`mailto:${extendedInfo.relations[0].value}`}>{extendedInfo.relations[0].value}</a>
                        : null}
                    </p>
                  )
                  : null}
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>User Justification</Table.Cell>
              <Table.Cell>
                {extendedRequest.justification}
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>Status</Table.Cell>
              {extendedRequest.status === 'approved'
                ? (
                  <Table.Cell positive>
                    {extendedRequest.status}
                  </Table.Cell>
                )
                : (
                  <Table.Cell negative>
                    {extendedRequest.status}
                  </Table.Cell>
                )}
            </Table.Row>
            <Table.Row>
              <Table.Cell>Reviewer</Table.Cell>
              <Table.Cell>
                {extendedRequest.reviewer || ''}
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>Last Updated</Table.Cell>
              <Table.Cell>{new Date(lastUpdated * 1000).toLocaleString()}</Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>Cross-Account</Table.Cell>
              {extendedRequest.cross_account === true
                ? (
                  <Table.Cell negative>
                    <Icon name="attention" />
                    {' '}
                    True
                  </Table.Cell>
                )
                : (
                  <Table.Cell positive>
                    False
                  </Table.Cell>
                )}
            </Table.Row>
          </Table.Body>

        </Table>
      )
      : null;

    const commentsContent = extendedRequest.comments
      ? (
        <CommentsFeedBlockComponent
          comments={extendedRequest.comments}
        />
      )
      : null;

    const changesContent = extendedRequest.changes && extendedRequest.changes.changes
            && extendedRequest.changes.changes.length > 0
      ? (
        <>
          {extendedRequest.changes.changes.map((change) => {
            if (change.change_type === 'inline_policy') {
              return (
                <InlinePolicyChangeComponent
                  change={change}
                  config={requestConfig}
                />
              );
            } if (change.change_type === 'managed_policy') {
              return (
                <ManagedPolicyChangeComponent
                  change={change}
                  config={requestConfig}
                />
              );
            } if (change.change_type === 'assume_role_policy') {
              return (
                <AssumeRolePolicyChangeComponent
                  change={change}
                  config={requestConfig}
                />
              );
            }
            return null;
          })}
        </>
      )
      : null;

    const approveRequestButton = requestConfig.can_approve_reject
      ? (
        <Grid.Column>
          <Button
            content="Approve and Commit Changes"
            positive
            fluid
          />
        </Grid.Column>
      )
      : null;

    const rejectRequestButton = requestConfig.can_approve_reject
      ? (
        <Grid.Column>
          <Button
            content="Reject Request"
            negative
            fluid
          />
        </Grid.Column>
      )
      : null;

    const cancelRequestButton = requestConfig.can_update_cancel
      ? (
        <Grid.Column>
          <Button
            content="Cancel Request"
            negative
            fluid
          />
        </Grid.Column>
      )
      : null;

    const viewOnly = !(approveRequestButton || rejectRequestButton || cancelRequestButton);
    const requestButtons = !viewOnly
      ? (
        <Grid container>
          <Grid.Row columns="equal">
            {approveRequestButton}
            {rejectRequestButton}
            {cancelRequestButton}
          </Grid.Row>
        </Grid>
      )
      : null;

    const requestButtonsContent = (extendedRequest.status === 'pending')
      ? (
        requestButtons
      )
      : (
        <Message info fluid>
          <Message.Header>This request can no longer be modified</Message.Header>
          <p>
            This request can no longer be modified as the status is
            {extendedRequest.status}
          </p>
        </Message>
      );

    const pageContent = (messagesToShow === null)
      ? (
        <Segment>
          {requestDetails}
          {changesContent}
          {commentsContent}
          {requestButtonsContent}
        </Segment>
      )
      : messagesToShow;

    return (
      <>
        <Dimmer
          active={isSubmitting || loading}
          inverted
        >
          <Loader />
        </Dimmer>
        <Header size="huge">
          Request Review for:
          {' '}
          {extendedRequest.arn}
        </Header>
        {pageContent}
      </>
    );
  }
}

export function renderPolicyRequestsReview(requestID) {
  ReactDOM.render(
    <PolicyRequestReview
      requestID={requestID}
    />,
    document.getElementById('policy_request_review'),
  );
}

export default PolicyRequestReview;
