import React, { useState } from 'react';
import {
    Accordion,
    Button,
    Grid,
    Label,
    Icon,
    Header,
    Message,
    Segment,
    Tab
} from 'semantic-ui-react';
import { useParams } from "react-router-dom";
import MonacoEditor from "react-monaco-editor";


const statement = {
    "Statement": [
        {
            "Action": [
                "s3:GetObjectTagging",
                "s3:GetObjectVersionAcl",
                "s3:ListBucket",
                "s3:GetObject",
                "s3:GetObjectVersionTagging",
                "s3:GetObjectAcl",
                "s3:ListBucketVersions",
                "s3:GetObjectVersion"
            ],
            "Effect": "Allow",
            "Resource": [
                "arn:aws:s3:::curtis-nflx-test/*",
                "arn:aws:s3:::curtis-nflx-test"
            ],
            "Sid": "cmccastrapel1600958681symv"
        },
        {
            "Action": [
                "sns:Publish",
                "sns:Subscribe",
                "sns:GetEndpointAttributes",
                "sns:ConfirmSubscription",
                "sns:Unsubscribe",
                "sns:GetTopicAttributes"
            ],
            "Effect": "Allow",
            "Resource": [
                "arn:aws:sns:us-east-1:313219654698:curtis-test-selfservice"
            ],
            "Sid": "cmccastrapel1600958681gopn"
        },
        {
            "Action": [
                "sqs:ReceiveMessage",
                "sqs:GetQueueAttributes",
                "sqs:SendMessage",
                "sqs:GetQueueUrl",
                "sqs:DeleteMessage"
            ],
            "Effect": "Allow",
            "Resource": [
                "arn:aws:sqs:us-east-1:313219654698:curtis-test-self-service"
            ],
            "Sid": "cmccastrapel1600958681jfiz"
        }
    ],
    "Version": "2012-10-17"
};

const inlinePolicies = [
    {
        name:"cm_ccastrapel_1600959047_ndig",
        statement,
    },
    {
        name: "cm_ccastrapel_1600985642_tvcg",
        statement,
    },
    {
        name: "cm_ccastrapel_1601479339_mdky",
        statement,
    },
];

const options = {
    selectOnLineNumbers: true,
    quickSuggestions: true,
    scrollbar: {
        alwaysConsumeMouseWheel: false,
    },
    scrollBeyondLastLine: false,
    automaticLayout: true,
};

const InlinePolicy = () => {
    const [activeIndex, setActiveIndex] = useState([0, 1, 2]);
    // const [config, setConfig] = useState(statement);

    const handleClick = (e, { index }) => {
        setActiveIndex([index]);
    };

    const onChange = (e, d) => {
        console.log(e, d);
    };

    const panels = inlinePolicies.map(policy => {
        return {
            key: policy.name,
            title: {
                content: (
                    policy.name
                )
            },
            content: {
                content: (
                    <>
                        <Message warning attached='top'>
                            <Icon name='warning' />
                            {`You are editing the policy ${policy.name}. There are lint errors.`}
                        </Message>
                        <Segment
                            attached
                            style={{
                                border: 0,
                                padding: 0
                            }}
                        >

                            <MonacoEditor
                                height="540px"
                                language="yaml"
                                theme="vs-dark"
                                value={JSON.stringify(policy.statement, null, "\t")}
                                onChange={onChange}
                                options={options}
                                textAlign="center"
                            />
                        </Segment>
                        <Button.Group attached="bottom">
                            <Button positive icon='save' content='Save' />
                            <Button.Or />
                            <Button primary icon='send' content='Submit' />
                            <Button.Or />
                            <Button negative icon='remove' content='Delete' />
                        </Button.Group>
                    </>
                )
            }
        }
    });

    // TODO, add expand all, close all features
    return (
        <>
            <Segment
                basic
                clearing
                style={{
                    marginBottom: 0
                }}
            >
                <Header as='h2' floated='left'>
                    Inline Policies
                    <Header.Subheader>
                        You can add/edit/delete inline policies for this role from here. Please create a new policy by using the buttons on the right.
                    </Header.Subheader>
                </Header>
                <Button.Group floated='right'>
                    <Button positive>Create New Inline Policy</Button>
                    <Button.Or />
                    <Button primary>Policy Wizard</Button>
                </Button.Group>
            </Segment>
            <Accordion
                defaultActiveIndex={activeIndex}
                exclusive={false}
                fluid
                onTitleClick={handleClick}
                panels={panels}
                styled
            />
        </>
    );
};

const IAMRolePolicy = () => {
    const { accountID, service, resource } = useParams();

    // TODO, show this role is managed by HoneyBee
    // TODO, tabs should be determined based on its service e.g. iam policy vs resource policy
    const tabs = [
        {
            menuItem: {
                key: 'inline_policy',
                content: (
                    <>
                        Inline Policy
                        <Label>{inlinePolicies.length}</Label>
                    </>
                )
            },
            render: () => {
                return (
                    <Tab.Pane>
                        <InlinePolicy />
                    </Tab.Pane>
                );
            }
        },
        {
            menuItem: 'Assume Role Policy',
            render: () => <Tab.Pane>Tab 2 Content</Tab.Pane>
        },
        {
            menuItem: 'Managed Policy',
            render: () => <Tab.Pane>Tab 3 Content</Tab.Pane>
        },
        {
            menuItem: 'Tags',
            render: () => <Tab.Pane>Tags</Tab.Pane>
        },
    ];

    return (
        <Tab panes={tabs}/>
    );
}


export default IAMRolePolicy;