// import axios from 'axios';
import _ from "lodash";
import React, { Component } from "react";
import PropTypes from "prop-types";
import {
  Button,
  Divider,
  Grid,
  Icon,
  Label,
  List,
  Header,
  Search,
  Segment,
} from "semantic-ui-react";

import "./Main.css";

const ARN_REGEX = /^arn:aws:iam::(?<account>\d+):role\/(?<role>.+)$/;
const PER_USER_ROLE_REGEX = /^cm_.+_N$/;
const ROLE_REGEX = /(?<accountName>.+)_(?<roleName>.+)$/;
const SIGNOUT_URL = "https://signin.aws.amazon.com/oauth?Action=logout";

const resultRenderer = ({ title, account, description }) => (
  <div>
    <Label>
      account
      <Label.Detail>{account}</Label.Detail>
      <Label.Detail>{title}</Label.Detail>
    </Label>
    <Label>
      role name
      <Label.Detail>{description}</Label.Detail>
    </Label>
  </div>
);

class ConsoleMeMain extends Component {
  state = {
    _xsrf: null,
    isLoading: true,
    signOut: false,
    eligibleRoles: [],
    selectedAccount: "",
    selectedRole: {
      account: null,
      arn: null,
      role: null,
      userRole: {
        accountName: null,
        roleName: null,
        perUserRole: null,
      },
    },
    searchLoading: false,
    searchResults: [],
    searchValue: "",
  };

  componentDidMount() {
    fetch("/api/v1/roles").then((resp) => {
      resp.json().then((resp) => {
        const { eligible_roles, _xsrf } = resp;
        const eligibleRoles = eligible_roles.reduce((roles, arn) => {
          const arnMatch = arn.match(ARN_REGEX);
          if (!arnMatch) {
            return;
          }

          const { role, account } = arnMatch.groups;
          const perUserRole = PER_USER_ROLE_REGEX.test(role);
          const userRole = {
            perUserRole,
            accountName: account,
            roleName: role,
          };
          if (!perUserRole) {
            const match = role.match(ROLE_REGEX);
            const { accountName, roleName } = match.groups;
            userRole["accountName"] = accountName;
            userRole["roleName"] = roleName;
          }
          roles.push({
            account,
            arn,
            userRole,
            role,
          });

          return roles;
        }, []);

        this.setState({
          eligibleRoles,
          _xsrf,
          isLoading: false,
        });
      });
    });
  }

  handleResultSelect = (e, { result }) => {
    this.setState({
      selectedAccount: result.account,
      searchLoading: false,
    });
  };

  handleSearchChange = (e, { value }) => {
    this.setState(
      {
        searchLoading: true,
        searchValue: value,
      },
      () => {
        if (this.state.searchValue.length < 1) {
          this.setState({
            searchLoading: false,
            searchValue: "",
            searchResults: [],
            selectedAccount: "",
          });
        }
        const re = new RegExp(_.escapeRegExp(this.state.searchValue), "i");
        const isMatch = (role) => re.test(role.arn);
        const searchableRoles = this.state.eligibleRoles.map((role) => {
          return {
            account: role.account,
            arn: role.arn,
            title: role.userRole.accountName,
            description: role.userRole.roleName,
          };
        });
        this.setState({
          searchLoading: false,
          searchResults: _.filter(searchableRoles, isMatch),
          selectedAccount: "",
        });
      }
    );
  };

  handleRoleDetailClick = (selectedRole, event) => {
    this.setState({
      selectedRole,
    });
  };

  handleSignInClick = (selectedRole, event) => {
    event.preventDefault();
    // we need to first sign-out from logged in console.
    this.setState({
      signOut: true, // once this is set iframe is notified to use sign out url
      isLoading: true,
      selectedRole,
    });
  };

  handleSignIn = (event) => {
    event.preventDefault();
    // set recent roles local storage.
    this.props.setRecentRole(this.state.selectedRole.role);

    // Once we sign out from the console, use the new credential to sign-in
    fetch("/", {
      method: "POST",
      headers: {
        "X-Xsrftoken": this.state._xsrf,
      },
      body: JSON.stringify({
        role: this.state.selectedRole.arn,
        region: "us-east-1",
        redirect: "redirect",
      }),
    }).then(
      (resp) => {
        if (resp.status != 200) {
          console.error(resp.status, resp.statusText);
          return;
        }
        resp.json().then((json) => {
          // Redirect user to AWS Console.
          window.location.assign(json.redirect);
        });
      },
      (error) => {
        console.error(error);
      }
    );
  };

  createEligibleRoleLists() {
    const filteredRoles = this.state.selectedAccount
      ? _.filter(
          this.state.eligibleRoles,
          (role) => role.account == this.state.selectedAccount
        )
      : this.state.eligibleRoles;

    const eligibleRoles = _.sortBy(filteredRoles, ["role"]).map((roleInfo) => {
      const { arn, userRole } = roleInfo;
      return (
        <List.Item
          active={userRole.roleName == this.state.selectedRole.role}
          key={arn}
        >
          <List.Content
            floated="left"
            onClick={this.handleSignInClick.bind(this, roleInfo)}
          >
            <List.Header>
              <Label as="a" color={userRole.perUserRole ? "orange" : "blue"}>
                <Icon name="sign-in" />
                {userRole.accountName}
                <Label.Detail>{userRole.roleName}</Label.Detail>
              </Label>
            </List.Header>
          </List.Content>
          <List.Content
            floated="right"
            onClick={this.handleRoleDetailClick.bind(this, roleInfo)}
          >
            <Label as="a">Info</Label>
          </List.Content>
        </List.Item>
      );
    });

    return eligibleRoles;
  }

  render() {
    const {
      isLoading,
      searchLoading,
      searchValue,
      searchResults,
      selectedRole,
    } = this.state;

    return (
      <Segment loading={isLoading} placeholder>
        <Grid columns={2} stackable textAlign="center">
          <Grid.Row verticalAlign="top">
            <Grid.Column>
              <Header icon>
                <Icon name="sign-in" />
                Sign-In Account
              </Header>
              <Search
                fluid
                loading={searchLoading}
                onResultSelect={this.handleResultSelect}
                onSearchChange={_.debounce(this.handleSearchChange, 500, {
                  leading: true,
                })}
                results={searchResults}
                value={searchValue}
                placeholder="search account..."
                resultRenderer={resultRenderer}
              />
              <Segment textAlign="left">
                <List selection verticalAlign="middle">
                  {this.createEligibleRoleLists()}
                </List>
              </Segment>
            </Grid.Column>
            <Grid.Column>
              <Header icon>
                <Icon name="settings" />
                Sign-In Details
                <Header.Subheader>
                  Check your sign-in settings and set preferences.
                </Header.Subheader>
              </Header>
              <Segment.Group>
                <Segment textAlign="left">
                  <Header as="h3" textAlign="left">
                    Account Details
                    <Header.Subheader>
                      the account you are sign-in details
                    </Header.Subheader>
                  </Header>
                  <Grid columns={1} relaxed="very">
                    <Grid.Column>
                      <div>
                        <b>ID</b>
                        <br />
                        {selectedRole.account}
                      </div>
                      <br />
                      <div>
                        <b>Name</b>
                        <br />
                        {selectedRole.userRole.accountName}
                      </div>
                    </Grid.Column>
                  </Grid>
                </Segment>
                <Segment textAlign="left">
                  <Header as="h3" textAlign="left">
                    Role Details
                    <Header.Subheader>
                      the sign-in role and its associated permissions details
                    </Header.Subheader>
                  </Header>
                  <Grid columns={1} relaxed="very">
                    <Grid.Column>
                      <div>
                        <b>Arn</b>
                        <br />
                        {selectedRole.arn ? (
                          <a href="#">{selectedRole.arn}</a>
                        ) : null}
                      </div>
                      <br />
                      <div>
                        <b>Permissions</b>
                        <br />
                        {selectedRole.role ? (
                          <a href="#">
                            {selectedRole.userRole.roleName + ".json"}
                          </a>
                        ) : null}
                      </div>
                      <br />
                      <div>
                        <b>Per-user Role</b>
                        &nbsp;
                        <Icon name="question circle outline" />
                        <br />
                        {selectedRole.userRole.perUserRole != null
                          ? selectedRole.userRole.perUserRole
                            ? "enabled"
                            : "disabled"
                          : null}
                      </div>
                      <br />
                      <div>
                        <b>AWS Credentials</b>
                        <br />
                        {selectedRole.arn ? (
                          <Label>
                            newt --app-type awscreds refresh -r{" "}
                            {selectedRole.arn}
                          </Label>
                        ) : null}
                      </div>
                    </Grid.Column>
                  </Grid>
                </Segment>
                <Segment>
                  {this.state.selectedRole.userRole.perUserRole != null ? (
                    <Button
                      primary
                      content="Enable Per-User Role"
                      disabled={this.state.selectedRole.userRole.perUserRole}
                    />
                  ) : null}
                </Segment>
              </Segment.Group>
            </Grid.Column>
          </Grid.Row>
        </Grid>
        <Divider vertical></Divider>
        <iframe
          className="logOutIframe"
          onLoad={this.handleSignIn}
          src={this.state.signOut ? SIGNOUT_URL : null}
        />
      </Segment>
    );
  }
}

ConsoleMeMain.propType = {
  setRecentRole: PropTypes.func,
};

export default ConsoleMeMain;
