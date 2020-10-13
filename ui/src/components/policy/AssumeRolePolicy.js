import React from 'react';
import {
    Button,
    Icon,
    Header,
    Message,
    Segment,
} from 'semantic-ui-react';
import MonacoEditor from "react-monaco-editor";


const editorOptions = {
    selectOnLineNumbers: true,
    quickSuggestions: true,
    scrollbar: {
        alwaysConsumeMouseWheel: false,
    },
    scrollBeyondLastLine: false,
    automaticLayout: true,
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

export default AssumeRolePolicy;
