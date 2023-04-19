import 'bootstrap/dist/css/bootstrap.min.css';
import './static/App.css';
import React from 'react';
import AppNavbar from "./components/navbar"
import Monitor from './components/monitor'
import AddQuery from './components/addQuery';
import Save from './components/save';
import LoginForm from './components/loginForm';
import EditQuery from './components/editQuery';
import DeleteQuery from './components/deleteQuery';



class DisplayManager extends React.Component {
  // Handle content (e.g. scan monitor, add query form) displayed on the page 
  constructor(props){
    super(props)
    this.childKey = 0;
  }
  render() {
    ++this.childKey;
    let CurrentScreen;
    switch(this.props.shot){
      case "monitor": CurrentScreen = <Monitor
                                      username={this.props.username}
                                      token={this.props.token}
                                      isLoggedIn={this.props.isLoggedIn}
                                      key={this.childKey}
                                      />; 
                                        break;
      case "add": CurrentScreen = <AddQuery
                                      username={this.props.username}
                                      token={this.props.token}
                                      isLoggedIn={this.props.isLoggedIn}
                                      key={this.childKey}
                                      />; break;
      case "save": CurrentScreen = <Save
                                      username={this.props.username}
                                      token={this.props.token}
                                      isLoggedIn={this.props.isLoggedIn}
                                      />; break;
      case "login": CurrentScreen = <LoginForm 
                                      setLoggedStatus={(s, u, p) => this.props.setLoggedStatus(s, u, p)}
                                      setShot={(s) => this.props.setShot(s)}
                                      isLoggedIn={this.props.isLoggedIn}
                                      />; break;
      case "edit": CurrentScreen = <EditQuery
                                      username={this.props.username}
                                      token={this.props.token}
                                      isLoggedIn={this.props.isLoggedIn}
                                      key={this.childKey}
                                      />; break;
      case "delete": CurrentScreen = <DeleteQuery
                                      username={this.props.username}
                                      token={this.props.token}
                                      isLoggedIn={this.props.isLoggedIn}
                                      key={this.childKey}
                                      />; break;
      default: CurrentScreen = <div className='App-err'><h1>N/A</h1></div>;
    }

    return (
      <div>
        {CurrentScreen}
      </div>
    );
  }
}



class App extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      shot: "login",
      isLoggedIn: false,
      username: '',
      token: '',
    };
  }

  // setters
  setCurrentShot(shot) {this.setState({shot: shot});}
  setLoggedStatus(success, username, token) {this.setState({isLoggedIn: success, username: username, token: token});}

  render() {
    return (
      <div className="App">
        <AppNavbar
        setShot={(s) => this.setCurrentShot(s)}
        username={this.state.username}
        isLoggedIn={this.state.isLoggedIn}
        />
        <DisplayManager 
        shot={this.state.shot}
        setShot={(s) => this.setCurrentShot(s)}
        setLoggedStatus={(s, u, p) => this.setLoggedStatus(s, u, p)}
        isLoggedIn={this.state.isLoggedIn}
        username={this.state.username}
        token={this.state.token}
        />
      </div>
    );
  }
}

export default App;
