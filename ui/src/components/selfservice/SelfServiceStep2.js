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
    };

    this.inlinePolicyEditorRef = React.createRef();
  }

  updateStatement(value) {
    this.props.updatePolicy(value);
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
      extra_actions: ["s3:get*"],
      effect: "Allow",
      ...permission,
    };
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
    }
  }

  handlePermissionRemove(target) {
    const { permissions } = this.props;
    _.remove(permissions, (permission) => _.isEqual(target, permission));
    this.props.handlePermissionsUpdate(permissions);
  }

  getPermissionItems() {
    const { config, services } = this.props;
    return this.props.permissions.map((permission, idx) => {
      const found = _.find(services, { key: permission.service });
      const serviceName = found.text;
      const { inputs } = config.permissions_map[found.key];
      return (
        <Item key={idx}>
          <Item.Content>
            <Item.Header>{serviceName}</Item.Header>
            <Item.Meta>
              <List relaxed>
                {Object.keys(permission).map((key) => {
                  if (
                    key === "actions" ||
                    key === "service" ||
                    key === "condition"
                  ) {
                    return null;
                  }
                  const inputConfig = _.find(inputs, { name: key });
                  return (
                    <List.Item>
                      <Grid.Row style={{display: "flex"}}>
                        {key === "resource_arn" ?
                           <>
                           <Icon name="users" /> <Header as={"h5"}>RESOURCE</Header>{permission[key]}
                           </>
                           : null}
                      </Grid.Row>
                      <Grid.Row style={{display: "flex"}}>
                        {key === "bucket_prefix" ?
                           <>
                           <Icon name="folder open" /> <Header as={"h5"}>NAME/PREFIX</Header>{permission[key]}
                           </>
                           :
                           null}
                      </Grid.Row>
                    </List.Item>
                  );
                })}
              </List>
            </Item.Meta>
            <Item.Extra>
              <Button
                size="tiny"
                color="red"
                floated="right"
                onClick={this.handlePermissionRemove.bind(this, permission)}
              >
                Remove
                <Icon name="right close" />
              </Button>
              <Icon name="cogs" rotated={"clockwise"} className={"actions"}/>
              {permission.actions != null
                ? permission.actions.map((action) => {
                    const actionDetail = _.find(found.actions, {
                      name: action,
                    });
                    return (
                      <Label as="a"
                             style={{ border: "1px solid #babbbc", backgroundColor: "#ffffff", color: "rgba(0,0,0,.85)"}}>
                        {actionDetail.text}
                      </Label>
                    );
                  })
                : null}
            </Item.Extra>
          </Item.Content>
        </Item>
      );
    });
  }

  render() {
    const { config, role, services, updated_policy } = this.props;
    const { service } = this.state;
    const { messages } = this.state;

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

    // TODO(ccastrapel): The false condition for headerMessage needs to be updated. Maybe the backend should just
    // provide a link to the policy editor for a given principal, or the repository location?
    const headerMessage = role.arn ? (
      <Header>
        Add Permission
        <Header.Subheader>
          Please add permissions to your role&nbsp;
          <a
            href={`/policies/edit/${role.account_id}/iamrole/${role.name}`}
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
          You can choose the resource(s) you wish to modify and the actions you
          wish to add. Advanced options include specified actions, include and
          exclude accounts.
          <a
            href={`/policies/edit/${role.account_id}/iamrole/${role.owner}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            {role.resource}
          </a>
          .&nbsp; You can also select multiple permissions.
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
                  The list of permission you have added in this request.
                </Header.Subheader>
              </Header>
              <Divider />
              <Item.Group divided>{this.getPermissionItems()}</Item.Group>
              <Divider />
              <Header>
                You must add at least one resource to continue or choose{" "}
                <SelfServiceModal
                  key={service}
                  config={config}
                  role={role}
                  service={service}
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
              <div style={{textAlign: "center"}}>
                <Button
                 size="massive"
                 positive
                 onClick={this.props.handleStepClick.bind(this, "next")}
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
