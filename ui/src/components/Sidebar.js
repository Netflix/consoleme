import React, { useEffect, useState } from "react";
import { Label, Icon, Image, Menu } from "semantic-ui-react";
import { parseLocalStorageCache, sendRequestCommon } from "../helpers/utils";
import { NavLink } from "react-router-dom";
import { useAuth } from "../auth/AuthProviderDefault";

const localStorageRecentRolesKey = "consoleMeLocalStorage";

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

  const { documentation_url, support_contact, support_chat_url } = siteConfig;

  return (
    <Menu
      color="black"
      fixed="left"
      inverted
      vertical
      style={{
        paddingTop: "10px",
        width: "240px",
        marginTop: "72px",
        minHeight: "700px",
      }}
    >
      <Menu.Item>
        <Label>{recentRoles.length}</Label>
        <Menu.Header>Recent Roles</Menu.Header>
        <Menu.Menu>
          {recentRoles.map((role) => {
            const roleName = role.split("/").pop();
            return (
              <Menu.Item
                as={NavLink}
                name={role}
                key={role}
                to={"/role/" + role}
              >
                {roleName}
              </Menu.Item>
            );
          })}
        </Menu.Menu>
      </Menu.Item>
      <Menu.Item>
        <Menu.Header>Help</Menu.Header>
        <Menu.Menu>
          <Menu.Item
            as="a"
            name="documentation"
            href={documentation_url || ""}
            rel="noopener noreferrer"
            target="_blank"
          >
            <Icon name="file" />
            Documentation
          </Menu.Item>
          <Menu.Item
            as="a"
            name="email"
            href={support_contact ? "mailto:" + support_contact : "/"}
            rel="noopener noreferrer"
            target="_blank"
          >
            <Icon name="send" />
            Email us
          </Menu.Item>
          <Menu.Item
            as="a"
            name="slack"
            href={support_chat_url || "/"}
            rel="noopener noreferrer"
            target="_blank"
          >
            <Icon name="slack" />
            Find us on Slack
          </Menu.Item>
        </Menu.Menu>
      </Menu.Item>
      <Menu.Menu
        style={{
          position: "absolute",
          bottom: "70px",
          left: "0",
        }}
      >
        <Menu.Item>
          <Image size="medium" src="/static/ui/images/logos/quarantine/1.png" />
          <br />
          <Image
            size="medium"
            src="/static/ui/images/netflix-security-dark-bg-tight.svg"
          />
        </Menu.Item>
      </Menu.Menu>
    </Menu>
  );
};

export default ConsoleMeSidebar;
