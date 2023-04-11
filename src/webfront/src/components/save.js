import '../static/save.css';
import React from 'react';
import Container from 'react-bootstrap/Container';
import { saveQuery } from '../db_conn';


function SaveDeny(props) {
    return (
        <h1>Access Denied</h1>
    )
}

class SaveForm extends React.Component {

    constructor(props) {
        super(props)
        this.state = {
            msg: '',
        }
    }

    async handleSave(){
        let resp = await saveQuery(this.props.username, this.props.token)
        this.setState({msg: resp['msg']})
    }

    async componentDidMount() {
        await this.handleSave()
    }

    render() {
        return (
            <Container>
                <h1>{this.state.msg}</h1>
            </Container>
        );
    }
}

class Save extends React.Component {
    render() {
        if(this.props.isLoggedIn){
            var SaveFormOrDeny = <SaveForm
                username={this.props.username}
                token={this.props.token}
            />;
        }else{
            var SaveFormOrDeny = <SaveDeny/>;
        }

        return (
            <Container className='save-container'>
                {SaveFormOrDeny}
            </Container>
        );
    }
}

export default Save;