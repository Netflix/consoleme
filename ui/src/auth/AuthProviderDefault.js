import React, { createContext, useContext, useReducer } from "react";

const initialAuthState = {
  user: null, // user profile data
};

const AuthContext = createContext(initialAuthState);

export const useAuth = () => useContext(AuthContext);

const reducer = (state, action) => {
  switch (action.type) {
    case "LOGIN": {
      const { user } = action;
      return {
        ...state,
        user,
      };
    }
    case "LOGOUT": {
      return {
        ...state,
        user: null,
      };
    }
    default: {
      return state;
    }
  }
};

export const AuthProvider = ({ children }) => {
  const [state, dispatch] = useReducer(reducer, initialAuthState);

  const login = async () => {
    // First check whether user is currently authenticated by using the backend auth endpoint.
    const auth = await fetch("/auth?redirect_url=" + window.location.href, {
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        Accept: "application/json",
      },
    }).then((res) => res.json());
    // redirect to IDP for authentication.
    if (auth.type === "redirect") {
      window.location.href = auth.redirect_url;
    }
    // User is now authenticated so retrieve user profile.
    const xsrf = document.cookie.match("_xsrf=([^;]*)");
    const user = await sendRequestTarget(null, "/api/v2/user_profile", "get", xsrf);
    dispatch({
      type: "LOGIN",
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

export async function sendRequestTarget(
  json,
  location = window.location.href,
  method = "post",
  xsrf,
) {
  let body = null;
  if (json) {
    body = JSON.stringify(json);
  }
  const rawResponse = await fetch(location, {
    method: method,
    headers: {
      "Content-type": "application/json",
      "X-Xsrftoken": xsrf,
      "X-Requested-With": "XMLHttpRequest",
      Accept: "application/json",
    },
    body: body,
  });
  const response = await rawResponse;

  let resJson;
  try {
    resJson = await response.json();
    if (
      response.status === 403 &&
      resJson.type === "redirect" &&
      resJson.reason === "unauthenticated"
    ) {
      const auth = await fetch("/auth?redirect_url=" + window.location.href, {
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          Accept: "application/json",
        },
      }).then((res) => res.json());
      // redirect to IDP for authentication.
      if (auth.type === "redirect") {
        window.location.href = auth.redirect_url;
      }
    }
  } catch (e) {
    resJson = response;
  }

  return resJson;
}
