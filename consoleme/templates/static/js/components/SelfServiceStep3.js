import _ from "lodash";
import React, {Component} from "react";
import {Button, Dimmer, Divider, Form, Header, Label, Loader, Message, Tab, Table, TextArea,} from "semantic-ui-react";
import {generate_id, getCompletions, sendRequestCommon} from "../helpers/utils";
import AceEditor from "react-ace";

import ace from "brace";
import "brace/ext/language_tools";
import "brace/theme/monokai";
import "brace/mode/json";

let langTools = ace.acequire("ace/ext/language_tools");
langTools.setCompleters([{getCompletions: getCompletions}])

class SelfServiceStep3 extends Component {
    constructor(props) {
        super(props);
        this.state = {
            activeIndex: 0,
            custom_statement: "",
            isError: false,
            isLoading: false,
            isSuccess: false,
            justification: "",
            messages: [],
            requestId: null,
            statement: ""
        };
        this.inlinePolicyEditorRef = React.createRef();
        this.handleJustificationChange = this.handleJustificationChange.bind(this);
        this.handleSubmit = this.handleSubmit.bind(this);
    }

    async componentDidMount() {
        const {role, permissions} = this.props;
        const payload = {
            "changes": [],
        };
        payload["changes"] = permissions.map(permission => {
            const change = {
                "principal_arn": role.arn,
                "generator_type": permission.service,
                "action_groups": permission.actions,
                "effect": "Allow",
                ...permission,
            };
            delete change["service"];
            delete change["actions"];
            return change;
        });

        const response = await sendRequestCommon(payload, "/api/v2/generate_changes");
        if (response.status != null && response.status === 400) {
            return this.setState({
                isError: true,
                messages: [response.message],
            });
        }

        if (response.length > 0) {
            const statement = JSON.stringify(response[0]["policy"]["policy_document"], null, 4);
            return this.setState({
                custom_statement: statement,
                isError: false,
                messages: [],
                statement,
            });
        } else {
            return this.setState({
                isError: true,
                messages: ["Unknown Exception raised. Please reach out for support"],
            });
        }
    }

    handleJSONEditorValidation(lintErrors) {
        const {activeIndex} = this.state;
        const messages = [];
        if (lintErrors.length > 0) {
            for (let i = 0; i < lintErrors.length; i++) {
                messages.push("Lint Error - Row: " + lintErrors[i]["row"] + ", Column: " + lintErrors[i]["column"] + ", Error: " + lintErrors[i]["text"]);
            }
            this.setState({
                isError: true,
                messages,
            });
        } else {
            if (activeIndex === 1) {
                this.setState({
                    isError: false,
                    messages: [],
                });
            }
        }
    }

    buildAceEditor(custom_statement) {
        return (
            <AceEditor
                mode="json"
                theme="monokai"
                width="100%"
                showPrintMargin={false}
                ref={this.inlinePolicyEditorRef}
                tabSize={4}
                onChange={this.handleJSONEditorChange.bind(this)}
                onValidate={this.handleJSONEditorValidation.bind(this)}
                value={custom_statement}
                name="json_editor"
                editorProps={{
                    $blockScrolling: true,
                }}
                setOptions={{
                    "enableBasicAutocompletion": true,
                    "enableLiveAutocompletion": true,
                    "wrapBehavioursEnabled": true,
                    "wrap": true,
                    "useSoftTabs": true,
                }}
            />
        );
    }

    buildPermissionsTable() {
        const {permissions, services} = this.props;
        const permissionRows = permissions.map(permission => {
            const serviceDetail = _.find(services, {"key": permission.service});
            return (
                <Table.Row>
                    <Table.Cell>
                        {serviceDetail.text}
                    </Table.Cell>
                    <Table.Cell collapsing textAlign='left'>
                        {
                            Object.keys(permission).map((key) => {
                                if (key === "actions" || key === "service") {
                                    return;
                                }
                                return (
                                    <Label as='a'>
                                        {key}
                                        <Label.Detail>
                                            {permission[key]}
                                        </Label.Detail>
                                    </Label>
                                )
                            })
                        }
                    </Table.Cell>
                    <Table.Cell>
                        {
                            permission.actions.map(action => {
                                const actionDetail = _.find(serviceDetail.actions, {"name": action});
                                return (
                                    <Label as="a" color="olive">
                                        {actionDetail.text}
                                    </Label>
                                );
                            })
                        }
                    </Table.Cell>
                </Table.Row>
            );
        });

        const permissionTable = (
            <Table celled striped selectable>
                <Table.Header>
                    <Table.HeaderCell>Service</Table.HeaderCell>
                    <Table.HeaderCell>Resource</Table.HeaderCell>
                    <Table.HeaderCell>Actions</Table.HeaderCell>
                </Table.Header>
                <Table.Body>
                    {permissionRows}
                </Table.Body>
            </Table>
        );

        return permissionTable;
    }

    handleSubmit() {
        const {role} = this.props;
        const {custom_statement, justification} = this.state;

        if (!justification) {
            return this.setState(state => ({
                messages: ["No Justification is Given"],
            }));
        }

        const {account_id, arn} = role;
        const policyName = generate_id();
        const policyType = "InlinePolicy";
        const request = {
            arn,
            account_id,
            justification,
            "data_list": [
                {
                    'type': policyType,
                    'name': policyName,
                    'value': custom_statement,
                    'is_new': true,
                },
            ],
        };

        this.setState({
            isLoading: true,
        }, async () => {
            const response = await sendRequestCommon(
                request,
                '/policies/submit_for_review',
            );

            const messages = [];
            if (response) {
                const {request_id, status} = response;
                if (status === "success") {
                    return this.setState({
                        isLoading: false,
                        isSuccess: true,
                        messages,
                        requestId: request_id,
                    });
                } else {
                    messages.push("Failed to create a request");
                }
            } else {
                messages.push("Failed to submit a request");
            }
            this.setState({
                isLoading: false,
                messages,
            });
        });
    }

    handleJustificationChange(e) {
        this.setState({
            justification: e.target.value,
        });
    }

    handleJSONEditorChange(custom_statement) {
        const editor = this.inlinePolicyEditorRef.current.editor;
        if (editor.completer && editor.completer.popup) {
            let popup = editor.completer.popup;
            popup.container.style.width = "600px";
            popup.resize();
        }
        this.setState({
            custom_statement,
        });
    }

    render() {
        const {role} = this.props;
        const {
            custom_statement,
            isError,
            isLoading,
            isSuccess,
            justification,
            messages,
            requestId,
            statement
        } = this.state;

        const active = custom_statement != statement;
        const messagesToShow = (messages.length > 0)
            ? (
                <Message negative>
                    <Message.Header>
                        We found some problems for this request.
                    </Message.Header>
                    <Message.List>
                        {
                            messages.map(message => {
                                return <Message.Item>{message}</Message.Item>;
                            })
                        }
                    </Message.List>
                </Message>
            )
            : null;

        const panes = [
            {
                menuItem: 'Review',
                render: () => {
                    return (
                        <Tab.Pane loading={isLoading}>
                            <Header>
                                Please Review Permissions
                                <Header.Subheader>
                                    You can customize your request using the JSON Editor for advanced permissions.
                                </Header.Subheader>
                            </Header>
                            <p>
                                Your new permissions will be attached to the role <a
                                href={`/policies/edit/${role.account_id}/iamrole/${role.name}`}
                                target="_blank">{role.arn}</a> with the
                                following statements:
                            </p>
                            <Dimmer.Dimmable dimmed={active}>
                                {this.buildPermissionsTable()}
                                <Dimmer active={active}>
                                    <Header as='h2' inverted>
                                        Your changes made from the JSON Editor will override these permissions.
                                    </Header>
                                </Dimmer>
                            </Dimmer.Dimmable>
                            <Divider/>
                            <Header>
                                Justification
                            </Header>
                            <Form>
                                <TextArea
                                    onChange={this.handleJustificationChange}
                                    placeholder={"Your Justification"}
                                    value={justification}
                                />
                            </Form>
                            <Divider/>
                            {messagesToShow}
                            <Button
                                content="Submit"
                                disabled={isError}
                                fluid
                                onClick={this.handleSubmit}
                                primary
                            />
                        </Tab.Pane>
                    );
                },
            },
            {
                menuItem: 'JSON Editor',
                render: () => {
                    const jsonEditor = this.buildAceEditor(custom_statement);
                    return (
                        <Tab.Pane loading={isLoading}>
                            <Header>
                                Edit your permissions in JSON format.
                            </Header>
                            <br/>
                            {jsonEditor}
                            <Divider/>
                            <Header>
                                Justification
                            </Header>
                            <Form>
                                <TextArea
                                    onChange={this.handleJustificationChange}
                                    placeholder={"Your Justification"}
                                    value={justification}
                                />
                            </Form>
                            <Divider/>
                            {messagesToShow}
                            <Button
                                content="Submit"
                                disabled={isError}
                                fluid
                                onClick={this.handleSubmit}
                                primary
                            />
                        </Tab.Pane>
                    );
                },
            }
        ];

        const tabContent = (isSuccess)
            ? (
                <Message positive>
                    <Message.Header>
                        Your request was successful.
                    </Message.Header>
                    You can check your request status from <a href={`/policies/request/${requestId}`}
                                                              target="_blank">here</a>.
                </Message>
            )
            : (
                <React.Fragment>
                    <Tab
                        onTabChange={(event, data) =>
                            this.setState({
                                activeIndex: data.activeIndex,
                            })
                        }
                        panes={panes}
                    />
                    <br/>
                </React.Fragment>
            );
        return tabContent;
    }
}

export default SelfServiceStep3;
