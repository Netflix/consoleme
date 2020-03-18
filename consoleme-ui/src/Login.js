import React, { Component } from 'react';
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
import './Login.css';

export default class Login extends Component {

  constructor(props) {
    super(props);

    this.state = {
      username: '',
      text: (<div>EMAIL</div>),
      text_plainText: "EMAIL",
      password: '',
      textcopy: (<div>PASSWORD</div>),
      textcopy_plainText: "PASSWORD",
    };
  }

  async componentDidMount() {

    if (localStorage.getItem('loginToken') != null) {

    }
  }

  async componentWillUnmount() {
  }

  async componentDidUpdate() {
  }

  async componentWillReceiveProps(nextProps) {
  }

  textInputChanged_username = async(event) => {
    await this.setState({username: event.target.value});
  };

  textInputChanged_password = async(event) =>  {
    await this.setState({password: event.target.value});
  };

  onClick_elSignin = async(ev) => {
    const credentials = {
      username: this.state.username,
      password: this.state.password
    };
    const loginRequest = await fetch("/auth", {
      method: 'POST', // *GET, POST, PUT, DELETE, etc.
      credentials: 'same-origin', // include, *same-origin, omit
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(credentials)
    });
    const resJson = await loginRequest.json(); // parses JSON response into native JavaScript objects
    console.log(resJson)
    if (resJson.authenticated === false && resJson.redirect) {
      window.location.replace(resJson.redirect);
    }
  };

  onClick_elSignin_sso = async(ev) => {
    // Refresh data sheet
    let res = await fetch("/auth")
    let resJson = await res.json();
    if (resJson.authenticated === false && resJson.redirect) {
      window.location.replace(resJson.redirect);
    }
  };


  render() {
    let layoutFlowStyle = {};
    let baseStyle = {};
    if (this.props.transitionId && this.props.transitionId.length > 0 && this.props.atTopOfScreenStack && this.props.transitionForward) {
      baseStyle.animation = '0.25s ease-in-out '+this.props.transitionId;
    }
    if ( !this.props.atTopOfScreenStack) {
      layoutFlowStyle.height = '100vh';
      layoutFlowStyle.overflow = 'hidden';
    }

    const style_elBackground = {
      width: '100%',
      height: '100%',
     };
    const style_elBackground_outer = {
      backgroundColor: '#f6f6f6',
     };

    const style_elUsername = {
      display: 'block',
      backgroundColor: 'white',
      paddingLeft: '1rem',
      boxSizing: 'border-box', // ensures padding won't expand element's outer size
      pointerEvents: 'auto',
     };
    const style_elText = {
      fontSize: 15.2,
      color: 'rgba(0, 0, 0, 0.8500)',
      textAlign: 'left',
     };

    const style_elPassword = {
      display: 'block',
      backgroundColor: 'white',
      paddingLeft: '1rem',
      boxSizing: 'border-box', // ensures padding won't expand element's outer size
      pointerEvents: 'auto',
     };
    const style_elSignin = {
      display: 'block',
      color: 'white',
      textAlign: 'center',
      cursor: 'pointer',
      pointerEvents: 'auto',
     };
    const style_elSignin_sso = {
      display: 'block',
      color: 'white',
      textAlign: 'center',
      cursor: 'pointer',
      pointerEvents: 'auto',
     };
    const style_elTextCopy = {
      fontSize: 15.2,
      color: 'rgba(0, 0, 0, 0.8500)',
      textAlign: 'left',
     };

    return (
      <div className="AppScreen LoginPageScreen" style={baseStyle}>
        <div className="background">
          <div className="containerMinHeight elBackground" style={style_elBackground_outer}>
            <div className="appBg" style={style_elBackground} />
          </div>
        </div>

        <div className="layoutFlow" style={layoutFlowStyle}>
          <div className="elUsername">
            <input className="baseFont" style={style_elUsername} type="text" placeholder="" onChange={this.textInputChanged_username} value={this.state.username}  />
          </div>

          <div className="elText">
            <div className="font-helveticaNeue" style={style_elText}>
              <div>{this.state.text}</div>
            </div>
          </div>

          <div className="elPassword">
            <input className="baseFont" style={style_elPassword} type="password" placeholder="" onChange={this.textInputChanged_password} value={this.state.password}  />
          </div>

          <div className="elSignin">
            <Button primary className="actionFont" style={style_elSignin}  color="accent" onClick={this.onClick_elSignin} >
              Sign In
            </Button>
          </div>

          <div className="elSignin_sso">
            <Button primary className="actionFont" style={style_elSignin_sso}  color="accent" onClick={this.onClick_elSignin_sso} >
              Sign In With SSO
            </Button>
          </div>

          <div className="elTextCopy">
            <div className="font-helveticaNeue" style={style_elTextCopy}>
              <div>{this.state.textcopy}</div>
            </div>
          </div>
        </div>

      </div>
    )
  }

}
