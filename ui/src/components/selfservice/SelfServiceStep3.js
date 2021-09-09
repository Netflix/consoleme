import React, { Component } from "react";
import {
  Button,
  Dimmer,
  Divider,
  Form,
  Grid,
  Header,
  Icon,
  Loader,
  Message,
  Segment,
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
      active: true,
      requestUrl: null,
      principal_name: "",
      change_type: "inline_policy",
    };
    this.inlinePolicyEditorRef = React.createRef();
    this.editorDidMount = this.editorDidMount.bind(this);
    this.handleJustificationChange = this.handleJustificationChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
    this.handleAdminSubmit = this.handleAdminSubmit.bind(this);
    this.onValueChange = this.onValueChange.bind(this);
  }

  async componentDidMount() {
    const { role, updated_policy } = this.props;
    this.setState({
      messages: [],
    });

    let parsed_policy = updated_policy;
    try {
      parsed_policy = { policy_document: JSON.parse(updated_policy) };
    } catch {
      // Some template languages don't use JSON
    }

    const payload = {
      dry_run: true,
      changes: {
        changes: [
          {
            principal: role.principal,
            change_type: this.state.change_type,
            action: "attach",
            policy: parsed_policy,
            expiration_date: this.props.expiration_date,
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
          principal_name:
            role.principal.resource_identifier +
            role.principal.resource_identifier,
          active: false,
          change_type: "generic_file",
        });
      } else {
        this.setState({
          new_policy: JSON.stringify(
            response.extended_request.changes.changes[0].policy.policy_document,
            null,
            "\t"
          ),
          principal_name: role.principal.principal_arn,
          active: false,
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

  onValueChange(newValue, e) {
    this.setState({
      new_policy: newValue,
    });
  }

  buildMonacoEditor() {
    const { old_policy, new_policy } = this.state;

    return (
      <MonacoDiffComponent
        oldValue={old_policy}
        newValue={new_policy}
        onLintError={this.onLintError}
        onValueChange={this.onValueChange}
        readOnly={false}
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
    const { role } = this.props;
    const { justification, admin_auto_approve, new_policy } = this.state;
    if (!justification) {
      return this.setState((state) => ({
        messages: ["No Justification is Given"],
      }));
    }
    let parsed_policy = new_policy;
    try {
      parsed_policy = { policy_document: JSON.parse(new_policy) };
    } catch {
      // Some template languages don't use JSON
    }

    const requestV2 = {
      justification,
      admin_auto_approve,
      changes: {
        changes: [
          {
            principal: role.principal,
            change_type: this.state.change_type,
            action: "attach",
            policy: parsed_policy,
            expiration_date: this.props.expiration_date,
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
          const { request_created, request_id, request_url } = response;
          if (request_created === true) {
            messages.push("success");
            return this.setState({
              isLoading: false,
              isSuccess: true,
              messages,
              requestId: request_id,
              requestUrl: request_url,
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

  getMessages() {
    const { isSuccess, messages, requestUrl } = this.state;
    if (messages.length > 0 && isSuccess === true) {
      return (
        <Message positive>
          <Message.Header>Your request was successful.</Message.Header>
          You can check your request status from{" "}
          <a href={requestUrl} target="_blank" rel="noopener noreferrer">
            here
          </a>
          .
        </Message>
      );
    } else if (messages.length > 0 && isSuccess === false) {
      return (
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
      );
    }
  }

  render() {
    const {
      admin_bypass_approval_enabled,
      isError,
      justification,
      old_policy,
      new_policy,
      role,
      active,
      isLoading,
    } = this.state;

    const messagesToShow = this.getMessages();

    // Only allow admin approval on AwsResource requests and not templated requests
    const submission_buttons =
      admin_bypass_approval_enabled &&
      role?.principal?.principal_type === "AwsResource" ? (
        <Grid.Row>
          <Button
            content={
              <div>
                <h3 style={{ marginBottom: "0px" }}>Go Back</h3>
                <h3
                  style={{
                    fontStyle: "italic",
                    opacity: "70%",
                    marginTop: "0px",
                  }}
                >
                  I need to make edits
                </h3>
              </div>
            }
            disabled={isError}
            fluid
            onClick={() => {
              this.props.handleStepClick("previous");
            }}
            style={{
              width: "50%",
              display: "inline-block",
              textAlign: "center",
              backgroundColor: "#f8f8f9",
              maxWidth: "15em",
            }}
            attached="left"
          />
          <Button
            content={
              <div>
                <h3 style={{ marginBottom: "0px" }}>Submit</h3>
                <h3
                  style={{
                    fontStyle: "italic",
                    opacity: "70%",
                    marginTop: "0px",
                  }}
                >
                  Everything looks good
                </h3>
              </div>
            }
            disabled={isError}
            fluid
            onClick={this.handleSubmit}
            style={{
              width: "50%",
              display: "inline-block",
              textAlign: "center",
              maxWidth: "15em",
            }}
            primary
            attached="right"
          />
          <Button
            content={
              <div>
                <h3 style={{ marginBottom: "0px" }}>Submit</h3>
                <h3
                  style={{
                    fontStyle: "italic",
                    opacity: "70%",
                    marginTop: "0px",
                  }}
                >
                  And apply without approval
                </h3>
              </div>
            }
            disabled={isError}
            fluid
            onClick={this.handleAdminSubmit}
            style={{
              width: "50%",
              display: "inline-block",
              textAlign: "center",
              maxWidth: "20em",
            }}
            floated={"right"}
            positive
          />
        </Grid.Row>
      ) : (
        <Grid.Row style={{ maxWidth: "30em" }}>
          <Button
            content={
              <div>
                <h3 style={{ marginBottom: "0px" }}>Go Back</h3>
                <h3
                  style={{
                    fontStyle: "italic",
                    opacity: "70%",
                    marginTop: "0px",
                  }}
                >
                  I need to make edits
                </h3>
              </div>
            }
            disabled={isError}
            fluid
            onClick={() => {
              this.props.handleStepClick("previous");
            }}
            style={{
              width: "50%",
              display: "inline-block",
              textAlign: "center",
              backgroundColor: "#f8f8f9",
            }}
            attached="left"
          />
          <Button
            content={
              <div>
                <h3 style={{ marginBottom: "0px" }}>Submit for Review</h3>
                <h3
                  style={{
                    fontStyle: "italic",
                    opacity: "70%",
                    marginTop: "0px",
                  }}
                >
                  Everything looks good
                </h3>
              </div>
            }
            disabled={isError}
            fluid
            onClick={this.handleSubmit}
            style={{
              width: "50%",
              display: "inline-block",
              textAlign: "center",
            }}
            positive
            attached="right"
          />
        </Grid.Row>
      );

    return (
      <div>
        <Header size={"huge"}>Review Changes & Submit</Header>
        {this.state.principal_name ? (
          <p>
            Principal: <b>{this.state.principal_name}</b>
          </p>
        ) : null}
        <p>
          Use the following editor to review changes before submitting for
          review.
        </p>
        <Segment>
          <Dimmer active={active}>
            <Loader>Loading</Loader>
          </Dimmer>
          <MonacoDiffComponent
            oldValue={old_policy}
            newValue={new_policy}
            onLintError={this.onLintError}
            onValueChange={this.onValueChange}
            readOnly={false}
          />
        </Segment>
        <Divider />
        <Header>
          Justification
          <sup>
            <Icon name="asterisk" style={{ color: "red", fontSize: ".5em" }} />
          </sup>{" "}
        </Header>
        <Form>
          <Dimmer active={isLoading}>
            <Loader>Submitting Request</Loader>
          </Dimmer>
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
  }
}

export default SelfServiceStep3;
