import React, { useState } from 'react';
import {
    Accordion,
    Button,
    Icon,
    Item,
    Label,
    Header,
    Menu,
    Search,
    Segment,
    Tab,
    Table,
} from 'semantic-ui-react';


const ResourceDetail = ({ resource }) => {
    const {
        account_id,
        account_name,
        apps,
        arn,
        cloudtrail_details,
        name,
        s3_details,
        templated,
        template_link,
    } = resource;

    // TODO, need information for resource id, resource type, created on, last updated, bigbrother link, s3 hive
    return (
        <Table celled striped definition>
            <Table.Body>
                <Table.Row>
                    <Table.Cell collapsing>
                        Account
                    </Table.Cell>
                    <Table.Cell>{`${account_name} (${account_id}`})</Table.Cell>
                </Table.Row>
                <Table.Row>
                    <Table.Cell collapsing>
                        Amazon Resource Name
                    </Table.Cell>
                    <Table.Cell>{arn}</Table.Cell>
                </Table.Row>
                <Table.Row>
                    <Table.Cell>
                        Resource type
                    </Table.Cell>
                    <Table.Cell>AWS::IAM::Role</Table.Cell>
                </Table.Row>
                <Table.Row>
                    <Table.Cell>
                        Resource name
                    </Table.Cell>
                    <Table.Cell>{name}</Table.Cell>
                </Table.Row>
                <Table.Row>
                    <Table.Cell>
                        CloudTrail Events
                    </Table.Cell>
                    <Table.Cell>
                        <a href={cloudtrail_details && cloudtrail_details.error_url || ""} target="_blank">
                            Link
                        </a>
                    </Table.Cell>
                </Table.Row>
                <Table.Row>
                    <Table.Cell>
                        S3 Access Log
                    </Table.Cell>
                    <Table.Cell>
                        <a href={s3_details && s3_details.error_url || ""} target="_blank">
                            Link
                        </a>
                    </Table.Cell>
                </Table.Row>
                <Table.Row>
                    <Table.Cell>
                        Config Timeline
                    </Table.Cell>
                    <Table.Cell>
                        <a href={`/role/${account_id}`} target="_blank">
                            Link
                        </a>
                    </Table.Cell>
                </Table.Row>
                <Table.Row>
                    <Table.Cell collapsing>
                        Created on
                    </Table.Cell>
                    <Table.Cell>09/24/2020, 07:50:00 AM</Table.Cell>
                </Table.Row>
                <Table.Row>
                    <Table.Cell collapsing>
                        Last updated
                    </Table.Cell>
                    <Table.Cell>10/10/2020, 11:48:38 PM</Table.Cell>
                </Table.Row>
                <Table.Row>
                    <Table.Cell collapsing>
                        Templated
                    </Table.Cell>
                    <Table.Cell>
                        <span>
                            {`${templated ? "True" : "False"}`}
                            {templated ? <a href={template_link} target="_blank">Link</a> : null}
                        </span>
                    </Table.Cell>
                </Table.Row>
            </Table.Body>
        </Table>
    );
};

export default ResourceDetail;
