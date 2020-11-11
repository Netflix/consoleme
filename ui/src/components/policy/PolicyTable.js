import React from 'react';
import { Header } from 'semantic-ui-react';
import ConsoleMeDataTable from '../blocks/ConsoleMeDataTable';

const PolicyTable = () => {
  const config = {
    expandableRows: true,
    tableName: 'Policies',
    tableDescription: 'View all of the AWS Resources we know about.',
    dataEndpoint: '/api/v2/policies?markdown=true',
    sortable: false,
    totalRows: 1000,
    rowsPerPage: 50,
    serverSideFiltering: true,
    columns: [
      {
        placeholder: 'Account ID',
        key: 'account_id',
        type: 'input',
        style: {
          width: '110px',
        },
      },
      {
        placeholder: 'Account',
        key: 'account_name',
        type: 'input',
        style: {
          width: '90px',
        },
      },
      {
        placeholder: 'Resource',
        key: 'arn',
        type: 'link',
        width: 6,
        style: {
          whiteSpace: 'normal',
          wordBreak: 'break-all',
        },
      },
      {
        placeholder: 'Tech',
        key: 'technology',
        type: 'input',
        style: {
          width: '70px',
        },
      },
      {
        placeholder: 'Template',
        key: 'templated',
        type: 'input',
        style: {
          width: '100px',
        },
      },
      {
        placeholder: 'Errors',
        key: 'errors',
        color: 'red',
        width: 1,
      },
    ],
  };

  return (
    <>
      <Header as="h2">
        Policies
        <Header.Subheader>
          View all of the AWS Resources we know about.
        </Header.Subheader>
      </Header>
      <ConsoleMeDataTable
        config={config}
      />
    </>
  );
};

export default PolicyTable;
