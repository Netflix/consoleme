import React, { useContext } from "react";

const AuthContext = React.createContext({});

export const useAuth = () => useContext(AuthContext);

export default AuthContext;

export const checkJwtExpiration = (authState) => {
  const localNow = new Date();
  const localTime = Math.round(localNow.getTime() / 1000);
  // Check if jwt is expired or will expire in 30 seconds
  if (
    authState.isAuthenticated === true &&
    (!authState.authCookieExpiration ||
      authState.authCookieExpiration + 30 < localTime)
  ) {
    return false;
  } else if (authState.isAuthenticated === true) {
    return true;
  }
  return false;
};
