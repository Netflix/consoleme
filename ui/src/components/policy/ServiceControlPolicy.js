import React, { useEffect, useState } from "react";
import { Accordion, Header, Table } from "semantic-ui-react";
import { ReadOnlyPolicyMonacoEditor } from "./PolicyMonacoEditor";
import { useAuth } from "../../auth/AuthProviderDefault";
import { usePolicyContext } from "./hooks/PolicyProvider";

const ServiceControlPolicy = () => {
  const { params = {} } = usePolicyContext();
  const { accountID } = params;
  const { sendRequestCommon } = useAuth();
  const [serviceControlPolicies, setServiceControlPolicies] = useState([]);
  const [panels, setPanels] = useState([]);

  useEffect(() => {
    (async () => {
      const result = await sendRequestCommon(
        null,
        `/api/v2/service_control_policies/${accountID}`,
        "get"
      );
      if (!result) {
        return;
      }
      setServiceControlPolicies(result);
    })();
  }, [accountID, sendRequestCommon]);

  useEffect(() => {
    const newPanels =
      serviceControlPolicies.length > 0
        ? serviceControlPolicies.map((policy) => {
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
                      <Header.Subheader>
                        {policy.policy.description}
                      </Header.Subheader>
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
          })
        : [];
    setPanels(newPanels);
  }, [serviceControlPolicies]);

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
