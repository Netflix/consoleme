import React, {Component} from 'react';
import PropTypes from 'prop-types';
import {
    Label,
    Icon,
    Image,
    Menu,
} from 'semantic-ui-react';

const LOGO_URL = '/static/screenplay/assets/netflix-security-dark-bg-tight.5f1eba5edb.svg';


class ConsoleMeSidebar extends Component {
    constructor(props) {
        super(props);
        this.state = {
            config: {},
        };
    }

    componentDidMount() {
        fetch(
            "/api/v1/siteconfig", {
                mode: 'no-cors',
                credentials: 'include',
            }).then((res) => {
            res.json().then((config) => {
                this.setState({
                    config,
                });
            });
        });
    }

    getConsoleMeLogo() {
        if (this.state.config.consoleme_logo) {
            return (
                <footer>
                    <Image
                        className="consoleme_logo"
                        src={this.state.config.consoleme_logo}
                    />
                    <br />
                    <Image
                        className="security-logo"
                        src={LOGO_URL}
                    />
                </footer>
            );
        }
        return null;
    }

    render() {
        const {
            consoleme_logo,
            documentation_url,
            support_contact,
            support_slack
        } = this.state.config;

        return (
            <Menu
                color="black"
                fixed="left"
                inverted
                vertical
                style={{
                    paddingTop: "10px",
                    width: "240px",
                    marginTop: "72px"
                }}
            >
                <Menu.Item>
                    <Label>
                        {this.props.recentRoles.length}
                    </Label>
                    <Menu.Header>
                        Recent Roles
                    </Menu.Header>
                    <Menu.Menu>
                        {
                            this.props.recentRoles.map((role) => {
                                return (
                                    <Menu.Item
                                        as="a"
                                        name={role}
                                        key={role}
                                    >
                                        {role}
                                    </Menu.Item>
                                )
                            })
                        }
                    </Menu.Menu>
                </Menu.Item>
                <Menu.Item>
                    <Menu.Header>Help</Menu.Header>
                    <Menu.Menu>
                        <Menu.Item
                            as="a"
                            name='documentation'
                            href={documentation_url || ""}
                            rel="noopener noreferrer"
                            target="_blank"
                        >
                            <Icon name="file" />
                            Documenation
                        </Menu.Item>
                        <Menu.Item
                            as="a"
                            name='email'
                            href={
                                support_contact
                                    ? "mailto:" + support_contact
                                    : "/"
                            }
                            rel="noopener noreferrer"
                            target="_blank"
                        >
                            <Icon name="send" />
                            Email us
                        </Menu.Item>
                        <Menu.Item
                            as="a"
                            name='slack'
                            href={support_slack || "/"}
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
                        position: 'absolute',
                        bottom: '70px',
                        left: '0'
                    }}
                >
                    <Menu.Item>
                        <Image
                            size="medium"
                            src='/images/logos/quarantine/1.png'
                        />
                        <br />
                        <a
                            href="http://go/infrasec"
                            rel="noopener noreferrer"
                            target="_blank"
                        >
                            <Image
                                size="medium"
                                src='/images/netflix-security-dark-bg-tight.svg'
                            />
                        </a>
                    </Menu.Item>
                </Menu.Menu>
            </Menu>
        )
    }
}

ConsoleMeSidebar.propType = {
    recentRoles: PropTypes.array,
};

export default ConsoleMeSidebar;