import Cookies from "js-cookie";
import { useEffect, useState } from "react";
import { useAuth } from "./AuthContext";


export const useApi = (url, options = {}) => {
    const { authState } = useAuth();
    const [state, setState] = useState({
        error: null,
        loading: true,
        data: null,
    });

    useEffect(() => {
        (async () => {
            if (!authState.isAuthenticated) {
                return;
            }

            try {
                const xsrf = Cookies.get("_xsrf");
                const { body, headers, method = "post", ...fetchOptions } = options;
                const res = await fetch(url, {
                    body,
                    ...fetchOptions,
                    headers: {
                        ...headers,
                        'Content-type': 'application/json',
                        'X-Xsrftoken': xsrf,
                    },
                    method,
                });
                setState({
                    ...state,
                    data: await res.json(),
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
    }, [authState]);

    return state;
};