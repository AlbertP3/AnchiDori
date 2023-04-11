import Table from 'react-bootstrap/Table';
import '../static/monitor.css';
import { getDashboard } from '../db_conn';
import React from 'react';



export default class Monitor extends React.Component{

    constructor() {
        super();
        this.state = {
        content: <tr></tr>,
        last_run: '',
        refresh_rate: 15,
        unnotifiedNew: false,
        default_notification: 'notification.wav'
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
                if (d[q]['is_new']) {
                    // await this.playNotification(d[q]['local_sound'])
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

    async playNotification(n){
        // TODO resolve local paths
        try{
            var audio = new Audio('../../'+n)
        }catch(e){
            var audio = new Audio('../../'+this.state.default_notification)
        }
        audio.play();
    }
    
    async updateTable() {
        this.setState({ 
            content: await this.getContent(),
            last_run: new Date().toISOString().slice(11, 19),
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
