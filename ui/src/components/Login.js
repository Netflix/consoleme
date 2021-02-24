import React, { useEffect, useState } from "react";
import {
  Button,
  Form,
  Grid,
  Header,
  Icon,
  Image,
  Message,
  Segment,
} from "semantic-ui-react";
import { useHistory } from "react-router-dom";
import qs from "qs";

const signInWithSSO = () => {};
const LoginForm = () => {
  const [pageConfig, setPageConfig] = useState(null);
  const [userName, setUserName] = useState(null);
  const [password, setPassword] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [redirectUrl, setRedirectUrl] = useState("/");
  const parsedQueryString = qs.parse(window.location.search, {
    ignoreQueryPrefix: true,
  });

  const history = useHistory();
  // TODO, pull login config and render login page based on it.
  useEffect(() => {
    (async () => {
      if (parsedQueryString) {
        Object.keys(parsedQueryString).forEach((key) => {
          if (key === "redirect_after_auth") {
            setRedirectUrl(parsedQueryString[key]);
          }
        });
      }
      const res = await fetch("/api/v2/login_configuration", {
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          Accept: "application/json",
        },
      });
      if (!res) {
        return;
      }
      setPageConfig(await res.json());
    })();
  }, []);
  if (!pageConfig) {
    return null;
  }

  const handleSetUserName = (e) => {
    setUserName(e.target.value);
  };

  const handleSetPassword = (e) => {
    setPassword(e.target.value);
  };

  const signInWithPassword = async () => {
    const res = await fetch("/api/v2/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        username: userName,
        password: password,
        after_redirect_uri: redirectUrl,
      }),
    });
    if (!res) {
      return;
    }

    if (res.status === 200) {
      const resJson = await res.json();
      history.push(resJson.redirect_url);
    } else if (res.status === 403) {
      let resJson = "";
      try {
        resJson = await res.json();
        resJson = resJson["errors"];
      } catch {
        resJson = await res;
      }
      setErrorMessage(resJson);
    }

    // TODO: Show authentication errors here if non 200 response
  };

  return (
    <>
      <Grid
        textAlign="center"
        verticalAlign="middle"
        style={{
          height: "100vh",
        }}
      >
        <Grid.Column
          style={{
            maxWidth: 380,
          }}
        >
          <Header
            attached="top"
            block
            textAlign="left"
            style={{
              fontSize: "34px",
              textTransform: "uppercase",
            }}
          >
            <Image src="/images/logos/logo192.png" />
            ConsoleMe
          </Header>
          {errorMessage ? (
            <Message negative>
              <p>{errorMessage}</p>
            </Message>
          ) : null}
          {pageConfig?.allow_password_login ? (
            <Segment attached textAlign="left">
              <Form size="small">
                <Form.Input
                  fluid
                  icon="user"
                  iconPosition="left"
                  placeholder="E-mail address"
                  label="Username or email"
                  onChange={handleSetUserName}
                />
                <Form.Input
                  fluid
                  icon="lock"
                  iconPosition="left"
                  placeholder="Password"
                  type="password"
                  label="Password"
                  onChange={handleSetPassword}
                />
                <Button
                  color="red"
                  fluid
                  size="large"
                  onClick={signInWithPassword}
                >
                  Sign in
                </Button>
                {pageConfig?.custom_message}
              </Form>
            </Segment>
          ) : null}
          {pageConfig?.allow_sso_login ? (
            <Segment attached textAlign="left">
              <p>Single Sign-On is enabled for your organization.</p>
              <Button color="green" fluid onClick={signInWithSSO}>
                Sign In With Your Identity Provider
              </Button>
            </Segment>
          ) : null}
          {pageConfig?.allow_sign_up ? (
            <Message attached="bottom">
              New to us? <a href="#">Sign Up</a>
            </Message>
          ) : null}
        </Grid.Column>
      </Grid>
      <Image
        disabled
        src="/images/logos/sunglasses/3.png"
        size="medium"
        style={{
          bottom: 0,
          right: 0,
          position: "absolute",
          marginRight: "10px",
          marginBottom: "10px",
        }}
      />
    </>
  );
};
export default LoginForm;
