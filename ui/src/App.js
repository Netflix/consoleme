import React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";

import AuthProvider from "./auth/AuthProvider";
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
        <Switch>
          <ProtectedRoute
            key="roles"
            exact
            path="/ui/"
            component={ConsoleMeDataTable}
            configEndpoint={"/api/v2/role_table_config"}
          />
          <ProtectedRoute
            key="selfservice"
            exact
            path="/ui/selfservice"
            component={ConsoleMeSelfService}
          />
          <ProtectedRoute
            key="policies"
            exact
            path="/ui/policies"
            component={ConsoleMeDataTable}
            configEndpoint={"/api/v2/policies_table_config"}
          />
          <ProtectedRoute
            key="review"
            exact
            path="/ui/policies/request/:requestID"
            component={PolicyRequestReview}
          />
          <ProtectedRoute
            key="requests"
            exact
            path="/ui/requests"
            component={ConsoleMeDataTable}
            configEndpoint={"/api/v2/requests_table_config"}
          />
          <ProtectedRoute
            key="iamrole_policy"
            path="/ui/policies/edit/:accountID/:serviceType/:region/:resourceName"
            component={PolicyEditor}
          />
          <ProtectedRoute
            key="resource_policy"
            path="/ui/policies/edit/:accountID/:serviceType/:resourceName"
            component={PolicyEditor}
          />
          <ProtectedRoute
            key="config"
            exact
            path="/ui/config"
            component={ConsoleMeDynamicConfig}
          />
          <ProtectedRoute
            key="role_query"
            exact
            path="/ui/role/:roleQuery+"
            component={ConsoleLogin}
          />
          <ProtectedRoute
            key="challenge_validator"
            exact
            path="/ui/challenge_validator/:challengeToken"
            component={ConsoleMeChallengeValidator}
          />
          <Route component={NoMatch} />
        </Switch>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
