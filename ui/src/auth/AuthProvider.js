import React, { useEffect, useMemo, useReducer, useState } from "react";
import AuthContext from "./AuthContext";
import { initialAuthState } from "./AuthState";


const reducer = (state, action) => {
  switch (action.type) {
    case 'LOGIN': {
      const { user, auth } = action;
      return {
        ...state,
        auth,
        user,
      };
    }
    case 'LOGOUT': {
      return {
        ...state,
        auth: null,
        user: null,
      };
    }
    default: {
      return state;
    }
  }
};

const AuthProvider = ({ children }) => {
  const [state, dispatch] = useReducer(reducer, initialAuthState);

  const login = async () => {
    // First check whether user is currently authenticated by using the backend auth endpoint.
    const auth = await fetch("/auth?redirect_url=" + window.location.href).then(res => res.json());
    // redirect to IDP for authentication.
    if (auth.type === "redirect") {
      window.location.href = auth.redirect_url;
    }
    // User is now authenticated so retrieve user profile.
    const user = await fetch("/api/v1/profile").then(res => res.json());
    dispatch({
      type: "LOGIN",
      auth,
      user,
    });
  };

  const logout = () => {
    dispatch({
      type: "LOGOUT",
    });
  };

  // check the current JWT (exist in the cookie) expiration time that given by the backend.
  const isAuthenticated = () => {
    const { auth, user } = state;
    if (user && auth) {
      const { authCookieExpiration, currentServerTime } = auth;
      const localTime = Math.round((new Date()).getTime() / 1000);
      const timeDrift = Math.abs(localTime - currentServerTime);
      // TODO, check time drift and raise error
      if (timeDrift > 500) {
        console.log(
            "Time drift detected between your clock and the servers. ",
            "Please correct your lock: " + timeDrift + " seconds."
        );
        return false;
      }
      // check JWT expiration
      return authCookieExpiration + 30 >= localTime;
    }
    return false;
  };

  return (
    <AuthContext.Provider
      value={{
        ...state,
        isAuthenticated,
        login,
        logout
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export default AuthProvider;
