import React from 'react';
import {
    Header,
    Table
} from 'semantic-ui-react';


const Issues = ({ cloudtrail = [], s3 = []}) => {
    return (
        <>
            <Header as="h2">
                <Header.Content>
                    Recent Permission Errors (Click here to see logs)
                    <Header.Subheader>
                        This section shows the permission errors discovered for this role in the last 24 hours. This data originated from CloudTrail.
                    </Header.Subheader>
                </Header.Content>
            </Header>
            <Table celled>
                <Table.Header>
                    <Table.Row>
                        <Table.HeaderCell>Error Call</Table.HeaderCell>
                        <Table.HeaderCell>Count</Table.HeaderCell>
                    </Table.Row>
                </Table.Header>
                <Table.Body>
                    <Table.Row negative>
                        <Table.Cell>lambda:GetPolicy20150331v2</Table.Cell>
                        <Table.Cell>48</Table.Cell>
                    </Table.Row>
                </Table.Body>
            </Table>
            <Header as="h2">
                Recent S3 Errors (Click here to query for recent S3 errors)
                <Header.Subheader>
                    This section shows the permission errors discovered for this role in the last 24 hours. This data originated from CloudTrail.
                </Header.Subheader>
            </Header>
            <Table celled>
                <Table.Header>
                    <Table.Row>
                        <Table.HeaderCell>Error Call</Table.HeaderCell>
                        <Table.HeaderCell>Count</Table.HeaderCell>
                        <Table.HeaderCell>Bucket Name</Table.HeaderCell>
                        <Table.HeaderCell>Bucket Prefix</Table.HeaderCell>
                        <Table.HeaderCell>Error Status</Table.HeaderCell>
                        <Table.HeaderCell>Error Code</Table.HeaderCell>
                    </Table.Row>
                </Table.Header>
                <Table.Body>
                    <Table.Row negative>
                        <Table.Cell>s3:PutObject</Table.Cell>
                        <Table.Cell>14</Table.Cell>
                        <Table.Cell>nflx-awsconfig-bunkerprod-sa-east-1</Table.Cell>
                        <Table.Cell>nflx-awsconfig-bunkerprod-sa-east-1/AWSLogs/388300705741/Config</Table.Cell>
                        <Table.Cell>403</Table.Cell>
                        <Table.Cell>AccessDenied</Table.Cell>
                    </Table.Row>
                </Table.Body>
            </Table>
        </>
    );
};

export default Issues;
