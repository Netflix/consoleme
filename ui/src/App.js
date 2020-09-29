import _ from "lodash";
import React, { useState, useEffect } from "react";
import { BrowserRouter, Redirect, Route, Switch } from "react-router-dom";
import { Dimmer, Loader, Segment } from "semantic-ui-react";

import AuthProvider from "./auth/AuthProvider";
import ProtectedRoute from "./auth/ProtectedRoute";

import ConsoleMeHeader from "./components/Header";
import ConsoleMeSidebar from "./components/Sidebar";
import ConsoleMeCatalog from "./components/Catalog";
import ConsoleMeDataTable from "./components/ConsoleMeDataTable";
import ConsoleMeSelfService from "./components/SelfService";
// import ConsoleMeLogin from "./components/Login";

const LOCAL_KEY = "consoleMeLocalStorage";

function App() {
    const [isLoading, setLoading] = useState(false);

    return (
        <BrowserRouter>
            <AuthProvider>
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
                        exact
                        path="/ui/"
                        component={ConsoleMeDataTable}
                        configEndpoint={"/api/v2/role_table_config"}
                        queryString={""}
                        setRecentRole={() => {
                            console.log('set roles');
                        }}
                    />
                    <Route
                        exact
                        path="/ui/selfservice"
                        component={ConsoleMeSelfService}
                    />
                    <ProtectedRoute
                        exact
                        path="/ui/catalog"
                        component={ConsoleMeCatalog}
                    />
                </Segment>
            </AuthProvider>
        </BrowserRouter>
    );
}

export default App;