import _ from 'lodash'
import React, {Component} from 'react';
import {
    Dimmer,
    Loader,
    Sidebar,
    Segment
} from 'semantic-ui-react';
import {
    BrowserRouter,
    Redirect,
    Route,
    Switch
} from 'react-router-dom'
import ConsoleMeSidebar from "./components/Sidebar";
import ConsoleMeHeader from './components/Header';
import ConsoleMeLogin from './Login';
import ConsoleMeMain from './components/Main';
import ConsoleMeSelfService from "./components/SelfService";

import './App.css';

const LOCAL_KEY = 'consoleMeLocalStorage';


class App extends Component {
    constructor(props) {
        super(props);
        this.state = {
            isLoading: true,
            userSession: null,
            recentRoles: [],
        };
    }

    PrivateRoute = ({ component: ChildComponent, ...rest }) => (
        <Route
            {...rest}
            render={(props) => (
                this.state.userSession ? (
                    <Sidebar.Pushable>
                        <ConsoleMeSidebar
                            recentRoles={this.state.recentRoles}
                        />
                        <Sidebar.Pusher>
                            <Segment basic>
                                <ConsoleMeHeader
                                    userSession={this.state.userSession}
                                />
                                <ChildComponent
                                    {...props}
                                    {...rest}
                                />
                            </Segment>
                        </Sidebar.Pusher>
                    </Sidebar.Pushable>
                ) : (
                    <Redirect
                        to={{
                            pathname: '/login',
                            state: { from: props.location },
                        }}
                    />
                )
            )}
        />
    );

    componentDidMount() {
        fetch("/api/v1/profile").then((resp) => {
            resp.json().then((userSession) => {
                this.setState({
                    userSession,
                    isLoading: false,
                    recentRoles: this.getRecentRoles(),
                });
            });
        });
    }

    getRecentRoles() {
        const roles = localStorage.getItem(LOCAL_KEY);
        return roles ? JSON.parse(roles) : [];
    }

    setRecentRole(role) {
        const roles = _.uniq(this.getRecentRoles());
        const recentRoles = roles.unshift(role) > 5 ? roles.slice(0, 5) : roles;
        localStorage.setItem(LOCAL_KEY, JSON.stringify(recentRoles));
        this.setState({
            recentRoles,
        });
    }

    render() {
        const {PrivateRoute} = this;

        return (
            <BrowserRouter>
                <div className="App">
                    { this.state.isLoading
                        ?
                        <Dimmer active inverted>
                            <Loader size='large'>
                                Loading
                            </Loader>
                        </Dimmer>
                        :
                        <Switch>
                            <PrivateRoute
                                exact
                                path="/v2"  // TODO: UIREFACTOR: Remove V2 when this new UI is done
                                component={ConsoleMeMain}
                                setRecentRole={this.setRecentRole.bind(this)}
                            />
                            <PrivateRoute
                                exact
                                path="/v2/selfservice" // TODO: UIREFACTOR: Remove V2 when this new UI is done
                                component={ConsoleMeSelfService}
                            />
                            <Route
                                exact
                                path="/login"
                                component={ConsoleMeLogin}
                            />
                        </Switch>
                    }
                </div>
            </BrowserRouter>
        );
    }
}

export default App;