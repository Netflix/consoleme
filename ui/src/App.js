import React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import { AuthProvider } from "./auth/AuthProviderDefault";
import { NotificationProvider } from "./components/hooks/notifications";
import ProtectedRoute from "./auth/ProtectedRoute";
import ConsoleMeSelectRoles from "./components/roles/SelectRoles";
import ConsoleMePolicyTable from "./components/policy/PolicyTable";
import ConsoleMeRequestTable from "./components/request/RequestTable";
import ConsoleMeSelfService from "./components/selfservice/SelfService";
import ConsoleMeDynamicConfig from "./components/DynamicConfig";
import PolicyRequestReview from "./components/request/PolicyRequestsReview";
import PolicyEditor from "./components/policy/PolicyEditor";
import ConsoleLogin from "./components/ConsoleLogin";
import ConsoleMeChallengeValidator from "./components/challenge/ConsoleMeChallengeValidator";
import CreateCloneFeature from "./components/roles/CreateCloneFeature";
import Login from "./components/Login";
import Logout from "./components/Logout";
import NoMatch from "./components/NoMatch";
import AuthenticateModal from "./components/AuthenticateModal";
import GenerateConfig from "./components/generate_config/GenerateConfig";

function App() {
  return (
    <BrowserRouter>
      <Switch>
        <ProtectedRoute
          key="roles"
          exact
          path="/"
          component={ConsoleMeSelectRoles}
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
          component={ConsoleMePolicyTable}
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
          component={ConsoleMeRequestTable}
        />
        <ProtectedRoute
          key="resource_policy"
          path="/policies/edit/:accountID/:serviceType/*/:resourceName"
          component={PolicyEditor}
        />
        <ProtectedRoute
          key="iamrole_policy"
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
          key="generate_config"
          exact
          path="/generate_config"
          component={GenerateConfig}
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
        <ProtectedRoute
          key="create_role"
          exact
          path="/create_role"
          component={CreateCloneFeature}
        />
        <ProtectedRoute key="logout" exact path="/logout" component={Logout} />
        <Route key="login" exact path="/login" component={Login} />
        <Route component={NoMatch} />
      </Switch>
      <AuthenticateModal />
    </BrowserRouter>
  );
}

const AuthWrapper = () => {
  return (
    <AuthProvider>
      <NotificationProvider>
        <App />
      </NotificationProvider>
    </AuthProvider>
  );
};

export default AuthWrapper;
