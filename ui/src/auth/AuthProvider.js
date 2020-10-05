import React, { useEffect, useMemo, useState,  } from "react";
import AuthContext from "./AuthContext";

const AuthProvider = (props) => {
  const initialState = useMemo(() => {
    return {
      authCookieExpiration: null,
      currentServerTime: null,
      isAuthenticated: false,
      userInfo: null,
      login: async () => {
        const authResponse = await fetch(
            "/auth?force_redirect=false&redirect_url=" + window.location.href
        );
        const auth = await authResponse.json();
        if (auth.type === "redirect") {
          window.location.href = auth.redirect_url;
        } else {
          const userResponse = await fetch("/api/v1/profile");
          const userInfo = await userResponse.json();
          if (userInfo) {
            setAuthState({
              ...authState,
              isAuthenticated: true,
              userInfo,
              authCookieExpiration: auth.authCookieExpiration,
              currentServerTime: auth.currentServerTime,
            });
          }
        }
      }
    }}, []
  );

  const [authState, setAuthState] = useState(initialState);

  useEffect(() => {
    console.log("AUTH STATE: ", authState);

    // if auth state changed trigger something here
    // if not authenticated redirect to login?
  }, [authState]);

  return (
    <AuthContext.Provider value={{ authState }}>
      {props.children}
    </AuthContext.Provider>
  );
};

export default AuthProvider;
