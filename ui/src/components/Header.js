import React, { useEffect } from "react";
import { Dropdown, Menu, Image } from "semantic-ui-react";
import { NavLink } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

const ConsoleMeHeader = () => {
  const { user } = useAuth();

  if (!user) {
    return null;
  }

  const generatePoliciesDropDown = () => {
    if (user.pages.policies.enabled === true) {
      return (
        <Dropdown text="Roles and Policies" pointing className="link item">
          <Dropdown.Menu>
            <Dropdown.Item as={NavLink} to="/ui/catalog">
              Service Catalog
            </Dropdown.Item>
            <Dropdown.Item as={NavLink} to="/ui/policies">
              Policies
            </Dropdown.Item>
            <Dropdown.Item as={NavLink} to="/ui/selfservice">
              Self Service Permissions
            </Dropdown.Item>
            <Dropdown.Item as={NavLink} to="/ui/requests">
              All Policy Requests
            </Dropdown.Item>
          </Dropdown.Menu>
        </Dropdown>
      );
    }
    return null;
  };

  const generateAdvancedDropDown = () => {
    if (user.pages.config.enabled === true) {
      return (
        <Dropdown text="Advanced" pointing className="link item">
          <Dropdown.Menu>
            <Dropdown.Item as={NavLink} to="/ui/config">
              Config
            </Dropdown.Item>
          </Dropdown.Menu>
        </Dropdown>
      );
    }
    return null;
  };

  const getAvatarImage = () => {
    if (user.employee_photo_url) {
      return (
        <Image
          alt={user.user}
          avatar
          src={user.employee_photo_url}
          title={user.user}
        />
      );
    }
    return null;
  };

  return (
    <Menu
      color="red"
      fixed="top"
      inverted
      style={{
        height: "72px",
        marginBottom: "0",
      }}
    >
      <Menu.Item
        as="a"
        header
        name="header"
        style={{
          fontSize: "20px",
          textTransform: "uppercase",
          width: "240px",
        }}
        href="/ui/"
      >
        <Image
          size="mini"
          src="/static2/images/logo192.png"
          style={{ marginRight: "1.5em" }}
        />
        ConsoleMe
      </Menu.Item>
      <Menu.Menu position="left">
        <Menu.Item active={false} exact as={NavLink} name={"roles"} to="/ui/">
          AWS Console Roles
        </Menu.Item>
        {generatePoliciesDropDown()}
        {generateAdvancedDropDown()}
      </Menu.Menu>
      <Menu.Menu position="right">
        <Menu.Item>{getAvatarImage()}</Menu.Item>
      </Menu.Menu>
    </Menu>
  );
};

export default ConsoleMeHeader;
