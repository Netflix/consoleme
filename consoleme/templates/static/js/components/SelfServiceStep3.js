import _ from 'lodash';
import React, {Component} from 'react';

import {
    Button,
    Divider,
    Feed,
    Header,
    Icon,
    Label,
    Message,
    Tab,
} from 'semantic-ui-react';

import AceEditor from "react-ace";
import "ace-builds/src-noconflict/mode-json";
import "ace-builds/src-noconflict/theme-monokai";

// TODO, remove this.
import policyExample from './policy_example';


class SelfServiceStep3 extends Component {
    state = {};

    componentDidMount() {
        // TODO(curtis), use the role and permissions from props and send them for policy
        // generation and review evaluation.
        const {role, permissions} = this.props;
    }

    handleRequestSubmit() {
        const {role, permissions} = this.props;
        // TODO(curtis), send a role and a list of permissions or JSON dump
        console.log("Send Request to Backend: ", role, permissions);
    }

    render() {
        const {role, permissions} = this.props;

        const ReviewComponent = (
            <Feed>
                <Feed.Event>
                    <Feed.Label>
                        <Icon name='close' color="pink" />
                    </Feed.Label>
                    <Feed.Content>
                        <Feed.Date>Denied</Feed.Date>
                        <Feed.Summary>
                            Target S3 bucket exists in the cross account. You need to assume a role in the cross account using your <a>{role.roleArn}</a> role.
                        </Feed.Summary>
                        <Feed.Extra text>
                            Please reach out to #security-help for further requests with this details.
                        </Feed.Extra>
                        <Feed.Meta>
                            <Label size="tiny">
                                <Icon name="tag" />
                                S3
                            </Label>
                            <Label size="tiny" content="Cross Account" />
                        </Feed.Meta>
                    </Feed.Content>
                </Feed.Event>
                <Feed.Event>
                    <Feed.Label>
                        <Icon name='close' color="pink" />
                    </Feed.Label>
                    <Feed.Content>
                        <Feed.Date>Denied</Feed.Date>
                        <Feed.Summary>
                            The bucket policy is required to allow your role to access the S3 bucket exists in the cross account.
                        </Feed.Summary>
                        <Feed.Extra text>
                            Please reach out to #security-help for further requests with this details.
                        </Feed.Extra>
                        <Feed.Meta>
                            <Label size="tiny" content="S3" />
                            <Label size="tiny" content="Bucket Policy" />
                        </Feed.Meta>
                    </Feed.Content>
                </Feed.Event>
                <Feed.Event>
                    <Feed.Label>
                        <Icon name='checkmark' color="teal"/>
                    </Feed.Label>
                    <Feed.Content>
                        <Feed.Date>Approved</Feed.Date>
                        <Feed.Summary>
                            Your role <a>{role.roleArn}</a> already has all the desired permissions for <b>GET</b>, <b>PUT</b> and <b>LIST</b> the bucket.
                        </Feed.Summary>
                    </Feed.Content>
                </Feed.Event>
                <Feed.Event>
                    <Feed.Label>
                        <Icon name='checkmark' color="teal"/>
                    </Feed.Label>
                    <Feed.Content>
                        <Feed.Date>Approved</Feed.Date>
                        <Feed.Summary>
                            There is no Object ACL configured in the S3 bucket
                        </Feed.Summary>
                        <Feed.Meta>
                            <Label size="tiny" content="S3" />
                            <Label size="tiny" content="Object ACL" />
                        </Feed.Meta>
                    </Feed.Content>
                </Feed.Event>
                <Feed.Event>
                    <Feed.Label>
                        <Icon name='checkmark' color="teal"/>
                    </Feed.Label>
                    <Feed.Content>
                        <Feed.Date>
                            Approved
                        </Feed.Date>
                        <Feed.Summary>
                            This S3 bucket is shared bucket and has no ownership tag exist.
                        </Feed.Summary>
                        <Feed.Meta>
                            <Label size="tiny" content="Ownership" />
                        </Feed.Meta>
                    </Feed.Content>
                </Feed.Event>
            </Feed>
        );

        const panes = [
            {
                menuItem: 'Review',
                render: () => (
                    <Tab.Pane>
                        <Header>
                            Please Review Permissions
                            <Header.Subheader>
                                You can customize your permissions in JSON Editor for further customization.
                            </Header.Subheader>
                        </Header>
                        <p>Your new permissions will be applied to the role <a href="#">{role.roleArn}</a>.</p>
                        <Divider />
                        <Message negative>
                            <Message.Header>
                                There are items to review.
                            </Message.Header>
                            <p>Please address issues in <b>Denied</b> status before the submission.</p>
                        </Message>
                        {ReviewComponent}
                        <Button
                            content="Submit"
                            fluid
                            onClick={this.handleRequestSubmit.bind(this)}
                            primary
                        />
                    </Tab.Pane>
                ),
            },
            {
                menuItem: 'JSON Editor',
                render: () => (
                    <Tab.Pane>
                        <Header>
                            Edit your permissions in JSON format.
                            <Header.Subheader>
                                Please refer to IAM JSON reference manual for further details.
                            </Header.Subheader>
                        </Header>
                        <br />
                        <AceEditor
                            mode="json"
                            theme="monokai"
                            width="100%"
                            onChange={(newValue) => {
                                console.log(newValue);
                            }}
                            value={policyExample}
                            name="json_editor"
                            editorProps={{ $blockScrolling: true }}
                        />
                    </Tab.Pane>
                ),
            }
        ];

        return (
            <React.Fragment>
                <Tab panes={panes} />
                <br />
            </React.Fragment>
        );
    }
}

export default SelfServiceStep3;
