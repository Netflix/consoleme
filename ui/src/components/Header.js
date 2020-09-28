import React, {Component} from 'react';
import PropTypes from 'prop-types';
import {
    Dropdown,
    Menu,
    Image,
} from 'semantic-ui-react';
import {NavLink} from 'react-router-dom'


class ConsoleMeHeader extends Component {
    static defaultProps = {
        userSession: {},
    }

    generateGroupsDropDown() {
        if (this.props.userSession.pages.groups.enabled === true) {
            return (
                <Dropdown text='Group Access' pointing className='link item'>
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

    generatePoliciesDropDown() {
        if (this.props.userSession.pages.policies.enabled === true) {
            return (
                <Dropdown
                    text="Roles and Policies"
                    pointing className="link item"
                >
                    <Dropdown.Menu>
                        <Dropdown.Item
                            as={NavLink}
                            to="/catalog"
                        >
                            Catalog
                        </Dropdown.Item>
                        <Dropdown.Item>
                            Policies
                        </Dropdown.Item>
                        <Dropdown.Item
                            as={NavLink}
                            to="/selfservice"
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

    generateAdvancedDropDown() {
        if (this.props.userSession.pages.config.enabled === true) {
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

    getAvatarImage() {
        if (this.props.userSession.employee_photo_url) {
            return (
                <Image
                    alt={this.props.userSession.user}
                    avatar
                    src={this.props.userSession.employee_photo_url}
                    title={this.props.userSession.user}
                />
            );
        }
        return null;
    }

    render() {
        if (!this.props.userSession) {
            return null;
        }
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
                    href="/"
                >
                    <Image
                        size='mini'
                        src='/images/logo192.png'
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
                        to="/"
                    >
                        AWS Console Roles
                    </Menu.Item>
                    {this.generateGroupsDropDown()}
                    {this.generatePoliciesDropDown()}
                    {this.generateAdvancedDropDown()}
                </Menu.Menu>
                <Menu.Menu position="right">
                    <Menu.Item>
                        {this.getAvatarImage()}
                    </Menu.Item>
                </Menu.Menu>
            </Menu>
        );
    }
}

ConsoleMeHeader.propType = {
    userSession: PropTypes.object,
};

export default ConsoleMeHeader;