import React, { useEffect } from "react";
import { useAuth } from "./AuthProvider";
import { Route, useRouteMatch } from "react-router-dom";
import { Segment } from "semantic-ui-react";

const ProtectedRoute = (props) => {
  const { login, user } = useAuth();
  const match = useRouteMatch(props);
  const { component: Component, ...rest } = props;

  useEffect(() => {
    if (!match) {
      return;
    }
    if (!user) {
      (async () => {
        await login();
      })();
    }
  }, [match]); // eslint-disable-line

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
