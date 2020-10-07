import Cookies from "js-cookie";
import { useEffect, useState } from "react";
import { useAuth } from "./AuthContext";

export const useApi = (url, options = {}) => {
  const { isAuthenticated, login } = useAuth();
  const [state, setState] = useState({
    error: null,
    loading: true,
    data: null,
  });

  useEffect(() => {
    (async () => {
      if (!isAuthenticated()) {
        await login();
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
          await login();
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
