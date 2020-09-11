import React, {Component} from 'react';
import PropTypes from 'prop-types';
import {
    Icon,
    Image,
    Sidebar,
} from 'semantic-ui-react';

import './Sidebar.css';

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

    getDocumentation() {
        if (this.state.config.documentation_url) {
            return (
                <li>
                    <a href={this.state.config.documentation_url} target={"_blank"}>
                        <Icon name={"book"}/>
                        Documentation
                    </a>
                </li>
            );
        }
        return null;
    }

    getSupportContact() {
        if (this.state.config.support_contact) {
            return (
                <li>
                    <a href={"mailto:" + this.state.config.support_contact} target={"_blank"}>
                        <Icon name={"envelope"}/>
                        Email us
                    </a>
                </li>
            );
        }
        return null;
    }

    getChatLink() {
        if (this.state.config.support_slack) {
            return (
                <li>
                    <a href={this.state.config.support_slack} target={"_blank"}>
                        <Icon name={"slack"}/>
                        Find us on Slack
                    </a>
                </li>
            );
        }
        return null;
    }

    render() {
        return (
            <Sidebar
                animation={'overlay'}
                direction={'left'}
                visible={true}
            >
                <div className="brand">
                    <a href="/">Consoleme</a>
                </div>
                <div className="roleHistory">
                    <h3>Recent roles</h3>
                    <ul>
                        {
                            this.props.recentRoles.map((role) => {
                                return (
                                    <li key={role}>
                                        <a>
                                            <div>
                                                <label>
                                                    {role}
                                                </label>
                                            </div>
                                        </a>
                                    </li>
                                )
                            })
                        }
                    </ul>
                </div>
                <div className="help">
                    <h3>Help</h3>
                    <ul>
                        {this.getDocumentation()}
                        {this.getSupportContact()}
                        {this.getChatLink()}
                    </ul>
                </div>
                <br />
                {this.getConsoleMeLogo()}
            </Sidebar>
        )
    }
}

ConsoleMeSidebar.propType = {
    recentRoles: PropTypes.array,
};

export default ConsoleMeSidebar;