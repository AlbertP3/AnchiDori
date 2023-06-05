import '../static/settings.css';
import React from 'react';
import Container from 'react-bootstrap/Container';
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import Row from 'react-bootstrap/Row';
import { getSettings, editSettings } from "../db_conn";


function SettingsFormDeny(props) {
    return (
        <h1>Access Denied</h1>
    )
}

class SettingsFormDisplay extends React.Component {

    async handleSettings(event) {
        event.preventDefault();
        let settings_data = {}
        settings_data['autosave'] = String(event.target.autosave.value).toLowerCase() === "true"
        settings_data['notes'] = event.target.notes.value
        let resp = await editSettings(this.props.username, this.props.token, settings_data)
        this.props.setSettingsEdited(false, resp['msg'])
    }

    render() {
        let data = this.props.data;
        return (
            <Form className='settings-form' onSubmit={async (event) => this.handleSettings(event)}>
            <Form.Group >
                <Row><Form.Label className='settings-label' column>AutoSave</Form.Label>
                    <Form.Select className="settings-input" type="text" name="autosave" value={data['autosave']}>
                        <option>true</option>
                        <option>false</option>
                </Form.Select></Row>
                <Row><Form.Label className='settings-label' column>Notes</Form.Label><Form.Control as="textarea" rows="7" type="text" className="settings-input" name="notes" defaultValue={data['notes']}/></Row>
            </Form.Group>
            <Button className="settings-submit" variant="primary" type="submit">
                Save
            </Button>
            </Form>
        )
    }
}


export default class Settings extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            eForm: <SettingsFormDeny/>,
            displayMode: true,
            data: {},
            settingsEditMsg: '',
        }
    }

    setSettingsEdited(b, m) {this.setState({displayMode: b, settingsEditMsg: m})}

    async handleShowSettings() {
        let resp = await getSettings(this.props.username, this.props.token)
        this.setState({data: resp})
    }

    async componentDidMount() {
        await this.handleShowSettings()
    }

    render() {
        let c = this.state.eForm
        if (this.props.isLoggedIn) {
            if (this.state.displayMode) {
                c = <SettingsFormDisplay
                        username={this.props.username}
                        token={this.props.token}
                        data={this.state.data}
                        setSettingsEdited={(b, m) => this.setSettingsEdited(b, m)}
                    />;
            } else {
                c = <h1>{this.state.settingsEditMsg}</h1>
            }
        }

        return (
            <Container className='settings-container'>
                {c}
            </Container>        
        );
    }
}