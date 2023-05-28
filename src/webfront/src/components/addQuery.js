import '../static/addQuery.css';
import React from 'react';
import Container from 'react-bootstrap/Container';
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import Row from 'react-bootstrap/Row';
import { addQuery } from '../db_conn';


function AddQueryFormDeny(props) {
    return (
        <h1>Access Denied</h1>
    )
}

function ShowQuerySubmit(msg) {
    return (
        <h1>{msg}</h1>
    )
}

class AddQueryFormAccept extends React.Component {

    async handleAddQuery(event) {
        event.preventDefault();
        let query_data = {}
        query_data['url'] = event.target.url.value
        query_data['sequence'] = event.target.sequence.value
        query_data['interval'] = event.target.interval.value
        query_data['cycles_limit'] = event.target.cycles_limit.value
        query_data['randomize'] = event.target.randomize.value
        query_data['eta'] = event.target.eta.value
        query_data['mode'] = event.target.mode.value
        query_data['is_recurring'] = event.target.is_recurring.value
        query_data['alias'] = event.target.alias.value
        query_data['cookies_filename'] = event.target.cookies_filename.value
        query_data['target_url'] = event.target.target_url.value
        query_data['alert_sound'] = event.target.alert_sound.value
        query_data['min_matches'] = event.target.min_matches.value
        query_data['cooldown'] = event.target.cooldown.value
        let resp = await addQuery(this.props.username, this.props.token, query_data)
        this.props.querySubmitSetter(true, resp['msg'])
    }

    render() {
        return (
                <Form className='addQuery-form' onSubmit={(event) => this.handleAddQuery(event)}>
                    <Form.Group >
                        <Row><Form.Label className='addQuery-label' column>URL</Form.Label><Form.Control className="addQuery-input" type="text" name="url"/></Row>
                        <Row><Form.Label className='addQuery-label' column>Sequence</Form.Label><Form.Control className="addQuery-input" type="text" name="sequence"/></Row>
                        <Row><Form.Label className='addQuery-label' column>Interval</Form.Label><Form.Control className="addQuery-input" type="text" name="interval"/></Row>
                        <Row><Form.Label className='addQuery-label' column>*Cycles limit</Form.Label><Form.Control className="addQuery-input" type="text" name="cycles_limit" defaultValue='0'/></Row>
                        <Row><Form.Label className='addQuery-label' column>*ETA</Form.Label><Form.Control className="addQuery-input" type="text" name="eta" placeholder='Y-m-d H:M:S'/></Row>
                        <Row><Form.Label className='addQuery-label' column>*Mode</Form.Label><Form.Control className="addQuery-input" type="text" name="mode" defaultValue='exists'/></Row>
                        <Row><Form.Label className='addQuery-label' column>*Randomize</Form.Label><Form.Control className="addQuery-input" type="text" name="randomize" defaultValue='0'/></Row>
                        <Row><Form.Label className='addQuery-label' column>*Recurring</Form.Label><Form.Control className="addQuery-input" type="text" name="is_recurring" defaultValue='false'/></Row>
                        <Row><Form.Label className='addQuery-label' column>*Alias</Form.Label><Form.Control className="addQuery-input" type="text" name="alias" placeholder='URL'/></Row>
                        <Row><Form.Label className='addQuery-label' column>*Cookies</Form.Label><Form.Control className="addQuery-input" type="text" name="cookies_filename" placeholder='None'/></Row>
                        <Row><Form.Label className='addQuery-label' column>*Target URL</Form.Label><Form.Control className="addQuery-input" type="text" name="target_url" placeholder='URL'/></Row>
                        <Row><Form.Label className='addQuery-label' column>*Sound</Form.Label><Form.Control className="addQuery-input" type="text" name="alert_sound" placeholder='Default'/></Row>
                        <Row><Form.Label className='addQuery-label' column>*Min matches</Form.Label><Form.Control className="addQuery-input" type="text" name="min_matches" defaultValue='1'/></Row>
                        <Row><Form.Label className='addQuery-label' column>*Cooldown</Form.Label><Form.Control className="addQuery-input" type="text" name="cooldown" defaultValue='0'/></Row>
                    </Form.Group>
                    <Button className="addQuery-submit" variant="primary" type="submit">
                        Add Query
                    </Button>
                </Form>
        )
    }   
}


export default class AddQuery extends React.Component {
    constructor(props){
        super(props)
        this.state = {
            querySubmitted: false,
            msg: ''
        }
    }

    querySubmitSetter(b, m) {this.setState({querySubmitted: b, msg: m})}

    render() {
        var AddQueryDisplay
        if (this.props.isLoggedIn){
            if (!this.state.querySubmitted){
                AddQueryDisplay = <AddQueryFormAccept
                                        username={this.props.username}
                                        token={this.props.token}
                                        querySubmitSetter={(b, m) => this.querySubmitSetter(b, m)}
                                    />;
            } else {
                AddQueryDisplay = ShowQuerySubmit(this.state.msg);
            }
        }else{
            AddQueryDisplay = <AddQueryFormDeny/>;
        }
        
        return (
            <Container className='addQuery-container'>
                {AddQueryDisplay}
            </Container>        
        );
    }
}
