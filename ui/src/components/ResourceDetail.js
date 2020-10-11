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


const ResourceDetail = () => {
    return (
        <Table celled striped definition>
            <Table.Body>
                <Table.Row>
                    <Table.Cell collapsing>
                        Amazon Resource Name
                    </Table.Cell>
                    <Table.Cell>arn:aws:iam::609753154238:role/CurtisTestRole</Table.Cell>
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
                    <Table.Cell>CurtisTestRole</Table.Cell>
                </Table.Row>
                <Table.Row>
                    <Table.Cell>
                        CloudTrail Events
                    </Table.Cell>
                    <Table.Cell>
                        <a
                            href="http://es_cis.us-east-1.dynprod.netflix.net:7103/app/kibana#/dashboard/13842cf0-6911-11e8-9079-c53a7a17b8ce?_g=(refreshInterval:('$$hashKey':'object:1987',display:'5%20seconds',pause:!f,section:1,value:5000),time:(from:now-1h,mode:quick,to:now))&_a=(description:'',filters:!(('$state':(store:appState),meta:(alias:!n,disabled:!f,index:'bigbrother_*',key:userIdentity.sessionContext.sessionIssuer.arn,negate:!f,type:phrase,value:'arn:aws:iam::609753154238:role/CurtisTestRole'),query:(match:(userIdentity.sessionContext.sessionIssuer.arn:(query:'arn:aws:iam::609753154238:role/CurtisTestRole',type:phrase))))),options:(darkTheme:!f),panels:!((col:1,id:AWS_Accounts,panelIndex:1,row:1,size_x:2,size_y:6,type:visualization),(col:3,id:BigBrother_Histogram,panelIndex:2,row:1,size_x:8,size_y:6,type:visualization),(col:1,id:BigBrother-IAM-Roles,panelIndex:3,row:7,size_x:6,size_y:3,type:visualization),(col:7,id:BigBrother_IAM_Users,panelIndex:4,row:7,size_x:6,size_y:3,type:visualization),(col:7,id:BigBrother_IPs,panelIndex:5,row:10,size_x:6,size_y:5,type:visualization),(col:11,id:BigBrother_Regions,panelIndex:6,row:1,size_x:2,size_y:3,type:visualization),(col:1,columns:!(eventID,eventName,userIdentity.userName,userIdentity.accountId,eventSource,sourceIPAddress,userIdentity.principalId),id:bigbrother,panelIndex:7,row:18,size_x:12,size_y:3,sort:!(eventTime,desc),type:search),(col:1,id:BigBrother_Errors,panelIndex:8,row:10,size_x:6,size_y:5,type:visualization),(col:1,id:BigBrother_Events,panelIndex:9,row:15,size_x:6,size_y:3,type:visualization),(col:7,id:BigBrother_Event_Source,panelIndex:10,row:15,size_x:6,size_y:3,type:visualization),(col:11,id:AW8WX5YJz7JA7xKXYBA4,panelIndex:11,row:4,size_x:2,size_y:3,type:visualization)),query:(match_all:()),timeRestore:!f,title:BigBrother,uiState:(P-1:(spy:(mode:(fill:!f,name:!n)),vis:(params:(sort:(columnIndex:!n,direction:!n)))),P-10:(vis:(params:(sort:(columnIndex:!n,direction:!n)))),P-11:(vis:(defaultColors:('0%20-%20100':'rgb(0,104,55)'))),P-2:(vis:(colors:(Count:%23508642),legendOpen:!f)),P-3:(vis:(colors:(Count:%23BF1B00),legendOpen:!f)),P-4:(vis:(colors:(Count:%23508642),legendOpen:!f)),P-8:(vis:(params:(sort:(columnIndex:!n,direction:!n)))),P-9:(vis:(params:(sort:(columnIndex:!n,direction:!n))))),viewMode:view)"
                            target="_blank"
                        >
                            Link
                        </a>
                    </Table.Cell>
                </Table.Row>
                <Table.Row>
                    <Table.Cell>
                        S3 Access Log
                    </Table.Cell>
                    <Table.Cell>
                        <a
                            href="https://bigdataportal.dynprod.netflix.net:7002/?query=SELECT%0A%20%20%20%20*%0A%20%20%20%20FROM%0A%20%20%20%20s3mgmt.s3_access_f%0A%20%20%20%20WHERE%0A%20%20%20%20dateint%20%3E%3D%2020201010%20and%0A%20%20%20%20requester_role%20%3D%20%27CurtisTestRole%27%20and%0A%20%20%20%20requester_account%20%3D%20%27609753154238%27%0A%20%20%20%20order%20by%20ts%20desc%0A%20%20%20%20limit%20100&jobType=PrestoJob"
                            target="_blank"
                        >
                            Link
                        </a>
                    </Table.Cell>
                </Table.Row>
                <Table.Row>
                    <Table.Cell>
                        Config Timeline
                    </Table.Cell>
                    <Table.Cell>
                        <a
                            href="https://consoleme.prod.bunker.netflix.net/role/609753154238?redirect=https%3A%2F%2Fus-east-1.console.aws.amazon.com%2Fconfig%2Fhome%3F%23%2Ftimeline%2FAWS%3A%3AIAM%3A%3ARole%2FAROAY36A6YK7CRJAXNQBN%2Fconfiguration"
                            target="_blank"
                        >
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
            </Table.Body>
        </Table>
    );
};

export default ResourceDetail;
