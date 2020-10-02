import React, { useState, useEffect } from "react";
import { BrowserRouter, Redirect, Route, Switch } from "react-router-dom";

import AuthProvider from "./auth/AuthProvider";
import ProtectedRoute from "./auth/ProtectedRoute";

import ConsoleMeCatalog from "./components/Catalog";
import ConsoleMeDataTable from "./components/ConsoleMeDataTable";
import ConsoleMeSelfService from "./components/SelfService";
// import ConsoleMeLogin from "./components/Login";

const LOCAL_KEY = "consoleMeLocalStorage";

// TODO(heewonk), come up with better 404 page
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
            path="/ui/requests"
            component={ConsoleMeDataTable}
            configEndpoint={"/api/v2/requests_table_config"}
            queryString={""}
          />
          <ProtectedRoute
            exact
            path="/ui/catalog"
            component={ConsoleMeCatalog}
          />
          <Route component={NoMatch} />
        </Switch>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
