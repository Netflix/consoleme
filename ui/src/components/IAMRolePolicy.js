import React, { useEffect, useState } from 'react';
import {
    Accordion,
    Button,
    Dropdown,
    Form,
    Label,
    List,
    Icon,
    Header,
    Message,
    Segment,
    Tab,
    Table
} from 'semantic-ui-react';
import MonacoEditor from "react-monaco-editor";
import { Link } from "react-router-dom";


const editorOptions = {
    selectOnLineNumbers: true,
    quickSuggestions: true,
    scrollbar: {
        alwaysConsumeMouseWheel: false,
    },
    scrollBeyondLastLine: false,
    automaticLayout: true,
};

const templateOptions = [
    {
        key: "default",
        value: JSON.stringify({
            "Statement":[
                {
                    "Action":[
                        ""
                    ],
                    "Effect":"Allow",
                    "Resource": [
                        ""
                    ]
                }
            ],
            "Version":"2012-10-17"
        }),
        text: "Default Template",
    },
    {
        key: "s3_write_access",
        value: JSON.stringify({
            "Statement": [
                {
                    "Action": [
                        "s3:ListBucket",
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::BUCKET_NAME",
                        "arn:aws:s3:::BUCKET_NAME/OPTIONAL_PREFIX/*"
                    ],
                    "Sid": "s3readwrite"
                }
            ]
        }),
        text: "S3 Write Access",
    },
];

const InlinePolicy = ({ arn = "", policies = [] }) => {
    const [activeIndex, setActiveIndex] = useState([]);
    const [panels, setPanels] = useState([]);
    const [newPolicy, setNewPolicy] = useState("");
    const [isNewPolicy, setIsNewPolicy] = useState(false);

    // side effect for rendering policies as Accordion
    useEffect(() => {
        setActiveIndex([...Array(policies.length).keys()]);
        const panels = policies.map(policy => {
            return {
                key: policy.PolicyName,
                title: {
                    content: (
                        policy.PolicyName
                    )
                },
                content: {
                    content: (
                        <>
                            <Message warning attached='top'>
                                <Icon name='warning' />
                                {`You are editing the policy ${policy.PolicyName}.`}
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
                                    value={JSON.stringify(policy.PolicyDocument, null, "\t")}
                                    onChange={onEditChange}
                                    options={editorOptions}
                                    textAlign="center"
                                />
                            </Segment>
                            <Button.Group attached="bottom">
                                <Button
                                    positive
                                    icon='save'
                                    content='Save'
                                />
                                <Button.Or />
                                <Button
                                    primary
                                    icon='send'
                                    content='Submit'
                                />
                                <Button.Or />
                                <Button
                                    negative
                                    icon='remove'
                                    content='Delete'
                                />
                            </Button.Group>
                        </>
                    )
                }
            }
        });
        setPanels(panels);
    }, [policies]);

    // side effect for adding a new policy
    useEffect(() => {
        if (!isNewPolicy) {
            return;
        }

        const panel = {
            key: "new_policy",
            title: "New Policy",
            content: {
                content: (
                    <>
                        <Segment
                            attached="top"
                        >
                            <Form>
                                <Form.Group widths='equal'>
                                    <Form.Input
                                        label='Policy Name'
                                        placeholder='Enter a Policy Name'
                                    />
                                    <Form.Dropdown
                                        label="Template"
                                        placeholder='Choose a template to add.'
                                        selection
                                        onChange={onTemplateChange}
                                        options={templateOptions}
                                    />
                                </Form.Group>
                            </Form>
                        </Segment>
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
                                value={JSON.stringify(newPolicy, null, "\t")}
                                onChange={onEditChange}
                                options={editorOptions}
                                textAlign="center"
                            />
                        </Segment>
                        <Button.Group attached="bottom">
                            <Button
                                positive
                                icon='save'
                                content='Save'
                            />
                            <Button.Or />
                            <Button
                                primary
                                icon='send'
                                content='Submit'
                            />
                            <Button.Or />
                            <Button
                                negative
                                icon='remove'
                                content='Cancel'
                            />
                        </Button.Group>
                    </>
                )
            }
        };

        // prepend the new policy editor
        setPanels([panel, ...panels.filter(panel => panel.key !== 'new_policy')]);
    }, [isNewPolicy, newPolicy]);

    const onTitleClick = (e, { index }) => {
        if (activeIndex.includes(index)) {
            setActiveIndex(activeIndex.filter(i => i !== index));
        } else {
            setActiveIndex([...activeIndex, index]);
        }
    };

    const onEditChange = (e, d) => {
        console.log(e, d);
    };

    const onTemplateChange = (e, { value }) => {
        setNewPolicy(JSON.parse(value));
    };

    const addInlinePolicy = () => {
        setIsNewPolicy(true);
    };

    const policyWizardLink = `/ui/selfservice?arn=${encodeURIComponent(arn)}`;

    // TODO, add expand all, close all features
    return (
        <>
            <Segment
                basic
                clearing
                style={{
                    padding: 0
                }}
            >
                <Header as='h2' floated='left'>
                    Inline Policies
                    <Header.Subheader>
                        You can add/edit/delete inline policies for this role from here. Please create a new policy by using the buttons on the right.
                    </Header.Subheader>
                </Header>
                <Button.Group floated='right'>
                    <Button
                        disabled={false}
                        onClick={addInlinePolicy}
                        positive
                    >
                        Create New Inline Policy
                    </Button>
                    <Button.Or />
                    <Button
                        as={Link}
                        disabled={false}
                        to={policyWizardLink}
                        primary
                    >
                        Policy Wizard
                    </Button>
                </Button.Group>
            </Segment>
            <Accordion
                activeIndex={activeIndex}
                exclusive={false}
                fluid
                onTitleClick={onTitleClick}
                panels={panels}
                styled
            />
        </>
    );
};

const AssumeRolePolicy = ({ policies = ""}) => {
    const onEditChange = (e, d) => {
        console.log(e, d);
    };

    return (
        <>
            <Header as='h2'>
                Assume Role Policy Document
                <Header.Subheader>
                    You can add/edit/delete assume role policy for this role from here.
                </Header.Subheader>
            </Header>
            <Message warning attached='top'>
                <Icon name='warning' />
                Make sure the roles that assume this role are carefully reviewed and have sts:assumerole permission.
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
                    value={JSON.stringify(policies, null, "\t")}
                    onChange={onEditChange}
                    options={editorOptions}
                    textAlign="center"
                />
            </Segment>
            <Button.Group attached="bottom">
                <Button
                    positive
                    icon='save'
                    content='Save'
                />
                <Button.Or />
                <Button
                    primary
                    icon='send'
                    content='Submit'
                />
                <Button.Or />
                <Button
                    negative
                    icon='remove'
                    content='Delete'
                />
            </Button.Group>
        </>
    );
};

const ManagedPolicy = ({ policies = []}) => {
    // TODO, retrieve available managed policies to attach
    const managedPolicyOptions = [
        {
            key: "arn:aws:iam::609753154238:policy/ApiProtect",
            value: "arn:aws:iam::609753154238:policy/ApiProtect",
            text: "arn:aws:iam::609753154238:policy/ApiProtect",
        },
    ];

    return (
        <>
            <Header as='h2'>
                Managed Policies
            </Header>
            <Form>
                <Form.Field>
                    <label>
                        Select a managed policy from the dropdown that you wish to add to this role.
                    </label>
                    <Dropdown
                        placeholder='Choose a managed policy to add to this role.'
                        fluid
                        selection
                        options={managedPolicyOptions}
                    />
                </Form.Field>
            </Form>
            <Header as='h3' attached="top" content="Attached Policies"/>
            <Segment attached="bottom">
                <List divided size="medium" relaxed='very' verticalAlign='middle'>
                    {
                        policies.map(policy => {
                            return (
                                <List.Item key={policy.PolicyName}>
                                    <List.Content floated='right' >
                                        <Button negative size="small">
                                            <Icon name="remove" />
                                            Remove
                                        </Button>
                                    </List.Content>
                                    <List.Content >
                                        <List.Header>
                                            {policy.PolicyName}
                                        </List.Header>
                                        <List.Description as='a'>
                                            {policy.PolicyArn}
                                        </List.Description>
                                    </List.Content>
                                </List.Item>
                            )
                        })
                    }
                </List>
            </Segment>
        </>
    );
};

const Tags = ({ tags = [] }) => {
    // TODO, add expand all, close all features
    return (
        <>
            <Segment
                basic
                clearing
                style={{
                    padding: 0
                }}
            >
                <Header as='h2' floated='left'>
                    Tags
                    <Header.Subheader>
                        You can add/edit/delete tags for this role from here.
                    </Header.Subheader>
                </Header>
                <Button.Group floated='right'>
                    <Button positive>Create New Tag</Button>
                </Button.Group>
            </Segment>
            <Form>
                {
                    tags.map(tag => {
                        return (
                            <Form.Group key={tag.Key} inline>
                                <Form.Input label='Key' placeholder='Key' value={tag.Key} readOnly />
                                <Form.Input label='Value' placeholder='Value' value={tag.Value} />
                                <Form.Button negative icon='remove' content='Delete Tag' />
                            </Form.Group>
                        );
                    })
                }
                <Form.Button primary icon='save' content='Save' />
            </Form>
        </>
    );
};

const Issues = ({ cloudtrail, s3 }) => {
    return (
        <>
            <Header as="h2">
                <Header.Content>
                    Recent Permission Errors (Click here to see logs)
                    <Header.Subheader>
                        This section shows the permission errors discovered for this role in the last 24 hours. This data originated from CloudTrail.
                    </Header.Subheader>
                </Header.Content>
            </Header>
            <Table celled>
                <Table.Header>
                    <Table.Row>
                        <Table.HeaderCell>Error Call</Table.HeaderCell>
                        <Table.HeaderCell>Count</Table.HeaderCell>
                    </Table.Row>
                </Table.Header>
                <Table.Body>
                    <Table.Row negative>
                        <Table.Cell>lambda:GetPolicy20150331v2</Table.Cell>
                        <Table.Cell>48</Table.Cell>
                    </Table.Row>
                </Table.Body>
            </Table>
            <Header as="h2">
                Recent S3 Errors (Click here to query for recent S3 errors)
                <Header.Subheader>
                    This section shows the permission errors discovered for this role in the last 24 hours. This data originated from CloudTrail.
                </Header.Subheader>
            </Header>
            <Table celled>
                <Table.Header>
                    <Table.Row>
                        <Table.HeaderCell>Error Call</Table.HeaderCell>
                        <Table.HeaderCell>Count</Table.HeaderCell>
                        <Table.HeaderCell>Bucket Name</Table.HeaderCell>
                        <Table.HeaderCell>Bucket Prefix</Table.HeaderCell>
                        <Table.HeaderCell>Error Status</Table.HeaderCell>
                        <Table.HeaderCell>Error Code</Table.HeaderCell>
                    </Table.Row>
                </Table.Header>
                <Table.Body>
                    <Table.Row negative>
                        <Table.Cell>s3:PutObject</Table.Cell>
                        <Table.Cell>14</Table.Cell>
                        <Table.Cell>nflx-awsconfig-bunkerprod-sa-east-1</Table.Cell>
                        <Table.Cell>nflx-awsconfig-bunkerprod-sa-east-1/AWSLogs/388300705741/Config</Table.Cell>
                        <Table.Cell>403</Table.Cell>
                        <Table.Cell>AccessDenied</Table.Cell>
                    </Table.Row>
                </Table.Body>
            </Table>
        </>
    );
};

const IAMRolePolicy = ({ resource }) => {
    const {
        arn = "",
        assume_role_policy_document = {},
        cloudtrail_details = {},
        inline_policies = [],
        managed_policies = [],
        s3_details = {},
        tags = [],
    } = resource;

    const tabs = [
        {
            menuItem: {
                key: 'inline_policy',
                content: (
                    <>
                        Inline Policy
                        <Label>{inline_policies.length}</Label>
                    </>
                )
            },
            render: () => {
                return (
                    <Tab.Pane>
                        <InlinePolicy
                            arn={arn}
                            policies={inline_policies}
                        />
                    </Tab.Pane>
                );
            }
        },
        {
            menuItem: 'Assume Role Policy',
            render: () => {
                return (
                    <Tab.Pane>
                        <AssumeRolePolicy
                            policies={assume_role_policy_document}
                        />
                    </Tab.Pane>
                );
            }
        },
        {
            menuItem: 'Managed Policy',
            render: () => {
                return (
                    <Tab.Pane>
                        <ManagedPolicy
                            policies={managed_policies}
                        />
                    </Tab.Pane>
                );
            }
        },
        {
            menuItem: 'Tags',
            render: () => {
                return (
                    <Tab.Pane>
                        <Tags
                            tags={tags}
                        />
                    </Tab.Pane>
                );
            }
        },
        {
            menuItem: {
                key: 'issues',
                content: (() => {
                    const cloudtrail_details_errors = cloudtrail_details && cloudtrail_details.errors
                    const s3_details_errors = s3_details && s3_details.errors

                    if (cloudtrail_details_errors && s3_details_errors) {
                        return (
                            <>
                                Issues
                                <Label color="red">
                                    {cloudtrail_details_errors.cloudtrail_errors.length + s3_details_errors.s3_errors.length}
                                </Label>
                            </>
                        );
                    } else {
                        return "Issues";
                    }
                })()
            },
            render: () => {
                return (
                    <Tab.Pane>
                        <Issues
                            cloudtrail={cloudtrail_details}
                            s3={s3_details}
                        />
                    </Tab.Pane>
                );
            }
        },
    ];

    return (
        <Tab panes={tabs}/>
    );
}


export default IAMRolePolicy;