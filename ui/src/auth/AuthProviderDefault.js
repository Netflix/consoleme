import React, { createContext, useContext, useReducer } from "react";
import { getCookie } from "../helpers/utils";
import ReactGA from "react-ga";

const initialAuthState = {
  user: null, // user profile data
  isSessionExpired: false,
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
    case "SESSION_EXPIRED": {
      const { isSessionExpired } = action;
      return {
        ...state,
        isSessionExpired,
      };
    }
    default: {
      return state;
    }
  }
};

export const AuthProvider = ({ children }) => {
  const [state, dispatch] = useReducer(reducer, initialAuthState);

  const login = async (history) => {
    try {
      // First check whether user is currently authenticated by using the backend auth endpoint.
      const auth = await fetch("/auth?redirect_url=" + window.location.href, {
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          Accept: "application/json",
        },
      }).then((res) => res.json());

      // ConsoleMe backend returns a response containing a redirection to IDP for authentication.
      if (auth.type === "redirect" && auth.reason === "unauthenticated") {
        window.location.href = auth.redirect_url;
      } else if (auth.status === 401) {
        // handle the session expiration if the response status is 401 for re-authentication
        setIsSessionExpired(true);
        return;
      }

      // User is now authenticated so retrieve user profile.
      const user = await sendRequestCommon(null, "/api/v2/user_profile", "get");

      // If backend Consoleme is configured with google analytics, let's set it up here
      if (user?.site_config?.google_analytics?.tracking_id) {
        ReactGA.initialize(
          user.site_config.google_analytics.tracking_id,
          user.site_config.google_analytics.options
        );
        user.google_analytics_initialized = true;
      } else {
        user.google_analytics_initialized = false;
      }

      dispatch({
        type: "LOGIN",
        user,
      });

      // Cloud administrators can override the initial landing URL for users by providing a configuration on the backend
      if (user?.site_config?.landing_url && window.location.pathname === "/") {
        history.push(user.site_config.landing_url);
      }
    } catch (error) {
      // If session expires, fetch will return the error page showing re-authentication is required and raise an
      // exception from handling the html file instead of application/json type.
      // Toggle the re-authentication modal to login back users if it's using ALB type of authentication system.
      console.error(error);
      setIsSessionExpired(true);
    }
  };

  const logout = () => {
    dispatch({
      type: "LOGOUT",
    });
  };

  const setIsSessionExpired = (isSessionExpired) => {
    dispatch({
      type: "SESSION_EXPIRED",
      isSessionExpired,
    });
  };

  const sendRequestCommon = async (
    json,
    location = window.location.href,
    method = "post"
  ) => {
    let body = null;

    if (json) {
      body = JSON.stringify(json);
    }

    if (state.isSessionExpired) {
      return null;
    }

    const xsrf = getCookie("_xsrf");
    return fetch(location, {
      method: method,
      headers: {
        "Content-type": "application/json",
        "X-Xsrftoken": xsrf,
        "X-Requested-With": "XMLHttpRequest",
        Accept: "application/json",
      },
      body: body,
    })
      .then((response) => {
        if (
          response.status === 403 &&
          response.type === "redirect" &&
          response.reason === "unauthenticated"
        ) {
          fetch("/auth?redirect_url=" + window.location.href, {
            headers: {
              "X-Requested-With": "XMLHttpRequest",
              Accept: "application/json",
            },
          }).then((resp) => {
            if (resp.type === "redirect") {
              window.location.href = resp.redirect_url;
            }
          });
        } else if (response.status === 401) {
          setIsSessionExpired(true);
        }

        try {
          return response.json();
        } catch {
          throw new Error(
            `Status: ${response.status}, Reason: ${response.statusText}`
          );
        }
      })
      .then((data) => {
        return data;
      })
      .catch((error) => {
        // fetch will raise an exception if it fetches an data that is not json such as html showing re-authentication
        // is required. This is to handle such case where ALB type of authentication is being used.
        console.error(error);
        setIsSessionExpired(true);
        return null;
      });
  };

  const sendRequestV2 = async (requestV2) => {
    const response = await sendRequestCommon(requestV2, "/api/v2/request");

    if (response) {
      const { request_created, request_id, request_url, errors } = response;
      if (request_created === true) {
        if (requestV2.admin_auto_approve && errors === 0) {
          return {
            message: `Successfully created and applied request: [${request_id}](${request_url}).`,
            request_created,
            error: false,
          };
        } else if (errors === 0) {
          return {
            message: `Successfully created request: [${request_id}](${request_url}).`,
            request_created,
            error: false,
          };
        } else {
          return {
            // eslint-disable-next-line max-len
            message: `This request was created and partially successful: : [${request_id}](${request_url}). But the server reported some errors with the request: ${JSON.stringify(
              response
            )}`,
            request_created,
            error: true,
          };
        }
      }
      return {
        message: `Server reported an error with the request: ${JSON.stringify(
          response
        )}`,
        request_created,
        error: true,
      };
    } else {
      return {
        message: `"Failed to submit request: ${JSON.stringify(response)}`,
        request_created: false,
        error: true,
      };
    }
  };

  const sendProposedPolicyWithHooks = async (
    command,
    change,
    newStatement,
    requestID,
    setIsLoading,
    setButtonResponseMessage,
    reloadDataFromBackend
  ) => {
    setIsLoading(true);
    const request = {
      modification_model: {
        command,
        change_id: change.id,
      },
    };
    if (newStatement) {
      request.modification_model.policy_document = JSON.parse(newStatement);
    }
    await sendRequestCommon(
      request,
      "/api/v2/requests/" + requestID,
      "PUT"
    ).then((response) => {
      if (!response) {
        return;
      }
      if (
        response.status === 403 ||
        response.status === 400 ||
        response.status === 500
      ) {
        // Error occurred making the request
        setIsLoading(false);
        setButtonResponseMessage([
          {
            status: "error",
            message: response.message,
          },
        ]);
      } else {
        // Successful request
        setIsLoading(false);
        setButtonResponseMessage(
          response.action_results.reduce((resultsReduced, result) => {
            if (result.visible === true) {
              resultsReduced.push(result);
            }
            return resultsReduced;
          }, [])
        );
        reloadDataFromBackend();
      }
    });
  };

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        logout,
        setIsSessionExpired,
        sendRequestCommon,
        sendRequestV2,
        sendProposedPolicyWithHooks,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
