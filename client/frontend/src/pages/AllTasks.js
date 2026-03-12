import React from "react";

class AllTasks extends React.Component {
    state = {
        isLoading: true,
        tasklist: [],
        error: null
    };
    getFetchTasks() {
        this.setState({
            loading: true
        }, () => {
            fetch("http://localhost:5000/alltasks"
            ).then(res => res.json()).then(result => this.setState({
                loading: false,
                tasklist: result
            })).catch(console.log);
        });
    }
    componentDidMount() {
        this.getFetchTasks();
    }
    render() {
        const {
            tasklist,
            error
        } = this.state;
        return (
            <React.Fragment>
            <h1>All The Tasks!</h1> {
                error ? <p>
                {
                    error.message
                } </p> : null}  {
                    JsonDataDisplay(tasklist)
                } </React.Fragment> );
    }
}

function JsonDataDisplay(jsonData){
        const DisplayData=jsonData.map(
            (task)=>{
                return(
                    <tr>
                        <td>{task.id}</td>
                        <td>{task.title}</td>
                        <td>{task.completed}</td>
                    </tr>
                )
            }
        )
        
        return(
            <div>
                <table class="table table-striped">
                    <thead>
                        <tr>
                        <th>ID</th>
                        <th>Title</th>
                        <th>Completed</th>
                        </tr>
                    </thead>
                    <tbody>
                        {DisplayData}
                    </tbody>
                </table>
            </div>
        )
}

export default AllTasks;