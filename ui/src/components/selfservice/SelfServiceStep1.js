import _ from "lodash";
import React, { useState, useEffect } from "react";
import {
  Form,
  Grid,
  Header,
  Loader,
  Message,
  Search,
  Segment,
} from "semantic-ui-react";
import RoleDetails from "../roles/RoleDetails";
import "./SelfService.css";
import { sendRequestCommon } from "../../helpers/utils";

const ARN_REGEX = /^arn:aws:iam::(?<accountId>\d{12}):role\/(?<roleName>.+)$/;

const SelfServiceStep1 = (props) => {
  const [isLoading, setIsLoading] = useState(false);
  const [isRoleLoading, setIsRoleLoading] = useState(false);
  const [messages, setMessages] = useState([]);
  const [results, setResults] = useState([]);
  const [value, setValue] = useState("");

  useEffect(() => {
    const { role } = props;
    if (role) {
      fetchRoleDetail(role.arn);
    }
  }, []);

  const fetchRoleDetail = (value) => {
    let {
      groups: { accountId, roleName },
    } = ARN_REGEX.exec(value);

    roleName = roleName.split("/").splice(-1, 1)[0];
    sendRequestCommon(
      null,
      `/api/v2/roles/${accountId}/${roleName}`,
      "get"
    ).then((response) => {
      // if the given role doesn't exist.
      if (response.status === 404) {
        // console.log(response.status, "if");
        props.handleRoleUpdate(null);
        setIsLoading(false);
        setIsRoleLoading(false);
        setMessages(response.messages);
      } else {
        const role = response;
        // console.log(role);
        // console.log(role.arn);
        props.handleRoleUpdate(role);
        setIsLoading(false);
        setIsRoleLoading(false);
        setValue(role.arn);
        setMessages([]);
      }
    });
  };

  useEffect(() => {
    if (isLoading) {
      const match = ARN_REGEX.exec(value);
      if (match) {
        fetchRoleDetail(value);
      } else {
        // If the given ARN is not a valid one.
        setIsLoading(false);
      }
    } else {
      props.handleRoleUpdate(null);
    }
  }, [isLoading]);

  useEffect(() => {
    if (isRoleLoading) {
      const match = ARN_REGEX.exec(value);
      if (match) {
        fetchRoleDetail(value);
      }
    }
  }, [isRoleLoading]);

  const handleSearchChange = (event, { value }) => {
    setIsLoading(true);
    setValue(value);

    setTimeout(() => {
      if (value.length < 1) {
        setIsLoading(false);
        setMessages([]);
        setResults([]);
        setValue("");
        return;
      }
      const re = new RegExp(_.escapeRegExp(value), "i");
      const isMatch = (result) => re.test(result.title);
      const TYPEAHEAD_API = "/policies/typeahead?resource=app&search=" + value;
      sendRequestCommon(null, TYPEAHEAD_API, "get").then((source) => {
        const filteredResults = _.reduce(
          source,
          (memo, data, name) => {
            const results = _.filter(data.results, isMatch);
            if (results.length) {
              memo[name] = { name, results };
            }
            return memo;
          },
          {}
        );
        setIsLoading(false);
        setResults(filteredResults);
      });
    }, 300);
  };

  const handleResultSelect = (e, { result }) => {
    const val = _.isString(result.title) ? result.title.trim() : result.title;
    setValue(val);
    setIsRoleLoading(true);
  };

  const role = props.role;
  // const { isLoading, isRoleLoading, messages, results, value } = state;
  const messagesToShow =
    messages && messages.length > 0 ? (
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

  return (
    <Segment>
      {messagesToShow}
      {/* {console.log(props)} */}
      <Grid columns={2} divided>
        <Grid.Row>
          <Grid.Column>
            <Header>
              Select a Role
              <Header.Subheader>
                Please search for your role where you want to attach new
                permissions.
              </Header.Subheader>
            </Header>
            <p>
              For Help, please visit{" "}
              <a
                href="http://go/selfserviceiamtldr"
                target="_blank"
                rel="noopener noreferrer"
              >
                go/selfserviceiamtldr
              </a>
            </p>
            <Form widths="equal">
              <Form.Field required>
                <label>Search Your Application Roles</label>
                <Search
                  category
                  loading={isLoading}
                  onResultSelect={(e, data) => handleResultSelect(e, data)}
                  onSearchChange={_.debounce(
                    (e) => handleSearchChange(e, e.target),
                    500,
                    {
                      leading: true,
                    }
                  )}
                  results={results}
                  value={value}
                />
              </Form.Field>
            </Form>
          </Grid.Column>
          <Grid.Column>
            <Header>Selected Role Information</Header>
            {isRoleLoading ? (
              <Loader active={isRoleLoading} />
            ) : (
              <RoleDetails role={role} />
            )}
          </Grid.Column>
        </Grid.Row>
      </Grid>
    </Segment>
  );
};

export default SelfServiceStep1;
