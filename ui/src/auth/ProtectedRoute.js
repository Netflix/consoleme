import React, { useEffect } from "react";
import { useAuth } from "./AuthContext";
import { Route, useRouteMatch } from "react-router-dom";
import { Segment } from "semantic-ui-react";

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
  );
};

export default ProtectedRoute;
