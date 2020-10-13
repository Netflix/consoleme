import React, { useEffect, useState } from 'react';
import { Button, Header, Icon, Label, Message, Segment, Tab } from 'semantic-ui-react';
import MonacoEditor from "react-monaco-editor";

import Issues from "./Issues";
import Tags from "./Tags";

const editorOptions = {
    selectOnLineNumbers: true,
    quickSuggestions: true,
    scrollbar: {
        alwaysConsumeMouseWheel: false,
    },
    scrollBeyondLastLine: false,
    automaticLayout: true,
};

const onEditChange = (e, d) => {
    console.log(e, d);
};


const ResourcePolicy = ({ resource }) => {
    const {
        arn = "",
        cloudtrail_details = {},
        inline_policies = [],
        read_only = false,
        s3_errors = {},
        resource_details = {},
        tags = [],
    } = resource;

    const [policy, setPolicy] = useState("");

    useEffect(() => {
        setPolicy(resource_details.Policy);
    }, [resource_details]);

    const tabs = [
        {
            menuItem: {
                key: 'policy',
                content: "Resource Policy"
            },
            render: () => {
                return (
                    <Tab.Pane>
                        <>
                            <Header as='h2'>
                                Resource Policy
                                <Header.Subheader>
                                    You can add/edit/delete resource policy here.
                                </Header.Subheader>
                            </Header>
                            <Message warning attached='top'>
                                <Icon name='warning' />
                                Double check whether cross account access for this resource is necessary.
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
                                    value={JSON.stringify(policy, null, "\t")}
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
                    </Tab.Pane>
                );
            }
        },
        {
            menuItem: {
                key: 'tags',
                content: 'Tags',
            },
            render: () => {
                return (
                    <Tab.Pane>
                        <Tags
                            tags={resource_details.TagSet}
                        />
                    </Tab.Pane>
                );
            }
        },
        {
            menuItem: {
                key: 'issues',
                content: (() => {
                    return "Issues";
                })()
            },
            render: () => {
                return (
                    <Tab.Pane>
                        <Issues
                            s3={s3_errors}
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


export default ResourcePolicy;