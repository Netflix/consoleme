import React, { useEffect } from 'react';
import {
    Dropdown,
    Menu,
    Image,
} from 'semantic-ui-react';
import {NavLink} from 'react-router-dom'

import { useAuth } from "../auth/AuthContext";


const ConsoleMeHeader = () => {
    const { authState } = useAuth();
    const { userInfo } = authState;

    if (!authState.isAuthenticated || !userInfo) {
        return null;
    }

    const generateGroupsDropDown = () => {
        if (userInfo.pages.groups.enabled === true) {
            return (
                <Dropdown
                    text='Group Access'
                    pointing
                    className='link item'
                >
                    <Dropdown.Menu>
                        <Dropdown.Item>
                            Request Access
                        </Dropdown.Item>
                        <Dropdown.Item>
                            Groups
                        </Dropdown.Item>
                        <Dropdown.Item>
                            Users
                        </Dropdown.Item>
                        <Dropdown.Item>
                            Pending
                        </Dropdown.Item>
                    </Dropdown.Menu>
                </Dropdown>
            );
        }
        return null;
    }

    const generatePoliciesDropDown = () => {
        if (userInfo.pages.policies.enabled === true) {
            return (
                <Dropdown
                    text="Roles and Policies"
                    pointing
                    className="link item"
                >
                    <Dropdown.Menu>
                        <Dropdown.Item
                            as={NavLink}
                            to="/ui/catalog"
                        >
                            Catalog
                        </Dropdown.Item>
                        <Dropdown.Item>
                            Policies
                        </Dropdown.Item>
                        <Dropdown.Item
                            as={NavLink}
                            to="/ui/selfservice"
                        >
                            Self Service Permissions
                        </Dropdown.Item>
                        <Dropdown.Item>
                            API Health
                        </Dropdown.Item>
                    </Dropdown.Menu>
                </Dropdown>
            );
        }
        return null;
    }

    const generateAdvancedDropDown = () => {
        if (userInfo.pages.config.enabled === true) {
            return (
                <Dropdown
                    text="Advanced"
                    pointing
                    className="link item"
                >
                    <Dropdown.Menu>
                        <Dropdown.Item>
                            Audit
                        </Dropdown.Item>
                        <Dropdown.Item>
                            Config
                        </Dropdown.Item>
                    </Dropdown.Menu>
                </Dropdown>
            );
        }
        return null;
    }

    const getAvatarImage = () => {
        if (userInfo.employee_photo_url) {
            return (
                <Image
                    alt={userInfo.user}
                    avatar
                    src={userInfo.employee_photo_url}
                    title={userInfo.user}
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
                marginBottom: "0"
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
                    size='mini'
                    src='/static2/images/logo192.png'
                    style={{ marginRight: '1.5em' }}
                />
                ConsoleMe
            </Menu.Item>
            <Menu.Menu position="left">
                <Menu.Item
                    active={false}
                    exact
                    as={NavLink}
                    name={"roles"}
                    to="/ui/"
                >
                    AWS Console Roles
                </Menu.Item>
                {generateGroupsDropDown()}
                {generatePoliciesDropDown()}
                {generateAdvancedDropDown()}
            </Menu.Menu>
            <Menu.Menu position="right">
                <Menu.Item>
                    {getAvatarImage()}
                </Menu.Item>
            </Menu.Menu>
        </Menu>
    );
};

export default ConsoleMeHeader;