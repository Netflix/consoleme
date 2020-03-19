import React, {Component} from 'react';
import {Container, Dropdown, Icon, Menu, Sidebar, Image} from 'semantic-ui-react';
import './App.css';

export default class Main extends Component {

  constructor(props) {
    super(props);

    this.state = {
      loading: 'true',
      headers: {}
    };
  }

  async componentWillMount() {
    const headerData = await this.getHeaderData()
    this.setState(
      {
        headers: headerData,
        loading: 'false'
      }
    );
    console.log(this.state)
  }

  async componentDidMount() {
    await this.setState({loading: 'true'})

  }

  getHeaderData = async (event) => {
    const PageHeaderDataReq = await fetch(
      "/api/v1/pageheader", {
        mode: 'no-cors',
        credentials: 'include',
      });
    const PageHeaderData = await PageHeaderDataReq.json();
    return PageHeaderData
  };

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
      )
    }
    return ''
  }

  generatePoliciesDropDown() {
    if (this.state.headers.pages.policies.enabled === true) {
      return (
        <Dropdown text='Roles and Policies' pointing className='link item'>
          <Dropdown.Menu>
            <Dropdown.Item>Policies</Dropdown.Item>
            <Dropdown.Item>Self Service Permissions</Dropdown.Item>
            <Dropdown.Item>API Health</Dropdown.Item>
          </Dropdown.Menu>
        </Dropdown>
      )
    }
    return ''
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
      )
    }
    return ''
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
      )
    }
    return ''
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
      )
    }
    return ''
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
      )
    }
    return ''
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
      )
    }
    return ''
  }

  getAvatarImage() {
    if (this.state.headers.employee_photo_url) {
      return (
        <div>
    <Image src={this.state.headers.employee_photo_url} avatar />
    <span>{this.state.headers.user}</span>
  </div>
      )
    }
    return ''
  }


  render() {
    if (this.state.loading !== 'false') {
      return <h2>Loading...</h2>;
    }

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
              {this.generateGroupsDropDown()}
              {this.generatePoliciesDropDown()}
              {this.generateAdvancedDropDown()}
              <Menu.Menu position='right'>
                <Menu.Item
                  name='logout'
                >
                  {this.getAvatarImage()}
                </Menu.Item>
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
                  {this.getDocumentation()}
                  {this.getSupportContact()}
                  {this.getChatLink()}
                </ul>
              </div>
              {this.getConsoleMeLogo()}
            </nav>
          </Sidebar>
          <Container id={"wrapper"}>
          </Container>
        </div>
      </div>
    );
  }
}
