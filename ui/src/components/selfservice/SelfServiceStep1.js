import _ from "lodash";
import React, { Component } from "react";
import {
  Form,
  Grid,
  Header,
  Icon,
  Loader,
  Message,
  Search,
  Segment,
} from "semantic-ui-react";
import RoleDetails from "../roles/RoleDetails";
import "./SelfService.css";

const ARN_REGEX = /^arn:aws:iam::(?<accountId>\d{12}):role\/(?<roleName>.+)$/;

class SelfServiceStep1 extends Component {
  constructor(props) {
    super(props);
    this.state = {
      isLoading: false,
      isRoleLoading: false,
      messages: [],
      results: [],
      value: "",
    };
  }

  componentDidMount() {
    const { role } = this.props;
    if (role) {
      this.fetchRoleDetail(role.arn);
    }
  }

  fetchRoleDetail(value) {
    let {
      groups: { accountId, roleName },
    } = ARN_REGEX.exec(value);

    roleName = roleName.split("/").splice(-1, 1)[0];
    this.props
      .sendRequestCommon(null, `/api/v2/roles/${accountId}/${roleName}`, "get")
      .then((response) => {
        if (!response) {
          return;
        }
        // if the given role doesn't exist.
        if (response.status === 404) {
          this.props.handleRoleUpdate(null);
          this.setState({
            isLoading: false,
            isRoleLoading: false,
            messages: [response.message],
          });
        } else {
          const role = response;
          this.props.handleRoleUpdate(role);
          this.setState({
            isLoading: false,
            isRoleLoading: false,
            value: role.arn,
            messages: [],
          });
        }
      });
  }

  handleSearchChange(event, { value }) {
    this.setState(
      {
        isLoading: true,
        value,
      },
      () => {
        const match = ARN_REGEX.exec(value);
        if (match) {
          this.fetchRoleDetail(value);
        } else {
          // If the given ARN is not a valid one.
          this.setState(
            {
              isLoading: false,
            },
            () => {
              this.props.handleRoleUpdate(null);
            }
          );
        }
      }
    );

    setTimeout(() => {
      const { value } = this.state;
      if (value.length < 1) {
        return this.setState({
          isLoading: false,
          messages: [],
          results: [],
          value: "",
        });
      }

      const TYPEAHEAD_API = `/api/v2/typeahead/self_service_resources?typeahead=${value}`;
      this.props
        .sendRequestCommon(null, TYPEAHEAD_API, "get")
        .then((results) => {
          // The Semantic UI Search component is quite opinionated
          // as it expects search results data to be in a specific format
          // and will throw an error when this is not the case.
          // A way to get around the error is to add a key to each search result
          // that is expected - `title` in our use case.
          const reformattedResults = results.map((res, idx) => {
            return {
              id: idx,
              title: res.display_text,
              ...res,
            };
          });
          this.setState({
            isLoading: false,
            results: reformattedResults,
          });
        });
    }, 300);
  }

  handleResultSelect(e, { result }) {
    const value = _.isString(result.title) ? result.title.trim() : result.title;
    this.setState(
      {
        value,
        isRoleLoading: true,
      },
      () => {
        const match = ARN_REGEX.exec(result.title);
        if (match) {
          this.fetchRoleDetail(value);
        }
      }
    );
  }

  resultRenderer(result) {
    return (
      <Grid>
        <Grid.Row verticalAlign="middle">
          <Grid.Column width={10}>
            <div style={{ display: "flex" }}>
              <Icon
                name={result.icon}
                style={{ flexShrink: 0, width: "30px" }}
              />
              <strong
                style={{
                  display: "inline-block",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {result.display_text}
              </strong>
            </div>
          </Grid.Column>
          <Grid.Column width={6} textAlign="right">
            {result.account ? result.account : null}
          </Grid.Column>
        </Grid.Row>
      </Grid>
    );
  }

  render() {
    const role = this.props.role;
    const { isLoading, isRoleLoading, messages, results, value } = this.state;
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
    return (
      <Segment>
        {messagesToShow}
        <Grid columns={2} divided style={{ minHeight: "400px" }}>
          <Grid.Row>
            <Grid.Column
              style={{
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
              }}
            >
              <div>
                <Header as="h1">
                  Search & Select a Role
                  <Header.Subheader>
                    Search for the role(s) you want to modify the actions,
                    effects, or resources to. You can refine your search using
                    the advanced search options.
                  </Header.Subheader>
                </Header>
                <Form widths="equal">
                  <Form.Field required>
                    <Search
                      fluid
                      loading={isLoading}
                      onResultSelect={this.handleResultSelect.bind(this)}
                      onSearchChange={_.debounce(
                        this.handleSearchChange.bind(this),
                        500,
                        {
                          leading: true,
                        }
                      )}
                      results={results}
                      resultRenderer={this.resultRenderer}
                      value={value}
                      placeholder="Enter role name or search terms here"
                    />
                  </Form.Field>
                </Form>
              </div>

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
            </Grid.Column>
            <Grid.Column>
              <Header as="h4">Selected Role Information</Header>
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
  }
}

export default SelfServiceStep1;
