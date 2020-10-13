import React, { useEffect, useRef, useState } from 'react';
import {
    Accordion,
    Button,
    Form,
    Icon,
    Header,
    Message,
    Ref,
    Segment,
} from 'semantic-ui-react';
import MonacoEditor from "react-monaco-editor";
import { Link } from "react-router-dom";

import { templateOptions } from "./policyTemplates";

const editorOptions = {
    selectOnLineNumbers: true,
    quickSuggestions: true,
    scrollbar: {
        alwaysConsumeMouseWheel: false,
    },
    scrollBeyondLastLine: false,
    automaticLayout: true,
};


const InlinePolicy = ({ arn = "", policies = [] }) => {
    const [activeIndex, setActiveIndex] = useState([]);
    const [panels, setPanels] = useState([]);
    const [newPolicy, setNewPolicy] = useState(JSON.parse(templateOptions[0].value));
    const [isNewPolicy, setIsNewPolicy] = useState(false);
    const inputNewRef = useRef(null);

    // side effect for rendering policies as Accordion
    useEffect(() => {
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
                                    <Ref innerRef={inputNewRef}>
                                        <Form.Input
                                            id="inputNew"
                                            label='Policy Name'
                                            placeholder='Enter a Policy Name'
                                        />
                                    </Ref>
                                    <Form.Dropdown
                                        label="Template"
                                        placeholder='Choose a template to add.'
                                        selection
                                        onChange={onTemplateChange}
                                        options={templateOptions}
                                        defaultValue={templateOptions[0].value}
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

    useEffect(() => {
        if (isNewPolicy) {
            // Here, we are trying to focus the nested input element in the Form.Input component.
            const inputNewEl = inputNewRef.current.querySelector("#inputNew");
            inputNewEl.focus();
        }
        setActiveIndex([...Array(panels.length).keys()]);
    }, [panels]);

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
        console.log(value);
        setNewPolicy(JSON.parse(value));
    };

    const addInlinePolicy = () => {
        setIsNewPolicy(true);
    };

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
                        to={`/ui/selfservice?arn=${encodeURIComponent(arn)}`}
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

export default InlinePolicy;
