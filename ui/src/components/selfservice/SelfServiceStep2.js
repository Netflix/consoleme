import _ from "lodash";
import React, { Component } from "react";
import {
  Button,
  Divider,
  Form,
  Grid,
  Icon,
  Item,
  Label,
  List,
  Header,
  Segment,
  Message,
} from "semantic-ui-react";
import SelfServiceComponent from "./SelfServiceComponent";
import SelfServiceModal from "./SelfServiceModal.js";
import { arnRegex } from "../../helpers/utils";

// TODO, move this to config file.
const DEFAULT_AWS_SERVICE = "s3";

class SelfServiceStep2 extends Component {
  constructor(props) {
    super(props);
    this.state = {
      service: DEFAULT_AWS_SERVICE,
      activeIndex: 0,
      isError: false,
      isLoading: false,
      isSuccess: false,
      messages: [],
      requestId: null,
      admin_bypass_approval_enabled: this.props.admin_bypass_approval_enabled,
      export_to_terraform_enabled: this.props.export_to_terraform_enabled,
      admin_auto_approve: false,
      policy_name: "",
      modal_policy: "",
      addPolicyMessage: false,
    };

    this.inlinePolicyEditorRef = React.createRef();
  }

  updateStatement(value) {
    this.props.updatePolicy(value);
  }

  updatePolicyMessage(value) {
    this.setState({
      addPolicyMessage: value,
    });
  }

  handleServiceTypeChange(e, { value }) {
    this.setState({
      service: value,
    });
  }

  handleExtraActionsAdd(extraAction) {
    const { extraActions } = this.props;
    extraActions.push.apply(extraActions, extraAction);
    this.props.handleExtraActionsUpdate(extraActions);
  }

  handleIncludeAccountsAdd(includeAccount) {
    const { includeAccounts } = this.props;
    includeAccounts.push.apply(includeAccounts, includeAccount);
    this.props.handleIncludeAccountsUpdate(includeAccounts);
  }

  handleExcludeAccountsAdd(excludeAccount) {
    const { excludeAccounts } = this.props;
    excludeAccounts.push.apply(excludeAccounts, excludeAccount);
    this.props.handleExcludeAccountsUpdate(excludeAccounts);
  }

  async handlePermissionAdd(permission) {
    const { role, permissions, updated_policy } = this.props;
    permissions.push(permission);
    const payload = {
      changes: [],
    };
    let editorChange = "";
    if (updated_policy !== "") {
      editorChange = {
        principal: role.principal,
        generator_type: "custom_iam",
        policy: JSON.parse(updated_policy),
      };
    }

    const change = {
      principal: role.principal,
      generator_type: permission.service,
      action_groups: permission.actions,
      condition: permission.condition,
      effect: "Allow",
      ...permission,
    };

    if (this.props.extraActions.length > 0) {
      change["extra_actions"] = [];
      for (const action of this.props.extraActions) {
        change["extra_actions"].push(action.value);
      }
    }
    if (this.props.includeAccounts.length > 0) {
      change["include_accounts"] = [];
      for (const account of this.props.includeAccounts) {
        change["include_accounts"].push(account.value);
      }
    }

    if (this.props.excludeAccounts.length > 0) {
      change["exclude_accounts"] = [];
      for (const account of this.props.excludeAccounts) {
        change["exclude_accounts"].push(account.value);
      }
    }

    delete change.service;
    delete change.actions;

    payload.changes = [change];

    if (editorChange !== "") {
      payload.changes.push(editorChange);
    }

    const response = await this.props.sendRequestCommon(
      payload,
      "/api/v2/generate_changes"
    );

    if (response.status != null && response.status === 400) {
      return this.setState({
        isError: true,
        messages: [response.message],
      });
    }

    if ("changes" in response && response.changes.length > 0) {
      const policy_name = response.changes[0].policy_name;
      const statement = JSON.stringify(
        response.changes[0].policy.policy_document,
        null,
        4
      );
      this.setState({
        custom_statement: statement,
        isError: false,
        messages: [],
        policy_name,
        statement,
      });
      // Let's try to get the policy in advanced policy editor here, and set it here.
      this.updateStatement(statement);
      this.setState(
        {
          service: null,
        },
        () => {
          this.props.handlePermissionsUpdate(permissions);
        }
      );
      // Reset extraActions, includeAccounts, and excludeAccounts
      this.props.handleResetUserChoices();
    }
  }

  handlePermissionRemove(target) {
    const { permissions } = this.props;
    _.remove(permissions, (permission) => _.isEqual(target, permission));
    this.props.handlePermissionsUpdate(permissions);
  }

  getPermissionItems() {
    const { services } = this.props;
    return this.props.permissions.map((permission, idx) => {
      const found = _.find(services, { key: permission.service });
      const serviceName = found.text;
      return (
        <Item key={idx}>
          <Item.Content
            style={{
              paddingLeft: "20px",
              paddingBottom: "20px",
              paddingTop: "20px",
            }}
          >
            {/* // TODO(mrobison): Re-introduce this in V2 when generate_changes addresses removal of permissions.
             <Button
              size="tiny"
              color="red"
              floated="right"
              onClick={this.handlePermissionRemove.bind(this, permission)}
            >
              Remove
            </Button> */}
            <Item.Header style={{ fontSize: "1.5em", marginBottom: "1em" }}>
              <Grid.Row>{serviceName}</Grid.Row>
            </Item.Header>
            <Item.Meta>
              <Grid columns={2}>
                <List relaxed style={{ width: "100%", marginTop: ".25em" }}>
                  {Object.keys(permission).map((key) => {
                    if (
                      key === "actions" ||
                      key === "service" ||
                      key === "condition"
                    ) {
                      return null;
                    }
                    return (
                      <List.Item style={{ marginRight: "0px" }}>
                        <Grid.Row
                          style={{ display: "flex", fontSize: "0.8750em" }}
                        >
                          {key === "resource_arn" ? (
                            <>
                              <Grid.Column
                                style={{ width: "75%", display: "flex" }}
                              >
                                <Icon
                                  name="users"
                                  style={{
                                    fontSize: "1.5em",
                                    color: "black",
                                    marginRight: ".75em",
                                  }}
                                />
                                <Header as={"h5"}>RESOURCE</Header>
                              </Grid.Column>
                              <Grid.Column style={{ width: "100%" }}>
                                {typeof permission[key] === "string"
                                  ? permission[key]
                                  : permission[key].join(",")}
                              </Grid.Column>
                            </>
                          ) : null}
                        </Grid.Row>
                        <Grid.Row
                          style={{
                            display: "flex",
                            fontSize: "0.8750em",
                            marginTop: ".15em",
                          }}
                        >
                          {key === "bucket_prefix" ? (
                            <>
                              <Grid.Column
                                style={{ width: "75%", display: "flex" }}
                              >
                                <Icon
                                  name="folder open"
                                  style={{
                                    fontSize: "1.5em",
                                    color: "black",
                                    marginRight: ".75em",
                                  }}
                                />
                                <Header as={"h5"}>NAME/PREFIX</Header>
                              </Grid.Column>
                              <Grid.Column style={{ width: "100%" }}>
                                {permission[key]}
                              </Grid.Column>
                            </>
                          ) : null}
                        </Grid.Row>
                      </List.Item>
                    );
                  })}
                </List>
              </Grid>
            </Item.Meta>
            <Item.Extra style={{ display: "flex", marginTop: "1.75em" }}>
              <Grid.Column style={{ width: "70%", display: "flex" }}>
                <Icon
                  name="cogs"
                  rotated={"clockwise"}
                  style={{
                    fontSize: "1.5em",
                    marginLeft: "-4px",
                    color: "black",
                    marginRight: ".75em",
                  }}
                />
                <Header
                  as={"h5"}
                  style={{ paddingTop: ".25em", marginTop: "0px" }}
                >
                  GROUP ACTIONS
                </Header>
              </Grid.Column>
              <Grid.Column style={{ width: "100%" }}>
                {permission.actions != null
                  ? permission.actions.map((action) => {
                      const actionDetail = _.find(found.actions, {
                        name: action,
                      });
                      return (
                        <Label
                          as="a"
                          style={{
                            border: "1px solid #babbbc",
                            backgroundColor: "#ffffff",
                            color: "rgba(0,0,0,.85)",
                            fontSize: "0.8750em",
                            lineHeight: "0.750em",
                            minWidth: "5em",
                            maxWidth: "7em",
                            textAlign: "center",
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                          }}
                        >
                          {actionDetail.text}
                        </Label>
                      );
                    })
                  : null}
              </Grid.Column>
            </Item.Extra>
          </Item.Content>
        </Item>
      );
    });
  }

  render() {
    const { config, role, services, updated_policy, permissions } = this.props;
    const { messages, service } = this.state;

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

    const policyMessage =
      this.state.addPolicyMessage === true ? (
        <Message info color="blue">
          <Message.Header>Advanced Editor has been modified</Message.Header>
          <p>
            Your changes made in the Advanced Editor will override these
            permissions.
          </p>
        </Message>
      ) : null;

    // TODO(ccastrapel): The false condition for headerMessage needs to be updated. Maybe the backend should just
    // provide a link to the policy editor for a given principal, or the repository location?
    const match = arnRegex.exec(role?.arn);
    let resourceType = null;
    if (match) resourceType = match?.groups?.resourceType;
    const headerMessage = role.arn ? (
      <Header>
        Add Permission
        <Header.Subheader>
          Please add permissions to your {resourceType}&nbsp;
          <a
            href={`/policies/edit/${role.account_id}/iam${resourceType}/${role.name}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            {role.arn}
          </a>
          .&nbsp; You can also select multiple permissions.
        </Header.Subheader>
      </Header>
    ) : (
      <Header>
        Modify Policy
        <Header.Subheader>
          Please choose the actions you wish to add.
        </Header.Subheader>
      </Header>
    );

    return (
      <Segment>
        <Grid columns={2} divided>
          <Grid.Row>
            <Grid.Column>
              <Header>{headerMessage}</Header>
              <Form>
                <Form.Select
                  value={service}
                  label="Select Desired Permissions"
                  onChange={this.handleServiceTypeChange.bind(this)}
                  options={services}
                  placeholder="Choose One"
                  required
                />
              </Form>
              <Divider />
              {service != null ? (
                <SelfServiceComponent
                  key={service}
                  config={config}
                  role={role}
                  service={service}
                  updated_policy={updated_policy}
                  updatePermission={this.handlePermissionAdd.bind(this)}
                  updateExtraActions={this.handleExtraActionsAdd.bind(this)}
                  updateIncludeAccounts={this.handleIncludeAccountsAdd.bind(
                    this
                  )}
                  updateExcludeAccounts={this.handleExcludeAccountsAdd.bind(
                    this
                  )}
                  {...this.props}
                />
              ) : null}
            </Grid.Column>
            <Grid.Column>
              <Header>
                Your Permissions
                <Header.Subheader>
                  The list of permissions you have added in this request. Please
                  use the Advanced Editor to remove permissions.
                </Header.Subheader>
              </Header>
              <Item.Group divided>{this.getPermissionItems()}</Item.Group>
              {policyMessage}
              <Header>
                {permissions.length === 0 ? (
                  <span>
                    You must add at least one resource to continue or choose{" "}
                  </span>
                ) : (
                  <span>Choose </span>
                )}
                <SelfServiceModal
                  key={service}
                  config={config}
                  role={role}
                  service={service}
                  updatePolicyMessage={this.updatePolicyMessage.bind(this)}
                  updateStatement={this.updateStatement.bind(this)}
                  updateExtraActions={this.handleExtraActionsAdd.bind(this)}
                  updateIncludeAccounts={this.handleIncludeAccountsAdd.bind(
                    this
                  )}
                  updateExcludeAccounts={this.handleExcludeAccountsAdd.bind(
                    this
                  )}
                  {...this.props}
                />{" "}
                to override permissions.
              </Header>
              <div style={{ textAlign: "center" }}>
                <Button
                  style={{ fontSize: "1.25em", width: "11em", height: "3.5em" }}
                  positive
                  onClick={() => {
                    this.props.handleStepClick("next");
                  }}
                >
                  Next
                </Button>
              </div>
              {messagesToShow}
            </Grid.Column>
          </Grid.Row>
        </Grid>
      </Segment>
    );
  }
}

export default SelfServiceStep2;
