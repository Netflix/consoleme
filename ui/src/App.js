import React, {Component} from 'react';
import {
  Sidebar,
  Segment
} from 'semantic-ui-react';
import {
  BrowserRouter,
  Route,
  Switch
} from 'react-router-dom'
import './App.css';

import ConsoleMeSidebar from "./components/Sidebar";
import ConsoleMeHeader from './components/Header';

class App extends Component {
  constructor(props) {
    super(props);
    this.state = {
      isLoading: true,
      userSession: null,
      recentRoles: [],
    };
  }

  componentDidMount() {
  }

  render() {
    return (
        <BrowserRouter>
          <Switch>
            <Route>
              <div className="App">
                <Sidebar.Pushable>
                  <ConsoleMeSidebar
                      recentRoles={this.state.recentRoles}
                  />
                  <Sidebar.Pusher>
                    <Segment basic>
                      <ConsoleMeHeader
                          userSession={this.state.userSession}
                      />
                      <div />
                    </Segment>
                  </Sidebar.Pusher>
                </Sidebar.Pushable>
              </div>
            </Route>
          </Switch>
        </BrowserRouter>
    );
  }
}

export default App;