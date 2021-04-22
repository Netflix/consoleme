import React, { useEffect, useState } from "react";
import { Accordion, Header, Table } from "semantic-ui-react";
import { ReadOnlyPolicyMonacoEditor } from "./PolicyMonacoEditor";

const mockData = [
  {
    targets: [
      {
        target_id: "1234567890",
        arn:
          "arn:aws:organizations::0987654321:account/abcdefg12345/1234567890",
        name: "scp_test",
        type: "ACCOUNT",
      },
      {
        target_id: "1234567890",
        arn:
          "arn:aws:organizations::0987654321:account/abcdefg12345/1234567890",
        name: "scp_test",
        type: "ACCOUNT",
      },
      {
        target_id: "1234567890",
        arn:
          "arn:aws:organizations::0987654321:account/abcdefg12345/1234567890",
        name: "scp_test",
        type: "ACCOUNT",
      },
      {
        target_id: "1234567890",
        arn:
          "arn:aws:organizations::0987654321:account/abcdefg12345/1234567890",
        name: "scp_test",
        type: "ACCOUNT",
      },
    ],
    policy: {
      id: "12345-abcdef",
      arn:
        "arn:aws:organizations::0987654321:policy/abcdefg12345/service_control_policy/12345-abcdef",
      name: "policy-name-test",
      description: "ne",
      type: "SERVICE_CONTROL_POLICY",
      aws_managed: false,
      content:
        // eslint-disable-next-line max-len
        '{"Version":"2012-10-17","Statement":[{"Action":["name:ChangeResourceRecordSets","name:ChangeTagsForResource","name:DeleteHostedZone","name:UpdateHostedZoneComment"],"Effect":"Deny","Resource":["arn:aws:name:::hostedzone/Z0711695Q8KY9W4V1EFT"]},{"Action":["namedomains:DisableDomainAutoRenew"],"Effect":"Deny","Resource":["*"]}]}',
    },
  },
  {
    targets: [
      {
        target_id: "313219654698",
        arn:
          "arn:aws:organizations::0987654321:account/abcdefg12345/313219654698",
        name: "scp_test",
        type: "ACCOUNT",
      },
    ],
    policy: {
      id: "12345-abcdef1",
      arn:
        "arn:aws:organizations::0987654321:policy/abcdefg12345/service_control_policy/12345-abcdef",
      name: "policy-name-test",
      description: "ne",
      type: "SERVICE_CONTROL_POLICY",
      aws_managed: false,
      content:
        // eslint-disable-next-line max-len
        '{"Version":"2012-10-17","Statement":[{"Action":["name:ChangeResourceRecordSets","name:ChangeTagsForResource","name:DeleteHostedZone","name:UpdateHostedZoneComment"],"Effect":"Deny","Resource":["arn:aws:name:::hostedzone/Z0711695Q8KY9W4V1EFT"]},{"Action":["namedomains:DisableDomainAutoRenew"],"Effect":"Deny","Resource":["*"]}]}',
    },
  },
  {
    targets: [
      {
        target_id: "313219654698",
        arn:
          "arn:aws:organizations::0987654321:account/abcdefg12345/313219654698",
        name: "scp_test",
        type: "ACCOUNT",
      },
    ],
    policy: {
      id: "12345-abcdef2",
      arn:
        "arn:aws:organizations::0987654321:policy/abcdefg12345/service_control_policy/12345-abcdef",
      name: "policy-name-test",
      description: "ne",
      type: "SERVICE_CONTROL_POLICY",
      aws_managed: false,
      content:
        // eslint-disable-next-line max-len
        '{"Version":"2012-10-17","Statement":[{"Action":["name:ChangeResourceRecordSets","name:ChangeTagsForResource","name:DeleteHostedZone","name:UpdateHostedZoneComment"],"Effect":"Deny","Resource":["arn:aws:name:::hostedzone/Z0711695Q8KY9W4V1EFT"]},{"Action":["namedomains:DisableDomainAutoRenew"],"Effect":"Deny","Resource":["*"]}]}',
    },
  },
];

const ServiceControlPolicy = () => {
  const [panels, setPanels] = useState([]);

  useEffect(() => {
    const newPanels = mockData.map((policy) => {
      return {
        key: policy.policy.id,
        title: policy.policy.name,
        content: {
          content: (
            <>
              <Header as="h4" block>
                Details
              </Header>
              <Header as="h5">
                ARN
                <Header.Subheader>{policy.policy.arn}</Header.Subheader>
              </Header>
              <Header as="h5">
                Description
                <Header.Subheader>{policy.policy.description}</Header.Subheader>
              </Header>
              <Header as="h5">
                Type
                <Header.Subheader>{policy.policy.type}</Header.Subheader>
              </Header>
              <Header as="h5">
                AWS Managed
                <Header.Subheader>
                  {policy.policy.aws_managed ? "True" : "False"}
                </Header.Subheader>
              </Header>
              <Header as="h4" block style={{ marginTop: "3rem" }}>
                Content
              </Header>
              <ReadOnlyPolicyMonacoEditor
                policy={JSON.parse(policy.policy.content)}
              />
              {policy.targets.length ? (
                <>
                  <Header as="h4" block style={{ marginTop: "3rem" }}>
                    Targets
                  </Header>
                  <Table celled>
                    <Table.Header>
                      <Table.Row>
                        <Table.HeaderCell>Name</Table.HeaderCell>
                        <Table.HeaderCell>ID</Table.HeaderCell>
                        <Table.HeaderCell>ARN</Table.HeaderCell>
                        <Table.HeaderCell>Type</Table.HeaderCell>
                      </Table.Row>
                    </Table.Header>
                    <Table.Body>
                      {policy.targets.map((target) => {
                        return (
                          <Table.Row key={target.target_id}>
                            <Table.Cell>{target.name}</Table.Cell>
                            <Table.Cell>{target.target_id}</Table.Cell>
                            <Table.Cell>{target.arn}</Table.Cell>
                            <Table.Cell>{target.type}</Table.Cell>
                          </Table.Row>
                        );
                      })}
                    </Table.Body>
                  </Table>
                </>
              ) : null}
            </>
          ),
        },
      };
    });
    setPanels(newPanels);
  }, []);

  return (
    <>
      <Header as="h2">
        Service Control Policies
        <Header.Subheader>
          Lorem ipsum dolor sit amet, consectetur adipisicing elit. A aliquid
          assumenda commodi cum cupiditate, debitis deserunt eligendi eos fuga
          itaque nam pariatur quibusdam, quisquam. Atque cupiditate iure libero
          sunt. Facere.
        </Header.Subheader>
      </Header>
      <Accordion
        defaultActiveIndex={[0]}
        exclusive={false}
        fluid
        panels={panels}
        styled
        style={{ marginTop: "2rem" }}
      />
    </>
  );
};

export default ServiceControlPolicy;
