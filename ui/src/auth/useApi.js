import Cookies from "js-cookie";
import { useEffect, useState } from "react";
import { useAuth, checkJwtExpiration } from "./AuthContext";

export const useApi = (url, options = {}) => {
  const { authState } = useAuth();
  const [state, setState] = useState({
    error: null,
    loading: true,
    data: null,
  });

  const handleLogin = async () => {
    await authState.login();
  };

  useEffect(() => {
    (async () => {
      if (!checkJwtExpiration(authState) || !authState.isAuthenticated) {
        handleLogin();
      }

      try {
        const xsrf = Cookies.get("_xsrf");
        const { body, headers, method = "post", ...fetchOptions } = options;
        const res = await fetch(url, {
          body,
          ...fetchOptions,
          headers: {
            ...headers,
            "Content-type": "application/json",
            "X-Xsrftoken": xsrf,
          },
          method,
        });
        const resJson = await res.json();
        if (res.status === 403 && res.reason === "unauthenticated") {
          await handleLogin();
        }
        setState({
          ...state,
          data: resJson,
          error: null,
          loading: false,
        });
      } catch (error) {
        setState({
          ...state,
          error,
          loading: false,
        });
      }
    })();
  }, [url]); // eslint-disable-line

  return state;
};
