import React from 'react';
import { Header } from 'semantic-ui-react';
import ConsoleMeDataTable from '../blocks/ConsoleMeDataTable';

const SelectRoles = () => {
  const config = {
    expandableRows: true,
    dataEndpoint: '/api/v2/eligible_roles',
    sortable: false,
    totalRows: 1000,
    rowsPerPage: 50,
    serverSideFiltering: false,
    columns: [
      {
        placeholder: 'Account Name',
        key: 'account_name',
        type: 'input',
      },
      {
        placeholder: 'Account ID',
        key: 'account_id',
        type: 'input',
      },
      {
        placeholder: 'Role Name',
        key: 'role_name',
        type: 'link',
      },
      {
        placeholder: 'AWS Console Sign-In',
        key: 'redirect_uri',
        type: 'button',
        icon: 'sign-in',
        content: 'Sign-In',
        onClick: {
          action: 'redirect',
        },
      },
    ],
  };

  return (
    <>
      <Header as="h1">
        Select a Role
        <Header.Subheader>
          Click "Sign-In" to log in to the AWS Console with one of your eligible roles.
          If you don't see a role that you need access to,
          <br />
          please visit our
          {' '}
          <a
            href="https://manuals.netflix.net/view/infrasec/mkdocs/master/faq/#how-do-i-access-aws-console-for-an-account"
            target="_blank"
            rel="noreferrer noopener"
          >
            FAQ
          </a>
          {' '}
          for help requesting access. Please use
          <a
            href="https://docs.google.com/forms/d/e/1FAIpQLSePlVCFPDmESvjqpnBeFTAVsRk-a6iTPcS-fV5eHrsK9nBE6Q/viewform"
            target="_blank"
            rel="noreferrer noopener"
          >
            this form
          </a>
          {' '}
          to provide feedback.
        </Header.Subheader>
      </Header>
      <ConsoleMeDataTable
        config={config}
        configEndpoint="/api/v2/role_table_config"
      />
    </>
  );
};

export default SelectRoles;
