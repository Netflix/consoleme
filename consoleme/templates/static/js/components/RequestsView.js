import React from "react";
import DataTable from "react-data-table-component";

const policiesExample = () => ([{
    id: "12e834fe-4670-4cd8-816e-bcf6c2da0202",
    username: "requester@example.com",
    updated_by: "updated_by@example.com",
    request_time: "request_time",
    status: "status",
    role: "role_arn",
    link: "/policies/request/12e834fe-4670-4cd8-816e-bcf6c2da0202",
}]);


const FilterComponent = ({filterText, onFilter, onClear}) => (
    <>
        <TextField id="search" type="text" placeholder="Filter By Name" value={filterText} onChange={onFilter}/>
        <ClearButton type="button" onClick={onClear}>X</ClearButton>
    </>
);

const columns = [
    {
        name: 'Request Time',
        selector: 'request_time',
    },
    {
        name: 'Request ID',
        selector: 'request_id',
    },
    {
        name: 'Username',
        selector: 'username',
    },
    {
        name: 'Updated By',
        selector: 'updated_by',
    },

];

const BasicTable = () => {
    const [filterText, setFilterText] = React.useState('');
    const [resetPaginationToggle, setResetPaginationToggle] = React.useState(false);
    const filteredItems = fakeUsers.filter(item => item.name && item.name.toLowerCase().includes(filterText.toLowerCase()));

    const subHeaderComponentMemo = React.useMemo(() => {
        const handleClear = () => {
            if (filterText) {
                setResetPaginationToggle(!resetPaginationToggle);
                setFilterText('');
            }
        };

        return <FilterComponent onFilter={e => setFilterText(e.target.value)} onClear={handleClear}
                                filterText={filterText}/>;
    }, [filterText, resetPaginationToggle]);

    return (
        <DataTable
            title="Requests"
            columns={columns}
            data={filteredItems}
            pagination
            paginationResetDefaultPage={resetPaginationToggle} // optionally, a hook to reset pagination to page 1
            subHeader
            subHeaderComponent={subHeaderComponentMemo}
            selectableRows
            persistTableHead
        />
    );
};