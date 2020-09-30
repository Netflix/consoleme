import React, { useEffect } from 'react';
import { useAuth } from './AuthContext';
import { Route, useRouteMatch } from 'react-router-dom';
import { Dimmer, Loader, Segment } from "semantic-ui-react";

import ConsoleMeHeader from "../components/Header";
import ConsoleMeSidebar from "../components/Sidebar";


const ProtectedRoute = ( props ) => {
    const { authState } = useAuth();
    const match = useRouteMatch(props);

    const handleLogin = async () => {
        await authState.login();
    };

    useEffect(() => {
        if (!match) {
            return;
        }
        if(!authState.isAuthenticated) {
            handleLogin();
        }
    }, [authState.isAuthenticated, match]);

    if (!authState.isAuthenticated) {
        return (
            <Dimmer active inverted>
                <Loader size="large">Loading</Loader>
            </Dimmer>
        );
    }

    const { component: Component, ...rest } = props;
    return (
        <React.Fragment>
            <ConsoleMeHeader />
            <ConsoleMeSidebar
                recentRoles={["example_role_1", "example_role_2", "example_role_3"]}
            />
            <Segment
                basic
                style={{
                    marginTop: "72px",
                    marginLeft: "240px",
                }}
            >
                <Route
                    { ...rest }
                    render={(props) => {
                        return (
                            <Component
                                {...props}
                                {...rest}
                            />
                        );
                    }}
                />
            </Segment>
        </React.Fragment>
    );
};

export default ProtectedRoute;
