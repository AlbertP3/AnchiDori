import React from "react";
import Container from 'react-bootstrap/Container';
import '../static/deleteQuery.css'
import { getAllQueries, deleteQuery } from "../db_conn";
import Button from 'react-bootstrap/Button';



function DeleteQueryFormDeny(props) {
    return (
        <h1>Access Denied</h1>
    )
}

class DeleteQueryFormPick extends React.Component {

    constructor(props) {
        super(props)
        this.state = {
            content: ''
        }
    }

    async handleDeleteQuery(uid) {
        let resp = await deleteQuery(this.props.username, this.props.token, uid)
        this.props.setMsg(resp['msg'])
    }

    async handleShowAllQueries() {
        let resp = await getAllQueries(this.props.username, this.props.token)
        let b = []
        Object.keys(resp).forEach(async function(q) {
            b.push(
                    <Button className="deleteQuery-select" onClick={async () => this.handleDeleteQuery(resp[q]['uid'])} key={resp[q]['uid']}>
                        {resp[q]['alias']}
                    </Button>
            )
        }, this)
        this.setState({'content': b})
    }

    async componentDidMount() {
        await this.handleShowAllQueries()
    }
    
    render() {
        let c = this.state.content
        return (
            <div>
                {c}
            </div>
        )
    }
}

export default class DeleteQuery extends React.Component {
    constructor(props) {
        super(props)
        this.state = {
            eForm: <DeleteQueryFormDeny/>,
            msg: '',
            queryDeleted: false,
        }
    }
    
    setMsg(m) {this.setState({msg: m, queryDeleted:true})}

    render() {
        let c = this.state.eForm
        if (this.props.isLoggedIn) {
            if (!this.state.queryDeleted){
                c = <DeleteQueryFormPick
                    username={this.props.username}
                    token={this.props.token}
                    setMsg={(m)=>this.setMsg(m)}
                />
            } else {
                c = <h1>{this.state.msg}</h1>
            }
        }
        return (
            <Container className='deleteQuery-container'>
                {c}
            </Container>
        )
    }
}
