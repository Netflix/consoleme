import React, { useEffect } from "react";
import { useAuth } from "./AuthProviderDefault";
import { useNotifications } from "../components/hooks/notifications";
import {
  Route,
  useHistory,
  useLocation,
  useRouteMatch,
} from "react-router-dom";
import { Segment } from "semantic-ui-react";
import ConsoleMeHeader from "../components/Header";
import ConsoleMeSidebar from "../components/Sidebar";
import ReactGA from "react-ga";

const ProtectedRoute = (props) => {
  const auth = useAuth();
  const notifications = useNotifications();
  let history = useHistory();
  const location = useLocation();
  const { login, user, isSessionExpired } = auth;
  const { RetrieveNotificationsAtInterval } = notifications;
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
        await login(history);
      })();
    }
    if (user) {
      let interval = 60;
      if (user?.site_config?.notifications?.request_interval) {
        interval = user.site_config.notifications.request_interval;
      }
      RetrieveNotificationsAtInterval(interval);
    }
  }, [match, user, isSessionExpired, login, history]); // eslint-disable-line

  if (!user) {
    return null;
  }

  let marginTop = "0px";

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
      marginTop = "72px";
    }
  }

  if (user?.google_analytics_initialized) {
    const currentPath = location.pathname + location.search;
    ReactGA.set({ page: currentPath });
    ReactGA.pageview(currentPath);
  }
  return (
    <>
      <ConsoleMeHeader />
      <ConsoleMeSidebar />
      <Segment
        basic
        style={{
          marginTop: marginTop,
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
