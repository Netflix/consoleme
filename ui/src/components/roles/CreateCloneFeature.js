import React, { Component } from "react";
import ReactDOM from "react-dom";
import _ from "lodash";
import {
  Button,
  Dimmer,
  Loader,
  Form,
  Grid,
  Header,
  Message,
  Search,
  Segment,
  Icon,
  Feed,
} from "semantic-ui-react";

const clone_options = [
  { text: "Assume Role Policy Document", value: "assume_role_policy" },
  { text: "Description", value: "copy_description" },
  { text: "Inline policies", value: "inline_policies" },
  { text: "Managed Policies", value: "managed_policies" },
  { text: "Tags", value: "tags" },
  { text: "Max Session Duration", value: "max_session_duration" },
];

const clone_default_selected_options = clone_options.map(
  (option) => option.value
);

class CreateCloneFeature extends Component {
  constructor(props) {
    super(props);
    this.state = {
      isLoading: false,
      isLoadingAccount: false,
      results: [],
      resultsAccount: [],
      value: "",
      source_role: null,
      source_role_value: "",
      dest_account_id: null,
      dest_account_id_value: "",
      dest_role_name: "",
      searchType: "",
      description: "",
      messages: null,
      requestSent: false,
      requestResults: [],
      isSubmitting: false,
      roleCreated: false,
      options: clone_default_selected_options,
      copy_description: true,
      feature_type: "create",
    };
  }

  handleSearchChange(event, { name, value }) {
    if (name === "source_role") {
      this.setState({
        isLoading: true,
        value,
        source_role_value: value,
        source_role: null,
        searchType: "iam_arn",
      });
    } else {
      this.setState({
        isLoadingAccount: true,
        value,
        dest_account_id_value: value,
        dest_account_id: null,
        searchType: "account",
      });
    }

    setTimeout(() => {
      const { value, searchType } = this.state;
      if (value.length < 1) {
        return this.setState({
          isLoading: false,
          isLoadingAccount: false,
          results: [],
          value: "",
          source_role: name === "source_role" ? null : this.state.source_role,
          source_role_value:
            name === "source_role" ? "" : this.state.source_role_value,
          dest_account_id:
            name === "source_role" ? this.state.dest_account_id : null,
          dest_account_id_value:
            name === "source_role" ? this.state.dest_account_id_value : "",
        });
      }

      const re = new RegExp(_.escapeRegExp(value), "i");

      const TYPEAHEAD_API =
        "/policies/typeahead?resource=" + searchType + "&search=" + value;

      this.props
        .sendRequestCommon(null, TYPEAHEAD_API, "get")
        .then((source) => {
          if (!source) {
            return;
          }
          if (searchType === "account") {
            this.setState({
              isLoadingAccount: false,
              resultsAccount: source.filter((result) => re.test(result.title)),
            });
          } else {
            this.setState({
              isLoading: false,
              results: source.filter((result) => re.test(result.title)),
            });
          }
        });
    }, 300);
  }

  handleSubmit() {
    const { feature_type } = this.state;
    if (feature_type === "clone") {
      this.handleCloneSubmit();
    } else {
      this.handleCreateSubmit();
    }
  }

  handleCreateSubmit() {
    const { dest_account_id, dest_role_name } = this.state;
    const errors = [];
    if (!dest_account_id) {
      errors.push(
        "No destination account provided, please select a destination account"
      );
    }
    if (dest_role_name === "") {
      errors.push(
        "No destination role name provided, please provide a destination role name"
      );
    }
    if (errors.length > 0) {
      return this.setState({
        messages: errors,
      });
    }
    const payload = {
      account_id: dest_account_id.substring(
        dest_account_id.indexOf("(") + 1,
        dest_account_id.indexOf(")")
      ),
      role_name: dest_role_name,
      description: this.state.description,
    };
    this.setState({
      dest_account_id: payload.account_id,
    });
    this.submitRequest(payload, "/api/v2/roles");
  }

  handleCloneSubmit() {
    const { source_role, dest_account_id, dest_role_name } = this.state;
    const errors = [];
    if (!source_role) {
      errors.push("No source role provided, please select a source role");
    }
    if (!dest_account_id) {
      errors.push(
        "No destination account provided, please select a destination account"
      );
    }
    if (dest_role_name === "") {
      errors.push(
        "No destination role name provided, please provide a destination role name"
      );
    }
    if (errors.length > 0) {
      return this.setState({
        messages: errors,
      });
    }

    const cloneOptions = {
      assume_role_policy: this.state.options.includes("assume_role_policy"),
      tags: this.state.options.includes("tags"),
      copy_description: this.state.options.includes("copy_description"),
      description: this.state.description,
      inline_policies: this.state.options.includes("inline_policies"),
      managed_policies: this.state.options.includes("managed_policies"),
      max_session_duration: this.state.options.includes("max_session_duration"),
    };

    const payload = {
      account_id: source_role.substring(13, 25),
      role_name: source_role.substring(source_role.lastIndexOf("/") + 1),
      dest_account_id: dest_account_id.substring(
        dest_account_id.indexOf("(") + 1,
        dest_account_id.indexOf(")")
      ),
      dest_role_name,
      options: cloneOptions,
    };
    this.setState({
      dest_account_id: payload.dest_account_id,
    });
    this.submitRequest(payload, "/api/v2/clone/role");
  }

  submitRequest(payload, url) {
    this.setState(
      {
        messages: null,
        isSubmitting: true,
      },
      async () => {
        const response = await this.props.sendRequestCommon(payload, url);
        const messages = [];
        let requestResults = [];
        let requestSent = false;
        let roleCreated = false;
        if (response) {
          requestSent = true;
          if (!response.hasOwnProperty("role_created")) {
            requestResults.push({
              Status: "error",
              message: response.message,
            });
          } else {
            requestResults = response.action_results;
            if (response.role_created === "true") {
              roleCreated = true;
            }
          }
        } else {
          messages.push("Failed to submit cloning request");
        }
        this.setState({
          isSubmitting: false,
          messages,
          requestSent,
          requestResults,
          roleCreated,
        });
      }
    );
  }

  handleResultSelect(e, { name, value_name, result }) {
    this.setState({
      [value_name]: result.title,
      [name]: result.title,
      isLoading: false,
    });
  }

  handleDropdownChange(e, { value }) {
    this.setState({
      options: value,
      copy_description: value.includes("copy_description"),
    });
  }

  handleChange = (e, { name, value }) => this.setState({ [name]: value });

  handleCheckChange = (e, { name, value }) => this.setState({ [name]: !value });

  render() {
    const {
      isLoading,
      isLoadingAccount,
      results,
      source_role_value,
      dest_account_id_value,
      dest_role_name,
      resultsAccount,
      description,
      messages,
      requestSent,
      requestResults,
      options,
      isSubmitting,
      roleCreated,
      dest_account_id,
      copy_description,
      feature_type,
    } = this.state;
    const messagesToShow =
      messages != null && messages.length > 0 ? (
        <Message negative>
          <Message.Header>There are some missing parameters</Message.Header>
          <Message.List>
            {messages.map((message) => (
              <Message.Item>{message}</Message.Item>
            ))}
          </Message.List>
        </Message>
      ) : null;

    const sourceRoleContent =
      feature_type === "clone" ? (
        <Grid.Column>
          <Header size="medium">
            Select source role
            <Header.Subheader>
              Please search for the role you want to clone.
            </Header.Subheader>
          </Header>
          <Form>
            <Form.Field required>
              <label>Source Role</label>
              <Search
                loading={isLoading}
                fluid
                name="source_role"
                value_name="source_role_value"
                onResultSelect={this.handleResultSelect.bind(this)}
                onSearchChange={_.debounce(
                  this.handleSearchChange.bind(this),
                  500,
                  {
                    leading: true,
                  }
                )}
                results={results}
                value={source_role_value}
              />
            </Form.Field>
            <Form.Dropdown
              placeholder="Options"
              fluid
              multiple
              search
              selection
              options={clone_options}
              defaultValue={options}
              label="Attributes to clone"
              onChange={this.handleDropdownChange.bind(this)}
            />
          </Form>
        </Grid.Column>
      ) : null;

    const feature_selection = (
      <Segment>
        <Form>
          <Form.Group inline>
            <Form.Radio
              label="Create blank role"
              name="feature_type"
              value="create"
              checked={feature_type === "create"}
              onChange={this.handleChange}
            />
            <Form.Radio
              label="Clone from existing role"
              name="feature_type"
              value="clone"
              checked={feature_type === "clone"}
              onChange={this.handleChange}
            />
          </Form.Group>
        </Form>
      </Segment>
    );

    const preRequestContent = (
      <Segment.Group vertical>
        {feature_selection}
        <Segment>
          <Grid columns={2} divided>
            <Grid.Row>
              {sourceRoleContent}
              <Grid.Column>
                <Header size="medium">
                  Role to be created
                  <Header.Subheader>
                    Please enter the destination account where you want the role
                    and desired role name.
                  </Header.Subheader>
                </Header>
                <Form>
                  <Form.Field required>
                    <label>Account ID</label>
                    <Search
                      loading={isLoadingAccount}
                      name="dest_account_id"
                      value_name="dest_account_id_value"
                      onResultSelect={this.handleResultSelect.bind(this)}
                      onSearchChange={_.debounce(
                        this.handleSearchChange.bind(this),
                        500,
                        {
                          leading: true,
                        }
                      )}
                      results={resultsAccount}
                      value={dest_account_id_value}
                      fluid
                    />
                  </Form.Field>
                  <Form.Input
                    required
                    fluid
                    label="Role name"
                    name="dest_role_name"
                    value={dest_role_name}
                    placeholder="Role name"
                    onChange={this.handleChange}
                  />
                  <Form.Input
                    required
                    fluid
                    name="description"
                    value={description}
                    placeholder="Optional description"
                    onChange={this.handleChange}
                    disabled={
                      copy_description === true && feature_type === "clone"
                    }
                  />
                </Form>
              </Grid.Column>
            </Grid.Row>
          </Grid>
        </Segment>
        <Segment>
          {messagesToShow}
          <Button
            content="Submit"
            fluid
            onClick={this.handleSubmit.bind(this)}
            primary
          />
        </Segment>
      </Segment.Group>
    );

    const postRequestContent =
      requestResults.length > 0 ? (
        <Segment>
          <Feed>
            {requestResults.map((result) => {
              const iconLabel =
                result.status === "success" ? (
                  <Icon name="checkmark" color="teal" />
                ) : (
                  <Icon name="close" color="pink" />
                );
              const feedResult =
                result.status === "success" ? "Success" : "Error";
              return (
                <Feed.Event>
                  <Feed.Label>{iconLabel}</Feed.Label>
                  <Feed.Content>
                    <Feed.Date>{feedResult}</Feed.Date>
                    <Feed.Summary>{result.message}</Feed.Summary>
                  </Feed.Content>
                </Feed.Event>
              );
            })}
          </Feed>
        </Segment>
      ) : null;

    const roleInfoLink = roleCreated ? (
      <Message info>
        The requested role has been created. You can view the role details{" "}
        <a
          href={`/policies/edit/${dest_account_id}/iamrole/${dest_role_name}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          here
        </a>
        .
      </Message>
    ) : null;

    const pageContent = requestSent ? postRequestContent : preRequestContent;

    return (
      <>
        <Dimmer active={isSubmitting} inverted>
          <Loader />
        </Dimmer>
        <Segment>
          <Header size="huge">Create a role</Header>
        </Segment>
        {roleInfoLink}
        {pageContent}
      </>
    );
  }
}

export function renderCreateCloneWizard() {
  ReactDOM.render(
    <CreateCloneFeature />,
    document.getElementById("create_clone_wizard")
  );
}

export default CreateCloneFeature;
