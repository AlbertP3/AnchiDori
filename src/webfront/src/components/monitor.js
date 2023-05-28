import Table from 'react-bootstrap/Table';
import '../static/monitor.css';
import { getDashboard, getSound } from '../db_conn';
import React from 'react';



export default class Monitor extends React.Component{

    constructor() {
        super();
        this.state = {
        content: <tbody></tbody>,
        last_run: '',
        refresh_rate: process.env.REACT_APP_REFRESH_SECONDS,
        unnotifiedNew: false,
        QSTAT_CODES: {
            '-1': 'Not Yet Ran',
            '0': 'OK',
            '1': 'Access Denied',
            '2': 'Connection Lost',
        }
        }
    }

    async getContent(){
        let d = await getDashboard(this.props.username, this.props.token);
        let b = []
        Object.keys(d).forEach(async function(q) {
            if ( parseInt(d[q]['cycles_limit'])>=0 ){
                let n = await this.getNotificationSign(d[q]['found'], d[q]['is_new'])
                let c = (d[q]['found'] && d[q]['is_recurring']) ? d[q]['cooldown'] : ''
                let r = (d[q]['is_recurring']) ? 'True' : ''
                let status_ = this.state.QSTAT_CODES[d[q]['status']]
                b.push(<tr key={d[q]['uid']}>
                    <td><a href={d[q]['target_url']} target="_blank" rel="noreferrer">{d[q]['alias']}</a></td>
                    <td>{n}</td>
                    <td>{r}</td>
                    <td>{d[q]['interval']}</td>
                    <td>{c}</td>
                    <td>{d[q]['cycles']}</td>
                    <td>{d[q]['eta']}</td>
                    <td>{d[q]['last_run']}</td>
                    <td>{status_}</td>
                    </tr>)
                if (d[q]['is_new'] && d[q]['found']) {
                    await this.playNotification(d[q]['alert_sound'])
                }
            }
        }, this);
        return (
            <tbody>{b}</tbody>
            )
      }

    async getNotificationSign(found, isNew){
        let match = ' '
        if (found) {
            if (isNew) {
                match = '!!!';
                this.setState({unnotifiedNew: true});
            } else {
                match = '+';
            }
        }
        return match
    }

    async playNotification(s){
        // TODO resolve local paths
        let a = await getSound(this.props.username, this.props.token, s)
        a.start()
    }
    
    async updateTable() {
        this.setState({ 
            content: await this.getContent(),
            last_run: new Date().toLocaleTimeString('en-GB'),
        })
    }

    async componentDidMount() {
        if (this.props.isLoggedIn)  {
            await this.updateTable()
            this.interval = setInterval(async () => {
                this.updateTable()
            }, this.state.refresh_rate*1000);
        }
     }

    async componentWillUnmount() {
        clearInterval(this.interval);
      }

    renderTableWithContent() {
        return (
            <Table striped bordered hover size="sm">
                <thead>
                    <tr>
                    <th>Alias</th>
                    <th>Found</th>
                    <th>Recurring</th>
                    <th>Interval</th>
                    <th>Cooldown</th>
                    <th>Cycles</th>
                    <th>ETA</th>
                    <th>Last Run</th>
                    <th>Status</th>
                    </tr>
                </thead>
                    {this.state.content}
            </Table>
        )
    }

    render() {
        let c = this.renderTableWithContent()
        return (
            <div>
                {c}
                <footer className='monitorStatus'>
                        Last Refresh: {this.state.last_run}
                </footer>
            </div>
        );
    }
}
