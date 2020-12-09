import React, { useEffect, useState } from "react";
import { Header } from "semantic-ui-react";
import ConsoleMeDataTable from "../blocks/ConsoleMeDataTable";
import { sendRequestCommon } from "../../helpers/utils";
import ReactMarkdown from "react-markdown";

const PolicyTable = () => {
  const [pageConfig, setPageConfig] = useState(null);

  useEffect(() => {
    (async () => {
      const data = await sendRequestCommon(
        null,
        "/api/v2/policies_page_config",
        "get"
      );
      setPageConfig(data);
    })();
  }, []);

  if (!pageConfig) {
    return null;
  }

  const { pageName, pageDescription, tableConfig } = pageConfig;

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
      <ConsoleMeDataTable config={tableConfig} />
    </>
  );
};

export default PolicyTable;
