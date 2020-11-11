import React, { useEffect, useState } from 'react';
import { Header } from 'semantic-ui-react';
import ConsoleMeDataTable from '../blocks/ConsoleMeDataTable';
import { sendRequestCommon } from "../../helpers/utils";
import ReactMarkdown from "react-markdown";

const tableConfig = {
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

const SelectRoles = () => {
  const [pageData, setPageData] = useState(null);

  useEffect(() => {
    (async () => {
      const data = await sendRequestCommon(null, "/api/v2/eligible_roles_page_config", "get");
      setPageData(data);
    })();
  }, []);

  if (!pageData) {
    return null;
  }

  const { pageName, pageDescription } = pageData;
  return (
      <>
        <Header as="h1">
          {pageName}
          <Header.Subheader>
            <ReactMarkdown
                escapeHtml={false}
                linkTarget="_blank"
                source={pageDescription}
            />
          </Header.Subheader>
        </Header>
        <ConsoleMeDataTable
            config={tableConfig}
            configEndpoint="/api/v2/role_table_config"
        />
      </>
  );
};

export default SelectRoles;
