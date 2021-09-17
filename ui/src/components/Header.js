import React, { useState } from "react";
import {
  Button,
  Dropdown,
  Menu,
  Image,
  Label,
  Message,
} from "semantic-ui-react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../auth/AuthProviderDefault";
import ReactMarkdown from "react-markdown";
import SettingsModal from "./SettingsModal";
import { NotificationsModal } from "./notifications/Notifications";
import { useNotifications } from "./hooks/notifications";

const ConsoleMeHeader = () => {
  const { user } = useAuth();
  const {
    notifications,
    unreadNotificationCount,
    GetAndSetNotifications,
  } = useNotifications();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);

  const generatePoliciesDropDown = () => {
    const canCreateRoles = user?.authorization?.can_create_roles;
    if (user?.pages?.policies?.enabled === true) {
      return (
        <Dropdown text="Roles and Policies" pointing className="link item">
          <Dropdown.Menu>
            <Dropdown.Item as={NavLink} to="/policies">
              Policies
            </Dropdown.Item>
            <Dropdown.Item as={NavLink} to="/selfservice">
              Self Service Permissions
            </Dropdown.Item>
            <Dropdown.Item as={NavLink} to="/requests">
              All Policy Requests
            </Dropdown.Item>
            {canCreateRoles ? (
              <Dropdown.Item as={NavLink} to="/create_role">
                Create Role
              </Dropdown.Item>
            ) : null}
          </Dropdown.Menu>
        </Dropdown>
      );
    }
    return null;
  };

  const generateAdvancedDropDown = () => {
    if (user?.pages?.config?.enabled === true) {
      return (
        <Dropdown text="Advanced" pointing className="link item">
          <Dropdown.Menu>
            <Dropdown.Item as={NavLink} to="/config">
              Config
            </Dropdown.Item>
          </Dropdown.Menu>
        </Dropdown>
      );
    }
    return null;
  };

  const openNotifications = () => {
    setNotificationsOpen(true);
  };

  const closeNotifications = () => {
    setNotificationsOpen(false);
  };

  const openSettings = () => {
    setSettingsOpen(true);
  };

  const closeSettings = () => {
    setSettingsOpen(false);
  };

  const getNotifications = () => {
    if (!user?.site_config?.notifications?.enabled) {
      return;
    }

    return (
      <>
        <Button circular icon="bell" color="red" onClick={openNotifications} />
        {unreadNotificationCount > 0 ? (
          <Label circular size="tiny" color="orange">
            {unreadNotificationCount}
          </Label>
        ) : null}
      </>
    );
  };

  const getAvatarImage = () => {
    let dropdownOptions = [
      {
        key: user.user,
        text: user.user,
        value: user.user,
        image: { avatar: true, src: user?.employee_photo_url },
      },
      {
        key: "settings",
        text: "Settings",
        onClick: openSettings,
      },
    ];
    if (user?.can_logout) {
      dropdownOptions.push({
        key: "logout",
        as: NavLink,
        to: "/logout",
        text: "Logout",
      });
    }
    return (
      <Dropdown
        inline
        options={dropdownOptions}
        defaultValue={dropdownOptions[0].value}
        icon={null}
      />
    );
  };

  const headerMessage = () => {
    if (
      user?.pages?.header?.custom_header_message_title ||
      user?.pages?.header?.custom_header_message_text
    ) {
      const headerTitle =
        user?.pages?.header?.custom_header_message_title || "";
      const headerText = user?.pages?.header?.custom_header_message_text || "";
      if (user?.pages?.header?.custom_header_message_route) {
        const re = new RegExp(user.pages.header.custom_header_message_route);
        if (!re.test(window.location.pathname)) {
          return null;
        }
      }
      return (
        <Message
          warning
          style={{ marginTop: "6em", marginLeft: "18em", marginBottom: "0em" }}
        >
          {}
          <Message.Header>{headerTitle}</Message.Header>
          <ReactMarkdown linkTarget="_blank" children={headerText} />
        </Message>
      );
    }
    return null;
  };

  return (
    <>
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
          href="/"
        >
          <Image
            size="mini"
            src="/images/logos/logo192.png"
            style={{ marginRight: "1.5em" }}
          />
          ConsoleMe
        </Menu.Item>
        <Menu.Menu position="left">
          <Menu.Item active={false} exact as={NavLink} name="roles" to="/">
            AWS Console Roles
          </Menu.Item>
          {generatePoliciesDropDown()}
          {generateAdvancedDropDown()}
        </Menu.Menu>
        <Menu.Menu position="right">
          <Menu.Item>{getAvatarImage()}</Menu.Item>
          <Menu.Item>{getNotifications()}</Menu.Item>
        </Menu.Menu>
      </Menu>
      {headerMessage()}
      <SettingsModal isOpen={settingsOpen} closeSettings={closeSettings} />
      <NotificationsModal
        isOpen={notificationsOpen}
        closeNotifications={closeNotifications}
        notifications={notifications}
        GetAndSetNotifications={GetAndSetNotifications}
      />
    </>
  );
};

export default ConsoleMeHeader;
