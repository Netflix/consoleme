import React from 'react';
import { Link } from 'react-router-dom';
import {
    Button,
    Container,
    Dropdown,
    Menu,
    Header,
    Icon,
    Image,
    Sidebar,
} from 'semantic-ui-react';
import logo from './static/logos/nosunglasses/1.png'
import security_logo from './static/screenplay/assets/netflix-security-dark-bg-tight.5f1eba5edb.svg'
import './App.css';


function Main() {
    return (
        <div className="App">
            <div id={"header"}>
                <a className="brand" href="/">Consoleme</a>
                <div className={"content"}>
                    <Menu pointing secondary>
                        <Menu.Item
                            name={"AWS Console Roles"}
                            active={true}
                        >
                            AWS Console Roles
                        </Menu.Item>
                      <Dropdown text='Group Access' pointing className='link item'>
                          <Dropdown.Menu>
                            <Dropdown.Item>Request Access</Dropdown.Item>
                            <Dropdown.Item>Groups</Dropdown.Item>
                            <Dropdown.Item>Users</Dropdown.Item>
                            <Dropdown.Item>Pending</Dropdown.Item>
                          </Dropdown.Menu>
                        </Dropdown>
                        <Dropdown text='Roles and Policies' pointing className='link item'>
                          <Dropdown.Menu>
                            <Dropdown.Item>Policies</Dropdown.Item>
                            <Dropdown.Item>Self Service Permissions</Dropdown.Item>
                            <Dropdown.Item>API Health</Dropdown.Item>
                          </Dropdown.Menu>
                        </Dropdown>
                        <Dropdown text='Advanced' pointing className='link item'>
                          <Dropdown.Menu>
                            <Dropdown.Item>Audit</Dropdown.Item>
                            <Dropdown.Item>Config</Dropdown.Item>
                          </Dropdown.Menu>
                        </Dropdown>
                        <Menu.Menu position='right'>
                            <Menu.Item
                                name='logout'
                            />
                        </Menu.Menu>
                    </Menu>
                </div>
            </div>
            <div id={"primary"}>
                <Sidebar
                    visible={true}
                    className={"nav"}
                >
                    <nav>
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
                            <li>
                                <a>
                                    <div>
                                        <label>
                                            awsprod_admin
                                        </label>
                                    </div>
                                </a>
                            </li>
                            <li>
                                <a>
                                    <div>
                                        <label>
                                            awstest_admin
                                        </label>
                                    </div>
                                </a>
                            </li>
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
                            <li>
                                <a href={"http://go/consolemedocs"} target={"_blank"}>
                                    <Icon name={"book"} />
                                    Documentation
                                </a>
                            </li>
                            <li>
                                <a href={"mailto:infrasec@netflix.com"} target={"_blank"}>
                                    <Icon name={"envelope"} />
                                    Email us
                                </a>
                            </li>
                            <li>
                                <a href={"https://netflix.slack.com/messages/C0ZQD445A/"} target={"_blank"}>
                                    <Icon name={"slack"} />
                                    Find us on Slack
                                </a>
                            </li>
                        </ul>
                    </div>
                    <footer>
                        <div id="consoleme_logo">
                            <img id="consoleme_logo" src={logo} />
                        </div>
                        <a
                            className="security-logo"
                            target="_blank"
                            href="http://go/infrasec"
                            style={{
                                background: 'url(' + security_logo + ') no-repeat 50%'
                            }}
                        />
                    </footer>
                        </nav>
                </Sidebar>
                <Container id={"wrapper"}>
                </Container>
            </div>
        </div>
    );
}

export default Main;
