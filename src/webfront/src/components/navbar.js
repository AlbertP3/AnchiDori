import '../static/navbar.css';
import React from 'react';
import Container from 'react-bootstrap/Container';
import Nav from 'react-bootstrap/Nav';
import Navbar from 'react-bootstrap/Navbar';



class AppNavbar extends React.Component {
    render() {
        var accInfo
        switch(this.props.isLoggedIn){
            case true: accInfo = <Nav.Link className="nav-acc">{this.props.username}</Nav.Link>; break;
            default: accInfo = <Nav.Link className="nav-acc" onClick={() => this.props.setShot('login')}>Login</Nav.Link>;
        }
    return (
        <Navbar bg="dark" expand="lg">
        <Container>
            <Navbar.Brand>AnchiDori</Navbar.Brand>
            <Navbar.Toggle aria-controls="basic-navbar-nav" />
            <Navbar.Collapse id="basic-navbar-nav">
            <Nav className="me-auto">
                <Nav.Link onClick={() => this.props.setShot('monitor')}>Monitor</Nav.Link>
                <Nav.Link onClick={() => this.props.setShot('add')}>Add</Nav.Link>
                <Nav.Link onClick={() => this.props.setShot('edit')}>Edit</Nav.Link>
                <Nav.Link onClick={() => this.props.setShot('save')}>Save</Nav.Link>
                <Nav.Link onClick={() => this.props.setShot('settings')}>Settings</Nav.Link>
                <Nav.Link onClick={() => this.props.setShot('delete')}>Delete</Nav.Link>
            </Nav>
                {accInfo}
            </Navbar.Collapse>
        </Container>
        </Navbar>
    );
    }
}

export default AppNavbar;
