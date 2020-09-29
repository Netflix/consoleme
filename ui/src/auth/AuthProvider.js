import React, { useState, useEffect } from 'react';
import AuthContext from './AuthContext';


const AuthProvider = (props) => {
    const initialAuthState = {
        isAuthenticated: false,
        userSession: {},
        login: async () => {
            const response = await fetch("/api/v1/profile");
            const userSession = await response.json();
            // setAuthState({
            //     ...authState,
            //     userSession,
            //     isAuthenticated: true,
            // });
        }
    };

    const [authState, setAuthState] = useState(initialAuthState);

    useEffect( () => {
        // if auth state changed trigger something here
        // if not authenticated redirect to login?
    }, [authState]);

    return (
        <AuthContext.Provider value={ { authState } }>
            {props.children}
        </AuthContext.Provider>
    );
};

export default AuthProvider;