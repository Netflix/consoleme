import React, { createContext, useContext, useReducer } from "react";
import { getCookie } from "../helpers/utils";

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
    const user = await sendRequestCommon(null, "/api/v2/user_profile", "get");
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

        if (response.ok) {
          return response.json();
        } else {
          throw new Error(response);
        }
      })
      .then((data) => {
        return data;
      })
      .catch((error) => {
        console.error(`Exception Raised: ${error}`);
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
