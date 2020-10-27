import React, { useEffect } from "react";
import { useAuth } from "./AuthContext";
import { Route, useRouteMatch } from "react-router-dom";
import { Dimmer, Loader, Segment } from "semantic-ui-react";

import ConsoleMeHeader from "../components/Header";
import ConsoleMeSidebar from "../components/Sidebar";

const ProtectedRoute = (props) => {
  const { login, user } = useAuth();

  const match = useRouteMatch(props);

  useEffect(() => {
    if (!match) {
      return;
    }
    if (!user) {
      login();
    }
  }, [match]); // eslint-disable-line

  const { component: Component, ...rest } = props;
  return (
    <>
      <ConsoleMeHeader />
      <ConsoleMeSidebar
        recentRoles={["example_role_1", "example_role_2", "example_role_3"]}
      />
      <Segment
        basic
        style={{
          marginTop: "72px",
          marginLeft: "240px",
        }}
      >
        <Route
          {...rest}
          render={(props) => {
            return <Component {...props} {...rest} />;
          }}
        />
      </Segment>
    </>
  );
};

export default ProtectedRoute;
