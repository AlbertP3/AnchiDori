import Table from 'react-bootstrap/Table';
import '../static/monitor.css';
import { getDashboard, getSound } from '../db_conn';
import React from 'react';



export default class Monitor extends React.Component{

    constructor() {
        super();
        this.state = {
        content: <tr></tr>,
        last_run: '',
        refresh_rate: process.env.REACT_APP_REFRESH_SECONDS,
        unnotifiedNew: false,
        }
    }

    async getContent(){
        let d = await getDashboard(this.props.username, this.props.token);
        let b = []
        Object.keys(d).forEach(async function(q) {
            if ( parseInt(d[q]['cycles_limit'])>=0 ){
                let n = await this.getNotificationSign(d[q]['found'], d[q]['is_new'], d[q]['is_recurring'])
                b.push(<tr>
                    <th><a href={d[q]['target_url']} target="_blank">{d[q]['alias']}</a></th>
                    <th>{n}</th>
                    <th>{d[q]['interval']}</th>
                    <th>{d[q]['cycles']}</th>
                    <th>{d[q]['last_run']}</th>
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

    async getNotificationSign(found, isNew, isRecurring){
        let match = ' '
        if (found) {
            if (isNew) {
                match = '!!!';
                this.state.unnotifiedNew = true;
            } else if (!isRecurring) {
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
                    <th>Interval</th>
                    <th>Cycles</th>
                    <th>Last Run</th>
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
