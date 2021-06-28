import React, { Component } from "react";
import {
  Button,
  Divider,
  Form,
  Grid,
  Header,
  Message,
  Tab,
  TextArea,
} from "semantic-ui-react";
import MonacoDiffComponent from "../blocks/MonacoDiffComponent";

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
      statement: "",
      admin_bypass_approval_enabled: this.props.admin_bypass_approval_enabled,
      export_to_terraform_enabled: this.props.export_to_terraform_enabled,
      admin_auto_approve: false,
      policy_name: "",
      dry_run_policy: "",
      old_policy: "",
      new_policy: "",
      role: this.props.role,
    };
    this.inlinePolicyEditorRef = React.createRef();
    this.editorDidMount = this.editorDidMount.bind(this);
    this.handleJustificationChange = this.handleJustificationChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
    this.handleAdminSubmit = this.handleAdminSubmit.bind(this);
  }

  async componentDidMount() {
    const { role, updated_policy } = this.props;

    const payload = {
      dry_run: true,
      changes: {
        changes: [
          {
            principal: role.principal,
            change_type: "inline_policy",
            action: "attach",
            policy: {
              policy_document: JSON.parse(updated_policy),
            },
          },
        ],
      },
    };

    const response = await this.props.sendRequestCommon(
      payload,
      "/api/v2/request"
    );

    if (response.status != null && response.status === 400) {
      return this.setState({
        isError: true,
        messages: [response.message],
      });
    }

    if (response.extended_request != null) {
      if (role.principal.principal_type === "HoneybeeAwsResourceTemplate") {
        this.setState({
          new_policy: response.extended_request.changes.changes[0].policy,
          old_policy: response.extended_request.changes.changes[0].old_policy,
        });
      } else {
        this.setState({
          new_policy: JSON.stringify(
            response.extended_request.changes.changes[0].policy.policy_document,
            null,
            "\t"
          ),
        });
      }
    }
  }

  editorDidMount(editor) {
    editor._modifiedEditor.onDidChangeModelDecorations(() => {
      const { modifiedEditor } = this.state;
      const model = modifiedEditor.getModel();
      if (model === null || model.getModeId() !== "json") {
        return;
      }

      const owner = model.getModeId();
      const uri = model.uri;
      const markers = editor.getModelMarkers({ owner, resource: uri });
      this.onLintError(
        markers.map(
          (marker) =>
            `Lint error on line ${marker.startLineNumber} columns ${marker.startColumn}-${marker.endColumn}: ${marker.message}`
        )
      );
    });
    this.setState({
      modifiedEditor: editor._modifiedEditor,
    });
  }

  onValueChange() {}

  buildMonacoEditor() {
    const { old_policy, new_policy } = this.state;

    return (
      <MonacoDiffComponent
        oldValue={old_policy}
        newValue={new_policy}
        readOnly={true}
        onLintError={this.onLintError}
        onValueChange={this.onValueChange}
      />
    );
  }

  handleAdminSubmit() {
    this.setState(
      {
        admin_auto_approve: true,
      },
      () => {
        this.handleSubmit();
      }
    );
  }

  handleSubmit() {
    const { role, updated_policy } = this.props;
    const { justification, admin_auto_approve } = this.state;
    if (!justification) {
      return this.setState((state) => ({
        messages: ["No Justification is Given"],
      }));
    }

    const requestV2 = {
      justification,
      admin_auto_approve,
      changes: {
        changes: [
          {
            principal: role.principal,
            change_type: "inline_policy",
            action: "attach",
            policy: {
              policy_document: JSON.parse(updated_policy),
            },
          },
        ],
      },
    };

    this.setState(
      {
        isLoading: true,
      },
      async () => {
        const response = await this.props.sendRequestCommon(
          requestV2,
          "/api/v2/request"
        );

        const messages = [];
        if (response) {
          const { request_created, request_id } = response;
          if (request_created === true) {
            return this.setState({
              isLoading: false,
              isSuccess: true,
              messages,
              requestId: request_id,
            });
          }
          messages.push(
            "Server reported an error with the request: " +
              JSON.stringify(response)
          );
        } else {
          messages.push("Failed to submit request");
        }
        this.setState({
          isLoading: false,
          messages,
        });
      }
    );
  }

  handleJustificationChange(e) {
    this.setState({
      justification: e.target.value,
    });
  }

  onLintError = (lintErrors) => {
    if (lintErrors.length > 0) {
      this.setState({
        messages: lintErrors,
        isError: true,
      });
    } else {
      this.setState({
        messages: [],
        isError: false,
      });
    }
  };

  render() {
    const {
      admin_bypass_approval_enabled,
      custom_statement,
      isError,
      isSuccess,
      justification,
      messages,
      requestId,
      statement,
      old_policy,
      new_policy,
      role,
    } = this.state;

    const active = custom_statement !== statement;
    const messagesToShow =
      messages.length > 0 ? (
        <Message negative>
          <Message.Header>
            We found some problems for this request.
          </Message.Header>
          <Message.List>
            {messages.map((message) => (
              <Message.Item>{message}</Message.Item>
            ))}
          </Message.List>
        </Message>
      ) : null;

    // Only allow admin approval on AwsResource requests and not templated requests
    const submission_buttons =
      admin_bypass_approval_enabled &&
      role?.principal?.principal_type === "AwsResource" ? (
        <Grid columns={2}>
          <Grid.Row>
            <Grid.Column>
              <Button
                content="Submit and apply without approval"
                disabled={isError}
                onClick={this.handleAdminSubmit}
                positive
                fluid
              />
            </Grid.Column>
            <Grid.Column>
              <Button
                content="Submit"
                disabled={isError}
                onClick={this.handleSubmit}
                primary
                fluid
              />
            </Grid.Column>
          </Grid.Row>
        </Grid>
      ) : (
        <Button
          content="Submit"
          disabled={isError}
          fluid
          onClick={this.handleSubmit}
          primary
        />
      );

    return (
      <div>
        <Header size={"huge"}>Review Changes & Submit</Header>
        <p>
          Use the following editor to review the changes you've modified before
          submitting for team review.
        </p>
        <MonacoDiffComponent
          oldValue={old_policy}
          newValue={new_policy}
          readOnly={true}
          onLintError={this.onLintError}
          onValueChange={this.onValueChange}
        />
        <Divider />
        <Header>Justification</Header>
        <Form>
          <TextArea
            onChange={this.handleJustificationChange}
            placeholder="Your Justification"
            value={justification}
          />
        </Form>
        <Divider />
        {messagesToShow}
        {submission_buttons}
      </div>
    );

    const tabContent = isSuccess ? (
      <Message positive>
        <Message.Header>Your request was successful.</Message.Header>
        You can check your request status from{" "}
        <a
          href={`/policies/request/${requestId}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          here
        </a>
        .
      </Message>
    ) : (
      <>
        <Tab
          onTabChange={(event, data) =>
            this.setState({
              activeIndex: data.activeIndex,
            })
          }
        />
        <br />
      </>
    );
    return tabContent;
  }
}

export default SelfServiceStep3;
