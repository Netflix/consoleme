import React, { useEffect } from "react";
import { useAuth } from "./AuthProviderDefault";
import { Route, useRouteMatch } from "react-router-dom";
import { Segment } from "semantic-ui-react";
import ConsoleMeHeader from "../components/Header";
import ConsoleMeSidebar from "../components/Sidebar";

const ProtectedRoute = (props) => {
  const auth = useAuth();
  const { login, user, isSessionExpired } = auth;
  const match = useRouteMatch(props);
  const { component: Component, ...rest } = props;

  useEffect(() => {
    // make sure we only handle the registered routes
    if (!match) {
      return;
    }

    // TODO(heewonk), This is a temporary way to prevent multiple logins when 401 type of access deny occurs.
    // Revisit later to enable this logic only when ALB type of authentication is being used.
    if (isSessionExpired) {
      return;
    }

    if (!user) {
      (async () => {
        await login();
      })();
    }
  }, [match, user, isSessionExpired, login]);

  if (!user) {
    return null;
  }

  let marginTop = "72px";

  if (
    user?.pages?.header?.custom_header_message_title ||
    user?.pages?.header?.custom_header_message_text
  ) {
    let matchesRoute = true;
    if (user?.pages?.header?.custom_header_message_route) {
      const re = new RegExp(user.pages.header.custom_header_message_route);
      if (!re.test(window.location.pathname)) {
        matchesRoute = false;
      }
    }
    if (matchesRoute) {
      marginTop = "0px";
    }
  }

  return (
    <>
      <ConsoleMeHeader />
      <ConsoleMeSidebar />
      <Segment
        basic
        style={{
          marginTop: marginTop,
          marginLeft: "240px",
        }}
      >
        <div className="inner-container">
          <Route
            {...rest}
            render={(props) => {
              return <Component {...props} {...rest} {...auth} />;
            }}
          />
        </div>
      </Segment>
    </>
  );
};

export default ProtectedRoute;
