import React, {Component} from 'react';
import ReactDOM from "react-dom";
import DataTable from 'react-data-table-component';
import {Button, Input} from 'semantic-ui-react'
// TODO: Make this a generic table view where we just need to pass the endpoints to hit
// TODO: Make columns a return from backend
// TODO: Date integers should be converted to string
// Rows should be expandable
// Request data should be cached to Redis. If request to backend is made and there is no cache, create it.
// When a request is made, call celery task to update requests cache
const columns = [
    {
        name: 'ARN',
        selector: 'arn',
        sortable: false,
    },
    {
        name: 'Requester',
        selector: 'username',
        sortable: true,
    },
    {
        name: 'Status',
        selector: 'status',
        sortable: true,
    },
    {
        name: 'Updated By',
        selector: 'updated_by',
        sortable: true,
    },
    {
        name: 'Request ID',
        selector: 'request_id',
        sortable: true,
    },
    // {
    //     name: 'Justification',
    //     selector: 'justification',
    //     sortable: false,
    // },
    {
        name: 'Last Upated',
        selector: 'last_updated',
        sortable: true,
    },
    {
        name: 'Policy Name',
        selector: 'policy_name',
        sortable: true,
    },
    {
        name: 'Request Time',
        selector: 'request_time',
        sortable: true,
    },
    // {
    //     name: 'Reviewer Comments',
    //     selector: 'reviewer_comments',
    //     sortable: false,
    // },
];

const Export = ({onExport}) => (
    <Button onClick={e => onExport(e.target.value)}>Export</Button>
);

const ExpandedComponent = ({data}) => (
    <div>
    <pre>
        {JSON.stringify(data, null, 2)}
    </pre>
    </div>
);

function convertArrayOfObjectsToCSV(array) {
    let result;

    const columnDelimiter = ',';
    const lineDelimiter = '\n';
    const keys = Object.keys(data[0]);

    result = '';
    result += keys.join(columnDelimiter);
    result += lineDelimiter;

    array.forEach(item => {
        let ctr = 0;
        keys.forEach(key => {
            if (ctr > 0) result += columnDelimiter;

            result += item[key];

            ctr++;
        });
        result += lineDelimiter;
    });

    return result;
}

function downloadCSV(array) {
    const link = document.createElement('a');
    let csv = convertArrayOfObjectsToCSV(array);
    if (csv == null) return;

    const filename = 'export.csv';

    if (!csv.match(/^data:text\/csv/i)) {
        csv = `data:text/csv;charset=utf-8,${csv}`;
    }

    link.setAttribute('href', encodeURI(csv));
    link.setAttribute('download', filename);
    link.click();
}


class RequestsView extends Component {
    state = {
        data: [],
        q: "",
        loading: false,
        totalRows: 0,
        perPage: 10,
        tableConfig: {
            expandableRows: true,
            expandOnRowClicked: true,
            pagination: true,
            highlightOnHover: true,
            striped: true,
            subHeader: true,
        }
    }

    componentDidMount() {
        const {perPage} = this.state;

        this.setState({loading: true});

        // TODO: Make URL configurable
        fetch("/api/v2/requests")
            .then(response => response.json())
            .then(json => this.setState({data: json, loading: false}))
    }

    search(rows) {
        const columns = rows[0] && Object.keys(rows[0])
        return rows.filter(
            (row) => columns.some(column => row[column] && row[column].toString().toLowerCase().indexOf(this.state.q.toLowerCase()) > -1)
        )
    }

    SubHeaderComponent(data) {
        const dataLen = data && data.length
        const searchFields = []
        for (let i = 0; i < dataLen; i++) {
            searchFields.push(<Input placeholder='Search...'/>)
        }
        return searchFields
    }


    render() {
        const {loading, data, totalRows, q, tableConfig} = this.state;
        //const actionsMemo = React.useMemo(() => <Export onExport={() => downloadCSV(data)}/>, []);
        return (
            <div>
                <div>
                    <input type={"text"} value={q} onChange={(e) => this.setState({q: e.target.value})}/>
                </div>
                <div>
                    <DataTable
                        title="Requests"
                        columns={columns}
                        data={this.search(data)}
                        progressPending={loading}
                        expandableRows={tableConfig.expandableRows}
                        expandOnRowClicked={tableConfig.expandOnRowClicked}
                        pagination={tableConfig.pagination}
                        highlightOnHover={tableConfig.highlightOnHover}
                        striped={tableConfig.striped}
                        subHeader={tableConfig.subHeader}
                        subHeaderComponent={this.SubHeaderComponent(data)}
                        expandableRowsComponent={<ExpandedComponent/>}
                        // actions={actionsMemo}
                    />
                </div>
            </div>
        )
    }
}


export function renderRequestsView() {
    ReactDOM.render(
        <RequestsView/>,
        document.getElementById("requests_view"),
    )
}

export default RequestsView;