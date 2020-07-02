import _ from 'lodash';
import React, {Component} from 'react';
import {Button, Dimmer, Divider, Form, Header, Label, Loader, Message, Tab, Table, TextArea,} from 'semantic-ui-react';
import {generate_id, getCompletions, sendRequestCommon} from '../helpers/utils';
import AceEditor from "react-ace";
import "ace-builds/src-noconflict/mode-json";
import "ace-builds/src-noconflict/theme-monokai";
import "ace-builds/src-noconflict/ext-language_tools"

let langTools = ace.acequire('ace/ext/language_tools');
langTools.setCompleters([{getCompletions: getCompletions}])

class SelfServiceStep3 extends Component {
  state = {
    custom_statement: "",
    isLoading: false,
    isSuccess: false,
    justification: "",
    messages: [],
    requestId: null,
    statement: "",
  };


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

    const response = await sendRequestCommon(payload, '/api/v2/generate_changes');
    if (response) {
      // TODO(heewonk), handle errors from the backend and validation
      const statement = JSON.stringify(response[0]["policy"]["policy_document"], null, 4);
      this.setState({
        custom_statement: statement,
        statement,
      });
    }
  }

  buildAceEditor(custom_statement) {
    let aceComponent = (
      <AceEditor
        mode="json"
        theme="monokai"
        width="100%"
        showPrintMargin={false}
        ref={function (reactAceComponent) {
          if (reactAceComponent && reactAceComponent != null) {
            const editor = reactAceComponent.editor;
            if (editor.completer && editor.completer.popup) {
              let popup = editor.completer.popup;
              popup.container.style.width = "600px";
              popup.resize();

            }
          }
        }}
        tabSize={4}
        onChange={this.handleJSONEditorChange.bind(this)}
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
    )
    return aceComponent
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

    return (
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
  }

  handleSubmit() {
    const {role} = this.props;
    const {justification, statement} = this.state;

    if (!justification) {
      return this.setState({
        messages: ["No Justification is Given"],
      });
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
          'value': statement,
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
    const {statement} = this.state;
    const messages = [];
    if (statement !== custom_statement) {
      messages.push("Please Review your custom changes before making a submission.");
    }
    this.setState({
      messages,
      custom_statement,
    });
  }

  render() {
    const {role} = this.props;
    const {custom_statement, isLoading, isSuccess, justification, messages, requestId, statement} = this.state;
    const messagesToShow = (messages.length > 0)
      ? (
        <Message negative>
          <Message.Header>
            There was an issue making a request.
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
        render: () => (
          <Tab.Pane>
            <Header>
              Please Review Permissions
              <Header.Subheader>
                You can customize your request using the JSON Editor for advanced permissions.
              </Header.Subheader>
            </Header>
            <p>
              Your new permissions will be attached to the role <a
              href={`/policies/edit/${role.account_id}/iamrole/${role.name}`} target="_blank">{role.arn}</a> with the
              followings.
            </p>
            {this.buildPermissionsTable()}
            <Divider/>
            <Header>
              Justification
            </Header>
            <Form>
              <TextArea
                onChange={this.handleJustificationChange.bind(this)}
                placeholder={"Your Justification"}
                value={justification}
              />
            </Form>
            <Divider/>
            <Button
              content="Submit"
              disabled={statement !== custom_statement}
              fluid
              onClick={this.handleSubmit.bind(this)}
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
            </Header>
            <br/>
            {this.buildAceEditor(custom_statement)}
            <Divider/>
            <Header>
              Justification
            </Header>
            <Form>
              <TextArea
                onChange={this.handleJustificationChange.bind(this)}
                placeholder={"Your Justification"}
                value={justification}
              />
            </Form>
            <Divider/>
            <Button
              content="Submit"
              fluid
              onClick={this.handleSubmit.bind(this)}
              primary
            />
          </Tab.Pane>
        ),
      }
    ];
    const tabContent = (isSuccess)
      ? (
        <Message positive>
          <Message.Header>
            Your request was successful.
          </Message.Header>
          You can check your request status from <a href={`/policies/request/${requestId}`} target="_blank">here</a>.
        </Message>

      )
      : (
        <React.Fragment>
          <Tab panes={panes}/>
          <br/>
        </React.Fragment>
      );

    return (
      <React.Fragment>
        <Dimmer
          active={isLoading}
          inverted
        >
          <Loader/>
        </Dimmer>
        {messagesToShow}
        {tabContent}
      </React.Fragment>
    );
  }
}

export default SelfServiceStep3;
