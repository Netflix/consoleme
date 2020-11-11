import React from 'react';
import { Header } from 'semantic-ui-react';
import ConsoleMeDataTable from '../blocks/ConsoleMeDataTable';

const RequestTable = () => {
  const config = {
    expandableRows: true,
    tableName: 'Requests',
    tableDescription: 'View all IAM policy requests created through ConsoleMe',
    dataEndpoint: '/api/v2/requests?markdown=true',
    sortable: false,
    totalRows: 1000,
    rowsPerPage: 50,
    serverSideFiltering: true,
    columns: [
      {
        placeholder: 'Username',
        key: 'username',
        type: 'input',
        style: {
          width: '100px',
        },
      },
      {
        placeholder: 'Arn',
        key: 'arn',
        type: 'link',
        style: {
          whiteSpace: 'normal',
          wordBreak: 'break-all',
        },
        width: 3,
      },
      {
        placeholder: 'Request Time',
        key: 'request_time',
        type: 'daterange',
      },
      {
        placeholder: 'Status',
        key: 'status',
        type: 'dropdown',
        style: {
          width: '90px',
        },
      },
      {
        placeholder: 'Request ID',
        key: 'request_id',
        type: 'link',
        style: {
          whiteSpace: 'normal',
          wordBreak: 'break-all',
        },
        width: 2,
      },
      {
        placeholder: 'Policy Name',
        key: 'policy_name',
        type: 'input',
        style: {
          width: '110px',
        },
      },
      {
        placeholder: 'Last Updated By',
        key: 'updated_by',
        type: 'input',
        style: {
          width: '110px',
        },
      },
    ],
  };

  return (
    <>
      <Header as="h2">
        Requests
        <Header.Subheader>
          View all IAM policy requests created through ConsoleMe
        </Header.Subheader>
      </Header>
      <ConsoleMeDataTable
        config={config}
      />
    </>
  );
};

export default RequestTable;
