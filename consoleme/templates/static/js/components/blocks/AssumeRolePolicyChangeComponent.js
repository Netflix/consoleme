import _ from "lodash";
import React, {Component} from "react";
import {Button, Dimmer, Divider, Form, Grid, Header, Label, Loader, Message, Tab, Table, TextArea, Segment} from "semantic-ui-react";
import { diff as DiffEditor } from "react-ace";
import {generate_id, getCompletions, sendRequestCommon} from "../../helpers/utils";

import ace from "brace";
import "brace/ext/language_tools";
import "brace/theme/monokai";
import "brace/mode/json";

let langTools = ace.acequire("ace/ext/language_tools");
langTools.setCompleters([{getCompletions: getCompletions}])

class AssumeRolePolicyChangeComponent extends Component {
    constructor(props) {
        super(props);
        const old_policy_doc = this.props.change.old_policy && this.props.change.old_policy.policy_document || {}
        let allOldKeys = [];
        JSON.stringify( old_policy_doc, function( key, value ){ allOldKeys.push( key ); return value; } )
        const new_policy_doc = this.props.change.policy.policy_document && this.props.change.policy.policy_document || {}
        let allnewKeys = [];
        JSON.stringify( new_policy_doc, function( key, value ){ allnewKeys.push( key ); return value; } )

        this.state = {
            activeIndex: 0,
            new_statement: JSON.stringify(new_policy_doc, allnewKeys.sort(), 4),
            isError: false,
            isLoading: false,
            messages: [],
            old_statement: JSON.stringify(old_policy_doc, allOldKeys.sort(), 4),
            change: this.props.change,
            config: this.props.config
        };
        this.assumeRolePolicyDiffRef = React.createRef();
    }

    handleJSONEditorChange(value) {
        // const editor = this.assumeRolePolicyDiffRef.current.editor;
        // if (editor.completer && editor.completer.popup) {
        //     let popup = editor.completer.popup;
        //     popup.container.style.width = "600px";
        //     popup.resize();
        // }
        this.setState({
            new_statement: value[1]
        })
    }

    buildAceDiff(old_statement, new_statement, name) {
        const {config} = this.state;
        return (
            <DiffEditor
                mode="json"
                theme="monokai"
                width="100%"
                showPrintMargin={false}
                ref={this.assumeRolePolicyDiffRef}
                tabSize={4}
                value={[old_statement, new_statement]}
                name={name}
                onChange={this.handleJSONEditorChange.bind(this)}
                editorProps={{
                    $blockScrolling: true,
                }}
                setOptions={{
                    "enableBasicAutocompletion": true,
                    "enableLiveAutocompletion": true,
                    "wrapBehavioursEnabled": true,
                    "wrap": true,
                    "useSoftTabs": true,
                    "readOnly": !(config.can_approve_reject || request_config.can_update_cancel)
                }}
            />
        );
    }

    render(){
        const {old_statement, new_statement, change, config} = this.state;

        const headerContent =
            (
                    <Header size={'large'}>
                        Assume Role Policy Change - {change.policy_name}
                    </Header>
            )
        const aceDiff = this.buildAceDiff(old_statement, new_statement, "ace_diff_" + change.policy_name);
        const applyChangesButton = config.can_approve_reject && change.status === "not_applied" ?
            (
                <Grid.Column>
                            <Button
                                content="Apply Change"
                                positive
                                fluid
                            />
                </Grid.Column>
            )
            : null;

        const updateChangesButton = config.can_update_cancel && change.status === "not_applied" ?
            (
                <Grid.Column>
                            <Button
                                content="Update Change"
                                positive
                                fluid
                            />
                </Grid.Column>
            )
            : null;

        const changesAlreadyAppliedContent = (change.status === "applied") ?
            (
                <Grid.Column>
                    <Message info>
                        <Message.Header>Change already applied</Message.Header>
                        <p>This change has already been applied and cannot be modified.</p>
                    </Message>
                </Grid.Column>
            )
            :
            null;

        const policyChangeContent = (change) ?
            (
                <Grid fluid>
                    <Grid.Row columns={'equal'}>
                        <Grid.Column>
                            <Header
                                size={'medium'}
                                content={'Current Policy'}
                                subheader={'This is a read-only view of the current policy in AWS.'}
                            />
                        </Grid.Column>
                        <Grid.Column>
                            <Header
                                size={'medium'}
                                content={'Proposed Policy'}
                                subheader={'This is an editable view of the proposed policy. An approver can modify the proposed policy before approving and applying it.'}
                            />
                        </Grid.Column>
                    </Grid.Row>
                    <Grid.Row>
                        <Grid.Column>
                            {aceDiff}
                        </Grid.Column>
                    </Grid.Row>
                    <Grid.Row columns={'equal'}>
                        {updateChangesButton}
                        {applyChangesButton}
                        {changesAlreadyAppliedContent}
                    </Grid.Row>
                </Grid>
            )
            :
            null;


        return (
            <Segment>
                {headerContent}
                {policyChangeContent}
            </Segment>
        )
        ;

    }

}

export default AssumeRolePolicyChangeComponent