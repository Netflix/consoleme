import React, { useReducer } from "react";
import AuthContext from "./AuthContext";
import { initialAuthState } from "./AuthState";

const reducer = (state, action) => {
  switch (action.type) {
    case "LOGIN": {
      const { user, auth } = action;
      return {
        ...state,
        auth,
        user,
      };
    }
    case "LOGOUT": {
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
    const auth = await fetch(
      "/auth?redirect_url=" + window.location.href
    ).then((res) => res.json());
    // redirect to IDP for authentication.
    if (auth.type === "redirect") {
      window.location.href = auth.redirect_url;
    }
    // User is now authenticated so retrieve user profile.
    const user = await fetch("/api/v1/profile").then((res) => res.json());
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

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export default AuthProvider;
