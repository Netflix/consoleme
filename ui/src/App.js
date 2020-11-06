import React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import AuthProvider from "./auth/AuthProvider";
import ConsoleMeHeader from "./components/Header";
import ConsoleMeSidebar from "./components/Sidebar";
import ProtectedRoute from "./auth/ProtectedRoute";
import ConsoleMeDataTable from "./components/ConsoleMeDataTable";
import ConsoleMeSelfService from "./components/SelfService";
import ConsoleMeDynamicConfig from "./components/DynamicConfig";
import PolicyRequestReview from "./components/PolicyRequestsReview";
import PolicyEditor from "./components/policy/PolicyEditor";
import ConsoleLogin from "./components/ConsoleLogin.js";
import ConsoleMeChallengeValidator from "./components/challenge/ConsoleMeChallengeValidator";

const NoMatch = ({ location }) => (
  <h3>
    No match for <code>{location.pathname}</code>
  </h3>
);

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ConsoleMeHeader />
        <ConsoleMeSidebar />
        <Switch>
          <ProtectedRoute
            key="roles"
            exact
            path="/"
            component={ConsoleMeDataTable}
            configEndpoint={"/api/v2/role_table_config"}
          />
          <ProtectedRoute
            key="selfservice"
            exact
            path="/selfservice"
            component={ConsoleMeSelfService}
          />
          <ProtectedRoute
            key="policies"
            exact
            path="/policies"
            component={ConsoleMeDataTable}
            configEndpoint={"/api/v2/policies_table_config"}
          />
          <ProtectedRoute
            key="review"
            exact
            path="/policies/request/:requestID"
            component={PolicyRequestReview}
          />
          <ProtectedRoute
            key="requests"
            exact
            path="/requests"
            component={ConsoleMeDataTable}
            configEndpoint={"/api/v2/requests_table_config"}
          />
          <ProtectedRoute
            key="iamrole_policy"
            path="/policies/edit/:accountID/:serviceType/:region/:resourceName"
            component={PolicyEditor}
          />
          <ProtectedRoute
            key="resource_policy"
            path="/policies/edit/:accountID/:serviceType/:resourceName"
            component={PolicyEditor}
          />
          <ProtectedRoute
            key="config"
            exact
            path="/config"
            component={ConsoleMeDynamicConfig}
          />
          <ProtectedRoute
            key="role_query"
            exact
            path="/role/:roleQuery+"
            component={ConsoleLogin}
          />
          <ProtectedRoute
            key="challenge_validator"
            exact
            path="/challenge_validator/:challengeToken"
            component={ConsoleMeChallengeValidator}
          />
          <Route component={NoMatch} />
        </Switch>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
