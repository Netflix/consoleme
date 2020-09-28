import _ from "lodash";
import React, { Component } from "react";
import { BrowserRouter, Redirect, Route, Switch } from "react-router-dom";
import { Dimmer, Loader, Segment } from "semantic-ui-react";
import ConsoleMeHeader from "./components/Header";
import ConsoleMeSidebar from "./components/Sidebar";

import ConsoleMeCatalog from "./components/Catalog";
import ConsoleMeDataTable from "./components/ConsoleMeDataTable";
import ConsoleMeSelfService from "./components/SelfService";
import ConsoleMeLogin from "./components/Login";

const LOCAL_KEY = "consoleMeLocalStorage";

class App extends Component {
  constructor(props) {
    super(props);
    this.state = {
      isLoading: true,
      userSession: null,
      recentRoles: ["awsprod_admin", "awstest_admin", "bunker_prod_admin"],
    };
  }

  PrivateRoute = ({ component: ChildComponent, ...rest }) => (
    <Route
      {...rest}
      render={(props) =>
        this.state.userSession ? (
          <React.Fragment>
            <ConsoleMeHeader
              {...props}
              {...rest}
              userSession={this.state.userSession}
            />
            <ConsoleMeSidebar recentRoles={this.state.recentRoles} />
            <Segment
              basic
              style={{
                marginTop: "72px",
                marginLeft: "240px",
              }}
            >
              <ChildComponent {...props} {...rest} />
            </Segment>
          </React.Fragment>
        ) : (
          <Redirect
            to={{
              pathname: "/login",
              state: { from: props.location },
            }}
          />
        )
      }
    />
  );

  componentDidMount() {
    fetch(
      "/auth?force_redirect=false&redirect_url=" + window.location.href
    ).then((resp) =>
      resp.json().then((loginResp) => {
        if (loginResp.type === "redirect") {
          window.location.href = loginResp.redirect_url;
        } else {
          fetch("/api/v1/profile").then((resp) => {
            resp.json().then((userSession) => {
              this.setState({
                userSession,
                isLoading: false,
                // recentRoles: this.getRecentRoles(),
              });
            });
          });
        }
      })
    );
  }

  getRecentRoles() {
    const roles = localStorage.getItem(LOCAL_KEY);
    return roles ? JSON.parse(roles) : [];
  }

  setRecentRole(role) {
    const roles = _.uniq(this.getRecentRoles());
    const recentRoles = roles.unshift(role) > 5 ? roles.slice(0, 5) : roles;
    localStorage.setItem(LOCAL_KEY, JSON.stringify(recentRoles));
    this.setState({
      recentRoles,
    });
  }

  render() {
    const { PrivateRoute } = this;
    const { isLoading, recentRoles, userSession } = this.state;

    return (
      <BrowserRouter>
        {isLoading ? (
          <Dimmer active inverted>
            <Loader size="large">Loading</Loader>
          </Dimmer>
        ) : (
          <Switch>
            <PrivateRoute
              exact
              path="/"
              component={ConsoleMeDataTable}
              configEndpoint={"/api/v2/role_table_config"}
              queryString={""}
              setRecentRole={this.setRecentRole.bind(this)}
            />
            <PrivateRoute
              exact
              path="/selfservice"
              component={ConsoleMeSelfService}
            />
            <PrivateRoute exact path="/catalog" component={ConsoleMeCatalog} />
            <Route exact path="/login" component={ConsoleMeLogin} />
          </Switch>
        )}
      </BrowserRouter>
    );
  }
}

export default App;
