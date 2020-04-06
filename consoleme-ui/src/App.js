// import Main from './Main';
import React, {Component} from 'react';
import {
    Container,
    Dropdown,
    Grid,
    Header,
    Icon,
    Menu,
    Sidebar,
    Image,
    Segment,
} from 'semantic-ui-react';
import {BrowserRouter, NavLink, Route, Switch} from 'react-router-dom'
import './App.css';

import Main from './components/Main';



class SelfService extends Component {
    render() {
        return (
            <div>
                <h2>Self Service</h2>
            </div>
        );
    }
}


class App extends Component {
    constructor(props) {
        super(props);
        this.state = {
            loading: true,
            headers: {}
        };
    }

    componentDidMount() {
        fetch(
            "/api/v1/pageheader", {
                mode: 'no-cors',
                credentials: 'include',
            }).then((res) => {
            res.json().then((data) => {
                this.setState({
                    headers: data,
                    loading: false,
                });
            });
        });
    }

    generateGroupsDropDown() {
        if (this.state.headers.pages.groups.enabled === true) {
            return (
                <Dropdown text='Group Access' pointing className='link item'>
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
        if (this.state.headers.pages.policies.enabled === true) {
            return (
                <Dropdown text='Roles and Policies' pointing className='link item'>
                    <Dropdown.Menu>
                        <Dropdown.Item as={NavLink} to="/policies2">Policies</Dropdown.Item>
                        <Dropdown.Item as={NavLink} to="/selfservice">Self Service Permissions</Dropdown.Item>
                        <Dropdown.Item as={NavLink} to="/apihealth">API Health</Dropdown.Item>
                    </Dropdown.Menu>
                </Dropdown>
            );
        }
        return null;
    }

    generateAdvancedDropDown() {
        if (this.state.headers.pages.config.enabled === true) {
            return (
                <Dropdown text='Advanced' pointing className='link item'>
                    <Dropdown.Menu>
                        <Dropdown.Item>Audit</Dropdown.Item>
                        <Dropdown.Item>Config</Dropdown.Item>
                    </Dropdown.Menu>
                </Dropdown>
            );
        }
        return null;
    }

    getConsoleMeLogo() {
        if (this.state.headers.consoleme_logo) {
            return (
                <footer>
                    <div id="consoleme_logo">
                        <img id="consoleme_logo" src={this.state.headers.consoleme_logo}/>
                    </div>
                    <a
                        className="security-logo"
                        target="_blank"
                        style={{
                            background: 'url(/static/screenplay/assets/netflix-security-dark-bg-tight.5f1eba5edb.svg) no-repeat 50%'
                        }}
                    />
                </footer>
            );
        }
        return null;
    }

    getDocumentation() {
        if (this.state.headers.documentation_url) {
            return (
                <li>
                    <a href={this.state.headers.documentation_url} target={"_blank"}>
                        <Icon name={"book"}/>
                        Documentation
                    </a>
                </li>
            );
        }
        return null;
    }

    getSupportContact() {
        if (this.state.headers.support_contact) {
            return (
                <li>
                    <a href={"mailto:" + this.state.headers.support_contact} target={"_blank"}>
                        <Icon name={"envelope"}/>
                        Email us
                    </a>
                </li>
            );
        }
        return null;
    }

    getChatLink() {
        if (this.state.headers.support_slack) {
            return (
                <li>
                    <a href={this.state.headers.support_slack} target={"_blank"}>
                        <Icon name={"slack"}/>
                        Find us on Slack
                    </a>
                </li>
            );
        }
        return null;
    }

    getAvatarImage() {
        if (this.state.headers.employee_photo_url) {
            return (
                <div>
                    <Image src={this.state.headers.employee_photo_url} avatar />
                    <span>{this.state.headers.user}</span>
                </div>
            );
        }
        return null;
    }

    render() {
        // TODO, remove this instead initialize header state data and render empty menus
        if (this.state.loading) {
            return (
                <div>
                    <h1>Loading ConsoleMe</h1>
                </div>
            );
        }

        return (
            <BrowserRouter>
                <div className="App">
                    <Sidebar.Pushable>
                        <Sidebar
                            animation={'overlay'}
                            direction={'left'}
                            visible={true}
                        >
                            <div className="brand">
                                <a href="/">Consoleme</a>
                            </div>
                            <div id="RoleHistory">
                                <h3>Recent roles</h3>
                                <ul>
                                    <li>
                                        <a>
                                            <div>
                                                <label>
                                                    bunker_prod_admin
                                                </label>
                                            </div>
                                        </a>
                                    </li>
                                </ul>
                            </div>
                            <div id={"help"}>
                                <h3>Help</h3>
                                <ul>
                                    {this.getDocumentation()}
                                    {this.getSupportContact()}
                                    {this.getChatLink()}
                                </ul>
                            </div>
                            {this.getConsoleMeLogo()}
                        </Sidebar>
                        <Sidebar.Pusher>
                            <Segment basic>
                                <Menu pointing secondary>
                                    <Menu.Item
                                        name={"AWS Console Roles"}
                                        active={true}
                                        as={NavLink}
                                        to="/"
                                    >
                                        AWS Console Roles
                                    </Menu.Item>
                                    {this.generateGroupsDropDown()}
                                    {this.generatePoliciesDropDown()}
                                    {this.generateAdvancedDropDown()}
                                    <Menu.Menu position='right'>
                                        <Menu.Item name='logout'>
                                            {this.getAvatarImage()}
                                        </Menu.Item>
                                    </Menu.Menu>
                                </Menu>
                                <Switch>
                                    <Route exact path="/" component={Main}/>
                                    <Route exact path="/selfservice" component={SelfService}/>
                                </Switch>
                            </Segment>
                        </Sidebar.Pusher>
                    </Sidebar.Pushable>
                </div>
            </BrowserRouter>
        );
    }
}

export default App;