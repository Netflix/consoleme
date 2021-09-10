import _ from "lodash";
import React, { Component } from "react";
import {
  Button,
  Divider,
  Form,
  Grid,
  Header,
  Icon,
  Loader,
  Message,
  Search,
  Segment,
} from "semantic-ui-react";
import ReactMarkdown from "react-markdown";
import RoleDetails from "../roles/RoleDetails";
import "./SelfService.css";
import SemanticDatepicker from "react-semantic-ui-datepickers";

class SelfServiceStep1 extends Component {
  constructor(props) {
    super(props);
    this.state = {
      isLoading: false,
      isRoleLoading: false,
      messages: [],
      results: [],
      value: "",
      count: [],
      principal: {},
    };
  }

  fetchRoleDetail(endpoint) {
    const { principal } = this.state;
    this.props.sendRequestCommon(null, endpoint, "get").then((response) => {
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
        response.principal = principal;
        this.props.handleRoleUpdate(response);
        this.setState({
          isLoading: false,
          isRoleLoading: false,
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
        this.setState(
          {
            isLoading: false,
          },
          () => {
            this.props.handleRoleUpdate(null);
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
    );
  }

  handleResultSelect(e, { result }) {
    const value = _.isString(result.title) ? result.title.trim() : result.title;
    this.setState(
      {
        value,
        isRoleLoading: true,
        principal: result.principal,
      },
      () => {
        this.fetchRoleDetail(result.details_endpoint);
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
                {result.icon === "users" ? (
                  <span style={{ color: "#286f85" }}>
                    {result.display_text}
                  </span>
                ) : (
                  <span>{result.display_text}</span>
                )}
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
    const { config, role } = this.props;
    const {
      isLoading,
      isRoleLoading,
      messages,
      results,
      value,
      principal,
    } = this.state;
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
                    Search for the role or template that you would like to add
                    permissions to.
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
                      placeholder="Enter search terms here"
                    />
                  </Form.Field>
                  {/*Allow users to specify expiration dates for AwsResources*/}
                  {this.props?.user?.site_config?.temp_policy_support &&
                  principal &&
                  principal?.principal_type === "AwsResource" ? (
                    <Form.Field>
                      <br />

                      <Header as="h1">
                        <Header.Subheader>
                          (Optional) Expiration date for requested permissions
                        </Header.Subheader>
                      </Header>
                      <SemanticDatepicker
                        onChange={this.props.handleSetPolicyExpiration.bind(
                          this
                        )}
                        type="basic"
                        compact
                      />
                    </Form.Field>
                  ) : null}
                </Form>
              </div>
              <Grid stackable columns={2}>
                <Grid.Row className={"helpContainer"}>
                  <Grid.Column>
                    {config?.help_message ? (
                      <ReactMarkdown
                        className={"help"}
                        linkTarget="_blank"
                        children={config.help_message}
                      />
                    ) : null}
                  </Grid.Column>
                  <Grid.Column>
                    <Button
                      style={{
                        fontSize: "1.25em",
                        width: "11em",
                        height: "3.5em",
                      }}
                      floated="right"
                      positive
                      onClick={this.props.handleStepClick.bind(this, "next")}
                    >
                      Next
                    </Button>
                  </Grid.Column>
                </Grid.Row>
              </Grid>
            </Grid.Column>
            <Grid.Column>
              <Header as="h4">Selected Principal</Header>
              <Header
                as="h4"
                style={{ marginTop: 0, color: "#686868", fontWeight: 400 }}
              ></Header>
              <Divider />
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
