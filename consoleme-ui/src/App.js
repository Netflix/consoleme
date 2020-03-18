import Main from './Main';
import Login from './Login';
import React from 'react';
import { BrowserRouter, Route, Switch } from 'react-router-dom'

function App() {
  return (
    <BrowserRouter>
      <Switch>
        <Route exact path="/" component={Main}/>
        <Route path="/login" component={Login}/>
      </Switch>
    </BrowserRouter>)
}

export default App;