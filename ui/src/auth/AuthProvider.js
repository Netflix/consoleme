import React, { useEffect, useMemo, useState } from "react";
import AuthContext from "./AuthContext";

const AuthProvider = (props) => {
  const initialState = useMemo(
    () => {
      return {
        authCookieExpiration: null,
        currentServerTime: null,
        isAuthenticated: false,
        userInfo: null,
        login: async () => {
          const authResponse = await fetch(
            "/auth?redirect_url=" + window.location.href
          );
          const auth = await authResponse.json();
          if (auth.type === "redirect") {
            window.location.href = auth.redirect_url;
          } else {
            const userResponse = await fetch("/api/v1/profile");
            const userInfo = await userResponse.json();
            // Get local epoch time, compare to server time
            const localNow = new Date();
            const localTime = Math.round(localNow.getTime() / 1000);
            const timeDrift = Math.abs(localTime - auth.currentServerTime);
            // TODO: Should we raise an error if the drift is too much?
            if (timeDrift > 500) {
              console.log(
                "Time drift detected between your clock and the servers. ",
                "Please correct your lock: " + timeDrift + " seconds."
              );
            }

            if (userInfo) {
              setAuthState({
                ...authState,
                userInfo,
                isAuthenticated: true,
                authCookieExpiration: auth.authCookieExpiration,
                currentServerTime: auth.currentServerTime,
              });
            }
          }
        },
      };
    },
    [] // eslint-disable-line
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
