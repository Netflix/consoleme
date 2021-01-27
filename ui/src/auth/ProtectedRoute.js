import React, { useEffect } from "react";
import { useAuth } from "./AuthProviderDefault";
import { Route, useRouteMatch } from "react-router-dom";
import { Segment } from "semantic-ui-react";

const ProtectedRoute = (props) => {
  const auth = useAuth();
  const { login, user } = auth;
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
  }, [match, user]); // eslint-disable-line

  if (!user) {
    return null;
  }

  let marginTop = "72px";

  if (
    user?.pages?.header?.custom_header_message_title ||
    user?.pages?.header?.custom_header_message_text
  ) {
    marginTop = "0px";
  }

  return (
    <Segment
      basic
      style={{
        marginTop: marginTop,
        marginLeft: "240px",
      }}
    >
      <Route
        {...rest}
        render={(props) => {
          return <Component {...props} {...rest} {...auth} />;
        }}
      />
    </Segment>
  );
};

export default ProtectedRoute;
