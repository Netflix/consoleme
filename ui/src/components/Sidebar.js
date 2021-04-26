import React, { useEffect, useState } from "react";
import { Label, Header, Icon, Image, Menu } from "semantic-ui-react";
import { parseLocalStorageCache } from "../helpers/utils";
import { NavLink } from "react-router-dom";
import { useAuth } from "../auth/AuthProviderDefault";

const localStorageRecentRolesKey = "consoleMeLocalStorage";

const listRecentRoles = (recentRoles, user) => {
  const arnRegex = /^arn:aws:iam::(\d{12}):role\/(.+)$/;
  return recentRoles.map((role) => {
    const match = role.match(arnRegex);
    if (!match) {
      return null;
    }
    const [, accountNumber, roleName] = match;
    const accountName = user?.accounts[accountNumber];
    return (
      <Menu.Item as={NavLink} name={role} key={role} to={"/role/" + role}>
        <Header
          color="blue"
          style={{
            fontSize: "14px",
          }}
        >
          <Header.Content>
            {accountName ? accountName : accountNumber}
            <Header.Subheader
              style={{
                fontSize: "14px",
                color: "grey",
              }}
            >
              {roleName}
            </Header.Subheader>
          </Header.Content>
        </Header>
      </Menu.Item>
    );
  });
};

const ConsoleMeSidebar = () => {
  const { user } = useAuth();
  const [siteConfig, setSiteConfig] = useState({});
  const recentRoles = parseLocalStorageCache(localStorageRecentRolesKey);

  useEffect(() => {
    if (!user?.site_config) {
      return;
    }
    setSiteConfig(user.site_config);
  }, [user]);

  const {
    consoleme_logo,
    documentation_url,
    security_logo,
    security_url,
    support_contact,
    support_chat_url,
  } = siteConfig;

  return (
    <Menu
      color="black"
      fixed="left"
      inverted
      vertical
      style={{
        paddingTop: "82px",
        width: "240px",
        zIndex: "100",
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
          justifyContent: "space-between",
          overflowY: "auto",
        }}
      >
        <div>
          <Menu.Item>
            <Label>{recentRoles.length}</Label>
            <Menu.Header>Recent Roles</Menu.Header>
            <Menu.Menu>{listRecentRoles(recentRoles, user)}</Menu.Menu>
          </Menu.Item>
          <Menu.Item>
            <Menu.Header>Help</Menu.Header>
            <Menu.Menu>
              {documentation_url ? (
                <Menu.Item
                  as="a"
                  name="documentation"
                  href={documentation_url}
                  rel="noopener noreferrer"
                  target="_blank"
                  style={{
                    fontSize: "14px",
                  }}
                >
                  <Icon name="file" />
                  Documentation
                </Menu.Item>
              ) : null}
              {support_contact ? (
                <Menu.Item
                  as="a"
                  name="email"
                  href={"mailto:" + support_contact}
                  rel="noopener noreferrer"
                  target="_blank"
                  style={{
                    fontSize: "14px",
                  }}
                >
                  <Icon name="send" />
                  Email us
                </Menu.Item>
              ) : null}
              {support_chat_url ? (
                <Menu.Item
                  as="a"
                  name="slack"
                  href={support_chat_url || "/"}
                  rel="noopener noreferrer"
                  target="_blank"
                  style={{
                    fontSize: "14px",
                  }}
                >
                  <Icon name="slack" />
                  Chat with us
                </Menu.Item>
              ) : null}
            </Menu.Menu>
          </Menu.Item>
        </div>
        <div>
          <Menu.Menu>
            <Menu.Item>
              {consoleme_logo && (
                <a href={"/"} rel="noopener noreferrer" target="_blank">
                  <Image
                    style={{
                      height: "250px",
                      margin: "auto",
                    }}
                    src={consoleme_logo}
                  />
                </a>
              )}
              <br />
              {security_logo && (
                <a
                  href={security_url || "/"}
                  rel="noopener noreferrer"
                  target="_blank"
                >
                  <Image size="medium" src={security_logo} />
                </a>
              )}
            </Menu.Item>
          </Menu.Menu>
        </div>
      </div>
    </Menu>
  );
};

export default ConsoleMeSidebar;
