import React from "react";
import Container from 'react-bootstrap/Container';
import '../static/editQuery.css'
import { getAllQueries, editQuery } from "../db_conn";
import Button from 'react-bootstrap/Button';
import Row from 'react-bootstrap/Row';
import Form from 'react-bootstrap/Form';


function EditQueryFormDeny(props) {
    return (
        <h1>Access Denied</h1>
    )
}

class EditQueryFormSelected extends React.Component {

    async handleEditQuery(event) {
        event.preventDefault();
        let query_data = {}
        query_data['uid'] = this.props.data['uid']
        query_data['url'] = event.target.url.value
        query_data['sequence'] = event.target.sequence.value
        query_data['interval'] = event.target.interval.value
        query_data['cycles_limit'] = event.target.cycles_limit.value
        query_data['randomize'] = event.target.randomize.value
        query_data['found'] = event.target.found.value
        query_data['eta'] = event.target.eta.value
        query_data['mode'] = event.target.mode.value
        query_data['is_recurring'] = event.target.is_recurring.value
        query_data['alias'] = event.target.alias.value
        query_data['cookies_filename'] = event.target.cookies_filename.value
        query_data['target_url'] = event.target.target_url.value
        query_data['alert_sound'] = event.target.alert_sound.value
        query_data['min_matches'] = event.target.min_matches.value
        query_data['cooldown'] = event.target.cooldown.value
        let resp = await editQuery(this.props.username, this.props.token, query_data)
        this.props.setQueryEdited(true, resp['msg'])
    }

    render() {
        let data = this.props.data;
        data['target_url'] = data['target_url'] !== data['url'] ? data['target_url'] : null
        return (
            <Form className='editQuery-form' onSubmit={async (event) => this.handleEditQuery(event)}>
            <Form.Group >
                <Row><Form.Label className='editQuery-label' column>URL</Form.Label><Form.Control className="editQuery-input" type="text" name="url" defaultValue={data['url']}/></Row>
                <Row><Form.Label className='editQuery-label' column>Sequence</Form.Label><Form.Control className="editQuery-input" type="text" name="sequence" defaultValue={data['sequence']}/></Row>
                <Row><Form.Label className='editQuery-label' column>Interval</Form.Label><Form.Control className="editQuery-input" type="text" name="interval" defaultValue={data['interval']}/></Row>
                <Row><Form.Label className='editQuery-label' column>Cycles limit</Form.Label><Form.Control className="editQuery-input" type="text" name="cycles_limit" defaultValue={data['cycles_limit']}/></Row>
                <Row><Form.Label className='editQuery-label' column>Found</Form.Label><Form.Control className="editQuery-input" type="text" name="found" defaultValue={data['found']}/></Row>
                <Row><Form.Label className='editQuery-label' column>ETA</Form.Label><Form.Control className="editQuery-input" type="text" name="eta" defaultValue={data['eta']}/></Row>
                <Row><Form.Label className='editQuery-label' column>Randomize</Form.Label><Form.Control className="editQuery-input" type="text" name="randomize" defaultValue={data['randomize']}/></Row>
                <Row><Form.Label className='editQuery-label' column>Mode</Form.Label><Form.Control className="editQuery-input" type="text" name="mode" defaultValue={data['mode']}/></Row>
                <Row><Form.Label className='editQuery-label' column>Recurring</Form.Label><Form.Control className="editQuery-input" type="text" name="is_recurring" defaultValue={data['is_recurring']}/></Row>
                <Row><Form.Label className='editQuery-label' column>Alias</Form.Label><Form.Control className="editQuery-input" type="text" name="alias" placeholder='URL' defaultValue={data['alias']}/></Row>
                <Row><Form.Label className='editQuery-label' column>Cookies</Form.Label><Form.Control className="editQuery-input" type="text" name="cookies_filename" placeholder='None' defaultValue={data['cookies_filename']}/></Row>
                <Row><Form.Label className='editQuery-label' column>Target URL</Form.Label><Form.Control className="editQuery-input" type="text" name="target_url" placeholder='URL' defaultValue={data['target_url']}/></Row>
                <Row><Form.Label className='editQuery-label' column>Sound</Form.Label><Form.Control className="editQuery-input" type="text" name="alert_sound" placeholder='Default' defaultValue={data['alert_sound']}/></Row>
                <Row><Form.Label className='editQuery-label' column>Min matches</Form.Label><Form.Control className="editQuery-input" type="text" name="min_matches" defaultValue={data['min_matches']}/></Row>
                <Row><Form.Label className='editQuery-label' column>Cooldown</Form.Label><Form.Control className="editQuery-input" type="text" name="cooldown" defaultValue={data['cooldown']}/></Row>
            </Form.Group>
            <Button className="editQuery-submit" variant="primary" type="submit">
                Edit Query
            </Button>
            </Form>
        )
    }
}


class EditQueryFormPick extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            content: <div></div>,
        }
    }

    async handleShowAllQueries() {
        let resp = await getAllQueries(this.props.username, this.props.token)
        let b = []
        Object.keys(resp).forEach(async function(q) {
            b.push(
                    <Button className="editQuery-select" onClick={() => this.props.setEditMode(resp[q])} key={resp[q]['uid']}>
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


export default class EditQuery extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            eForm: <EditQueryFormDeny/>,
            pickMode: true,
            data: {},
            queryEdited: false,
            editQueryMsg: '',
        }
    }

    setEditMode(data) {this.setState({data: data, pickMode: false})}
    setQueryEdited(b, m) {this.setState({queryEdited: b, editQueryMsg: m})}

    render() {
        let c = this.state.eForm
        if (this.props.isLoggedIn) {
            if (this.state.pickMode) {
                c = <EditQueryFormPick
                        username={this.props.username}
                        token={this.props.token}
                        setEditMode={(d) => this.setEditMode(d)}
                    />;
            } else if (!this.state.queryEdited) {
                c = <EditQueryFormSelected
                        username={this.props.username}
                        token={this.props.token}
                        data={this.state.data}
                        setQueryEdited={(b, m) => this.setQueryEdited(b, m)}
                    />;
            } else {
                c = <h1>{this.state.editQueryMsg}</h1>
            }
        }

        return (
            <Container className='editQuery-container'>
                {c}
            </Container>        
        );
    }
}