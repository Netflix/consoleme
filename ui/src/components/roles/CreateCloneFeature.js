import React, { useState, useEffect } from "react";
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
import { sendRequestCommon } from "../../helpers/utils";

const clone_options = [
  { text: "Assume Role Policy Document", value: "assume_role_policy" },
  { text: "Description", value: "copy_description" },
  { text: "Inline policies", value: "inline_policies" },
  { text: "Managed Policies", value: "managed_policies" },
  { text: "Tags", value: "tags" },
];

const clone_default_selected_options = clone_options.map(
  (option) => option.value
);

const CreateCloneFeature = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingAccount, setIsLoadingAccount] = useState(false);
  const [results, setResults] = useState([]);
  const [resultsAccount, setResultsAccount] = useState([]);
  const [value, setValue] = useState("");
  const [source_role, setSource_role] = useState(null);
  const [source_role_value, setSource_role_value] = useState("");
  const [dest_account_id, setDest_account_id] = useState(null);
  const [dest_account_id_value, setDest_account_id_value] = useState("");
  const [dest_role_name, setDest_role_name] = useState("");
  const [searchType, setSearchType] = useState("");
  const [description, setDescription] = useState("");
  const [messages, setMessages] = useState(null);
  const [requestSent, setRequestSent] = useState(false);
  const [requestResults, setRequestResults] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [roleCreated, setRoleCreated] = useState(false);
  const [options, setOptions] = useState(clone_default_selected_options);
  const [copy_description, setCopy_description] = useState(true);
  const [feature_type, setFeature_type] = useState("create");

  const [payload, setPayload] = useState(null);
  const [url, setUrl] = useState("");

  const handleSearchChange = (event, { name, value }) => {
    let stype;
    if (name === "source_role") {
      setIsLoading(true);
      setValue(value);
      setSource_role_value(value);
      setSource_role(null);
      setSearchType("iam_arn");
      stype = "iam_arn";
    } else {
      setIsLoadingAccount(true);
      setValue(value);
      setDest_account_id_value(value);
      setDest_account_id(null);
      setSearchType("account");
      stype = "account";
    }

    setTimeout(() => {
      if (value.length < 1) {
        setIsLoading(false);
        setIsLoadingAccount(false);
        setResults([]);
        setValue("");
        setSource_role(name === "source_role" ? null : source_role);
        setSource_role_value(name === "source_role" ? "" : source_role_value);
        setDest_account_id(name === "source_role" ? dest_account_id : null);
        setDest_account_id_value(
          name === "source_role" ? dest_account_id_value : ""
        );
        return;
      }
      const re = new RegExp(_.escapeRegExp(value), "i");

      const TYPEAHEAD_API =
        "/policies/typeahead?resource=" + stype + "&search=" + value;

      sendRequestCommon(null, TYPEAHEAD_API, "get").then((source) => {
        if (stype === "account") {
          setIsLoadingAccount(false);
          setResultsAccount(source.filter((result) => re.test(result.title)));
        } else {
          setIsLoading(false);
          setResults(source.filter((result) => re.test(result.title)));
        }
      });
    }, 300);
  };

  const handleSubmit = () => {
    if (feature_type === "clone") {
      handleCloneSubmit();
    } else {
      handleCreateSubmit();
    }
  };

  const handleCreateSubmit = () => {
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
      setMessages(errors);
    }
    const payload = {
      account_id: dest_account_id.substring(
        dest_account_id.indexOf("(") + 1,
        dest_account_id.indexOf(")")
      ),
      role_name: dest_role_name,
      description: description,
    };
    setDest_account_id(payload.account_id);
    submitRequest(payload, "/api/v2/roles");
  };

  const handleCloneSubmit = () => {
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
      setMessages(errors);
    }

    const cloneOptions = {
      assume_role_policy: options.includes("assume_role_policy"),
      tags: options.includes("tags"),
      copy_description: options.includes("copy_description"),
      description: description,
      inline_policies: options.includes("inline_policies"),
      managed_policies: options.includes("managed_policies"),
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
    setDest_account_id(payload.dest_account_id);
    submitRequest(payload, "/api/v2/clone/role");
  };

  useEffect(async () => {
    if (isSubmitting) {
      const response = await sendRequestCommon(payload, url);
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
      setIsSubmitting(false);
      setMessages(messages);
      setRequestSent(requestSent);
      setRequestResults(requestResults);
      setRoleCreated(roleCreated);
    }
  }, [isSubmitting]);

  const submitRequest = (payload, url) => {
    setPayload(payload);
    setUrl(url);
    setMessages(null);
    setIsSubmitting(true);
  };

  const handleResultSelect = (e, { name, value_name, result }) => {
    if (name === "source_role" && value_name === "source_role_value") {
      setSource_role(result.title);
      setSource_role_value(result.title);
    } else if (
      name === "dest_account_id" &&
      value_name === "dest_account_id_value"
    ) {
      setDest_account_id(result.title);
      setDest_account_id_value(result.title);
    }
    setIsLoading(false);
  };

  const handleDropdownChange = (e, { value }) => {
    setOptions(value);
    setCopy_description(value.includes("copy_description"));
  };

  const handleChange = (e, { name, value }) => {
    if (name === "feature_type") {
      setFeature_type(value);
    } else if (name === "dest_role_name") {
      setDest_role_name(value);
    } else if (name === "description") {
      setDescription(value);
    }
  };

  const handleCheckChange = (e, { name, value }) => {
    // setState({ ...state, [name]: !value });
  };

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
              onResultSelect={(e, data) => handleResultSelect(e, data)}
              onSearchChange={_.debounce(
                (e) => handleSearchChange(e, e.target),
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
            onChange={(e) => handleDropdownChange(e, e.target)}
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
            onChange={handleChange}
          />
          <Form.Radio
            label="Clone from existing role"
            name="feature_type"
            value="clone"
            checked={feature_type === "clone"}
            onChange={handleChange}
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
                    onResultSelect={(e, data) => handleResultSelect(e, data)}
                    onSearchChange={_.debounce(
                      (e) => handleSearchChange(e, e.target),
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
                  onChange={handleChange}
                />
                <Form.Input
                  required
                  fluid
                  name="description"
                  value={description}
                  placeholder="Optional description"
                  onChange={handleChange}
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
          onClick={() => handleSubmit(this)}
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
};

export function renderCreateCloneWizard() {
  ReactDOM.render(
    <CreateCloneFeature />,
    document.getElementById("create_clone_wizard")
  );
}

export default CreateCloneFeature;
