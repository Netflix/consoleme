import React, { useState, useEffect } from "react";
import { BrowserRouter, Redirect, Route, Switch } from "react-router-dom";

import AuthProvider from "./auth/AuthProvider";
import ProtectedRoute from "./auth/ProtectedRoute";
import ConsoleMeDataTable from "./components/ConsoleMeDataTable";
import ConsoleMeSelfService from "./components/SelfService";
import ConsoleMeDynamicConfig from "./components/DynamicConfig";
import PolicyRequestReview from "./components/PolicyRequestsReview";
import PolicyEditor from "./components/policy/PolicyEditor";

const LOCAL_KEY = "consoleMeLocalStorage";

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
            exact
            path="/ui/"
            component={ConsoleMeDataTable}
            configEndpoint={"/api/v2/role_table_config"}
            queryString={""}
          />
          <ProtectedRoute
            exact
            path="/ui/selfservice"
            component={ConsoleMeSelfService}
          />
          <ProtectedRoute
            exact
            path="/ui/policies"
            component={ConsoleMeDataTable}
            configEndpoint={"/api/v2/policies_table_config"}
            queryString={""}
          />
          <ProtectedRoute
            exact
            path="/ui/policies/request/:requestID"
            component={PolicyRequestReview}
          />
          <ProtectedRoute
            exact
            path="/ui/requests"
            component={ConsoleMeDataTable}
            configEndpoint={"/api/v2/requests_table_config"}
            queryString={""}
          />
          <ProtectedRoute
            path="/ui/policies/edit/:accountID/:serviceType/:region/:resourceName"
            component={PolicyEditor}
          />
          <ProtectedRoute
            path="/ui/policies/edit/:accountID/:serviceType/:resourceName"
            component={PolicyEditor}
          />
          <ProtectedRoute
            exact
            path="/ui/config"
            component={ConsoleMeDynamicConfig}
          />
          <Route component={NoMatch} />
        </Switch>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
