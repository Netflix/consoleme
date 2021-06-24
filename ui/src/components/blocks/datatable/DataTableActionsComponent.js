import React, { useState } from "react";
import { Button, Grid, Icon } from "semantic-ui-react";
import { useAuth } from "../../../auth/AuthProviderDefault";
import { omit } from "lodash";
import { json2csv } from "json-2-csv";

const DataTableActionsComponent = ({ filters, tableConfig }) => {
  const { sendRequestCommon } = useAuth();
  const [jsonExportLoading, setJsonExportLoading] = useState(false);
  const [csvExportLoading, setCsvExportLoading] = useState(false);

  const fetchAllData = async () => {
    // Remove the `limit` filter so we can fetch all records
    const filtersWithoutLimit = omit(filters, ["limit"]);
    return await sendRequestCommon(
      { filters: filtersWithoutLimit },
      tableConfig.dataEndpoint
    );
  };

  const generateFileDownload = (data, type, ext) => {
    const fileName = `console_me_export_${new Date().getTime()}`;
    const blob = new Blob([data], { type: type });
    const href = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = href;
    link.download = fileName + `.${ext}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleExportJson = () => {
    setJsonExportLoading(true);
    fetchAllData()
      .then(({ data }) => {
        generateFileDownload(JSON.stringify(data), "application/json", "json");
      })
      .catch((error) => console.error("Error during JSON export: ", error))
      .finally(() => setJsonExportLoading(false));
  };

  const handleExportCsv = () => {
    setCsvExportLoading(true);
    fetchAllData()
      .then(({ data }) => {
        json2csv(
          data,
          (err, csv) => {
            if (err) {
              console.error("Error when generating CSV: ", err);
              return;
            }
            generateFileDownload(csv, "text/csv;charset=utf-8;", "csv");
          },
          {
            emptyFieldValue: "",
          }
        );
      })
      .catch((error) => console.error("Error during CSV export: ", error))
      .finally(() => setCsvExportLoading(false));
  };

  if (!tableConfig.allowCsvExport && !tableConfig.allowJsonExport) {
    return null;
  }

  return (
    <Grid>
      <Grid.Column textAlign="right">
        {tableConfig.allowJsonExport ? (
          <Button
            basic
            size="small"
            compact
            onClick={handleExportJson}
            loading={jsonExportLoading}
          >
            <Icon name="file code outline" color="black" /> Export JSON
          </Button>
        ) : null}
        {tableConfig.allowCsvExport ? (
          <Button
            basic
            size="small"
            compact
            onClick={handleExportCsv}
            loading={csvExportLoading}
          >
            <Icon name="file excel outline" color="black" /> Export CSV
          </Button>
        ) : null}
      </Grid.Column>
    </Grid>
  );
};

export default DataTableActionsComponent;
