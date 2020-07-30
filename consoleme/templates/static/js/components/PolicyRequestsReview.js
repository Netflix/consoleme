import ReactDOM from "react-dom";

import React, {Component} from 'react';
import {Button, Dimmer, Grid, Header, Icon, Image, Loader, Message, Segment, Table} from "semantic-ui-react";
import CommentsFeedBlockComponent from "./blocks/CommentsFeedBlockComponent";
import InlinePolicyChangeComponent from "./blocks/InlinePolicyChangeComponent";
import ManagedPolicyChangeComponent from "./blocks/ManagedPolicyChangeComponent";
import AssumeRolePolicyChangeComponent from "./blocks/AssumeRolePolicyChangeComponent"
class PolicyRequestReview extends Component {

    constructor(props) {
        super(props);
        const {request_id} = props;
        this.state = {
            request_id,
            loading: false,
            extended_request: {},
            messages: [],
            isSubmitting: false,
            last_updated: null,
            request_config: {}
        };
    }

    async componentDidMount() {
        const {request_id} = this.state;
        this.setState({
            loading: true,
        },  () => {
            fetch(`/api/v2/requests/${request_id}`).then((resp) => {
                    resp.text().then((resp) => {
                        const response = JSON.parse(resp);
                        if (response.status === 404 || response.status === 500) {
                            this.setState({
                                loading: false,
                                messages: [response.message],
                            });
                        } else {
                            this.setState({
                                extended_request: JSON.parse(response.request),
                                request_config: response.request_config,
                                last_updated: response.last_updated
                            });
                        }
                    })
            });
        });


    }


    render() {
        const {last_updated, extended_request, messages, isSubmitting, request_config} = this.state;
        const extended_info = (extended_request.requester_info && extended_request.requester_info.extended_info) ?
            (extended_request.requester_info.extended_info)
            :
            null;
        const messagesToShow = (messages.length > 0)
            ? (
                <Message negative>
                    <Message.Header>
                        There was a problem with your request
                    </Message.Header>
                    <Message.List>
                        {
                            messages.map(message => {
                                return <Message.Item>{message}</Message.Item>;
                            })
                        }
                    </Message.List>
                </Message>
            ) : null;
        console.log(extended_request)
        console.log(request_config)
        const request_details = (extended_request) ?
            (
                  <Table celled definition striped>
                    <Table.Body>
                      <Table.Row>
                        <Table.Cell>
                          User
                        </Table.Cell>
                        <Table.Cell>
                            {extended_info ?
                                (
                                    <Header size={'medium'}>
                                        {extended_info.name && extended_info.name.fullName + " - " || ""}
                                        {extended_request.requester_info.details_url ?
                                            <a href={extended_request.requester_info.details_url}
                                               target={"_blank"}>{extended_request.requester_email}</a>
                                            :
                                            <span>
                                                {extended_request.requester_email}
                                            </span>
                                        }
                                    {extended_info.thumbnailPhotoUrl ?
                                        (<Image src={extended_info.thumbnailPhotoUrl} size={'small'} inline/>)
                                        :
                                        null
                                    }
                                    </Header>
                                )
                                :
                                <span>
                                    {extended_request.requester_info && extended_request.requester_info.details_url ?
                                        <a href={extended_request.requester_info.details_url}
                                           target={"_blank"}>{extended_request.requester_email}</a>
                                        :
                                        <span>
                                            {extended_request.requester_email}
                                        </span>
                                    }
                                </span>
                            }
                        </Table.Cell>
                      </Table.Row>
                      <Table.Row>
                        <Table.Cell>Request Time</Table.Cell>
                        <Table.Cell>{new Date(extended_request.timestamp).toLocaleString()}</Table.Cell>
                      </Table.Row>
                      <Table.Row>
                        <Table.Cell>Title</Table.Cell>
                        <Table.Cell>
                            {extended_info ?
                                <p>
                                    {extended_info.customAttributes && extended_info.customAttributes.title || ""}
                                </p>
                                :
                                null
                            }
                        </Table.Cell>
                      </Table.Row>
                      <Table.Row>
                        <Table.Cell>Manager</Table.Cell>
                        <Table.Cell>
                            {extended_info ?
                                <p>
                                    {extended_info.customAttributes && extended_info.customAttributes.manager + " - " || ""}
                                    {extended_info.relations && extended_info.relations.length > 0 && extended_info.relations[0].value ?
                                            <a href={"mailto:"+extended_info.relations[0].value}>{extended_info.relations[0].value}</a>
                                            :
                                            null
                                    }
                                </p>
                                :
                                null
                            }
                        </Table.Cell>
                      </Table.Row>
                      <Table.Row>
                        <Table.Cell>User Justification</Table.Cell>
                        <Table.Cell>
                            {extended_request.justification}
                        </Table.Cell>
                      </Table.Row>
                      <Table.Row>
                        <Table.Cell>Status</Table.Cell>
                          {extended_request.status === "approved" ?
                              (
                                  <Table.Cell positive>
                                      {extended_request.status}
                                  </Table.Cell>
                              ) :
                              (
                                  <Table.Cell negative>
                                      {extended_request.status}
                                  </Table.Cell>
                              )

                          }
                      </Table.Row>
                      <Table.Row>
                        <Table.Cell>Reviewer</Table.Cell>
                        <Table.Cell>
                            {extended_request.reviewer || ""}
                        </Table.Cell>
                      </Table.Row>
                      <Table.Row>
                        <Table.Cell>Last Updated</Table.Cell>
                        <Table.Cell>{new Date(last_updated * 1000).toLocaleString()}</Table.Cell>
                      </Table.Row>
                      <Table.Row>
                        <Table.Cell>Cross-Account</Table.Cell>
                          {extended_request.cross_account === true ?
                              (
                                  <Table.Cell negative>
                                      <Icon name='attention' /> True
                                  </Table.Cell>
                              ) :
                              (
                                  <Table.Cell positive>
                                      False
                                  </Table.Cell>
                              )

                          }
                      </Table.Row>
                    </Table.Body>

                  </Table>
            )
            :
            null;

        const commentsContent = extended_request.comments ?
                (
                    <CommentsFeedBlockComponent
                        comments={extended_request.comments}
                    />
                )
                : null;

        const changesContent = extended_request.changes && extended_request.changes.changes && extended_request.changes.changes.length > 0 ?
            (
                <React.Fragment>
                    {extended_request.changes.changes.map(function(change, i) {
                        if (change.change_type === "inline_policy") {
                            return <InlinePolicyChangeComponent
                                change={change}
                                config={request_config}
                            />
                        } else if(change.change_type === "managed_policy") {
                            return <ManagedPolicyChangeComponent
                                change={change}
                                config={request_config}
                                />
                        } else if(change.change_type === "assume_role_policy") {
                            return <AssumeRolePolicyChangeComponent
                                change={change}
                                config={request_config}
                                />
                        } else {
                            return null
                        }
                    })
                    }
                </React.Fragment>
            )
            :
            null;

        const approveRequestButton = request_config.can_approve_reject ?
            (
                <Grid.Column>
                            <Button
                                content="Approve and Commit Changes"
                                positive
                                fluid
                            />
                </Grid.Column>
            )
            : null;

        const rejectRequestButton = request_config.can_approve_reject ?
            (
                <Grid.Column>
                            <Button
                                content="Reject Request"
                                negative
                                fluid
                            />
                </Grid.Column>
            )
            : null;

        const cancelRequestButton = request_config.can_update_cancel ?
            (
                <Grid.Column>
                            <Button
                                content="Cancel Request"
                                negative
                                fluid
                            />
                </Grid.Column>
            )
            : null;

        const viewOnly = !(approveRequestButton || rejectRequestButton || cancelRequestButton)
        const requestButtons = !viewOnly ?
            (
                <Grid container>
                    <Grid.Row columns={'equal'}>
                        {approveRequestButton}
                        {rejectRequestButton}
                        {cancelRequestButton}
                    </Grid.Row>
                </Grid>
            )
            :
            null;

        const requestButtonsContent = (extended_request.status === "pending") ?
            (
                requestButtons
            )
            :
            (
                <Message info fluid>
                        <Message.Header>This request can no longer be modified</Message.Header>
                        <p>This request can no longer be modified as it's status is {extended_request.status}</p>
                </Message>
            )

        const pageContent = (messagesToShow === null) ?
            <Segment>
                {request_details}
                {changesContent}
                {commentsContent}
                {requestButtonsContent}
            </Segment>
            :
            messagesToShow;

        return <React.Fragment>
                <Dimmer
                    active={isSubmitting}
                    inverted
                >
                    <Loader />
                </Dimmer>
                <Header size='huge'>
                    Request Review for: {extended_request.arn}
                </Header>
                {pageContent}
            </React.Fragment>
    }
}

export function renderPolicyRequestsReview(request_id) {
    ReactDOM.render(
        <PolicyRequestReview
            request_id={request_id}
        />,
        document.getElementById("policy_request_review"),
    );
}

export default PolicyRequestReview;