import '../static/loginForm.css'
import React from 'react';
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import Container from 'react-bootstrap/Container';
import { authenticateUser } from '../db_conn';



class LoginForm extends React.Component {
    async handleLogin(event) {
        event.preventDefault();
        let username = event.target.username.value;
        let password = event.target.password.value;
        let resp = await authenticateUser(username, password);
        let success = resp['auth_success']
        let token = resp['token']
        if (success === true) {
            this.props.setLoggedStatus(success, username, token);
            this.props.setShot('monitor');
        }
    }

    render() {
        return (
            <Container className="loginForm-container">
                <Form onSubmit={(event) => this.handleLogin(event)}>
                <Form.Group className="mb-3" controlId="formBasicEmail">
                    <Form.Label>Username</Form.Label>
                    <Form.Control className="loginForm-input" type="text" name="username"/>
                </Form.Group>
        
                <Form.Group className="mb-3" controlId="formBasicPassword">
                    <Form.Label>Password</Form.Label>
                    <Form.Control className="loginForm-input" type="password" name="password" />
                </Form.Group>
                <Button className="loginForm-submit" variant="primary" type="submit">
                    Login
                </Button>
                </Form>
            </Container>
          );
    }
  
}

export default LoginForm;