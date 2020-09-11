import React, { Component } from "react";
import PropTypes from "prop-types";
import { Dropdown, Menu, Image } from "semantic-ui-react";
import { NavLink } from "react-router-dom";

class ConsoleMeHeader extends Component {
  static defaultProps = {
    userSession: {},
  };

  generateGroupsDropDown() {
    if (this.props.userSession.pages.groups.enabled === true) {
      return (
        <Dropdown text="Group Access" pointing className="link item">
          <Dropdown.Menu>
            <Dropdown.Item>Request Access</Dropdown.Item>
            <Dropdown.Item>Groups</Dropdown.Item>
            <Dropdown.Item>Users</Dropdown.Item>
            <Dropdown.Item>Pending</Dropdown.Item>
          </Dropdown.Menu>
        </Dropdown>
      );
    }
    return null;
  }

  generatePoliciesDropDown() {
    if (this.props.userSession.pages.policies.enabled === true) {
      // TODO: UIREFACTOR: Remove V2 references when this new UI is done
      return (
        <Dropdown text="Roles and Policies" pointing className="link item">
          <Dropdown.Menu>
            <Dropdown.Item as={NavLink} to="/catalog">
              Catalog
            </Dropdown.Item>
            <Dropdown.Item as={NavLink} to="/ui/policies">
              Policies
            </Dropdown.Item>
            <Dropdown.Item as={NavLink} to="/ui/selfservice">
              Self Service Permissions
            </Dropdown.Item>
            <Dropdown.Item as={NavLink} to="/ui/apihealth">
              API Health
            </Dropdown.Item>
          </Dropdown.Menu>
        </Dropdown>
      );
    }
    return null;
  }

  generateAdvancedDropDown() {
    if (this.props.userSession.pages.config.enabled === true) {
      return (
        <Dropdown text="Advanced" pointing className="link item">
          <Dropdown.Menu>
            <Dropdown.Item>Audit</Dropdown.Item>
            <Dropdown.Item>Config</Dropdown.Item>
          </Dropdown.Menu>
        </Dropdown>
      );
    }
    return null;
  }

  getAvatarImage() {
    if (this.props.userSession.employee_photo_url) {
      return (
        <div>
          <Image src={this.props.userSession.employee_photo_url} avatar />
          <span>{this.props.userSession.user}</span>
        </div>
      );
    }
    return null;
  }

  render() {
    if (!this.props.userSession) {
      return null;
    }

    return (
      <Menu pointing secondary>
        <Menu.Item name={"AWS Console Roles"} active={true} as={NavLink} to="/">
          AWS Console Roles
        </Menu.Item>
        {this.generateGroupsDropDown()}
        {this.generatePoliciesDropDown()}
        {this.generateAdvancedDropDown()}
        <Menu.Menu position="right">
          <Menu.Item name="logout">{this.getAvatarImage()}</Menu.Item>
        </Menu.Menu>
      </Menu>
    );
  }
}

ConsoleMeHeader.propType = {
  userSession: PropTypes.object,
};

export default ConsoleMeHeader;
