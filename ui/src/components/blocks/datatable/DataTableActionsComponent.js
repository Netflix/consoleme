import React from "react";
import { Button, Grid, Icon } from "semantic-ui-react";

import { json2csv } from "json-2-csv";

const DataTableActionsComponent = ({ filteredData, tableConfig }) => {
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
    const data = JSON.stringify(filteredData);
    generateFileDownload(data, "application/json", ".json");
  };

  const handleExportCsv = () => {
    json2csv(
      filteredData,
      (err, csv) => {
        if (err) {
          console.error("Failed to export CSV.");
          return;
        }
        generateFileDownload(csv, "text/csv;charset=utf-8;", ".csv");
      },
      {
        emptyFieldValue: "",
      }
    );
  };

  if (!tableConfig.allowCsvExport && !tableConfig.allowJsonExport) {
    return null;
  }

  return (
    <Grid>
      <Grid.Column textAlign="right">
        {tableConfig.allowJsonExport ? (
          <Button basic size="small" compact onClick={handleExportJson}>
            <Icon name="file code outline" color="black" /> Export JSON
          </Button>
        ) : null}
        {tableConfig.allowCsvExport ? (
          <Button basic size="small" compact onClick={handleExportCsv}>
            <Icon name="file excel outline" color="black" /> Export CSV
          </Button>
        ) : null}
      </Grid.Column>
    </Grid>
  );
};

export default DataTableActionsComponent;
