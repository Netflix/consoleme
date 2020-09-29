import React, { useEffect } from 'react';
import { useAuth } from './AuthContext';
import { Route, useRouteMatch } from 'react-router-dom';

const ProtectedRoute = ( props ) => {
    const { authState } = useAuth();
    const match = useRouteMatch(props);

    const handleLogin = async () => {
         await authState.login();
    };

    useEffect(() => {
        // Only process logic if the route matches
        if (!match) {
            return;
        }
        if(!authState.isAuthenticated) {
            handleLogin();
        }
    }, [authState.isAuthenticated, match]);

    if (!authState.isAuthenticated) {
        return null;
    }

    return (
        <Route
            { ...props }
        />
    );
};

export default ProtectedRoute;
