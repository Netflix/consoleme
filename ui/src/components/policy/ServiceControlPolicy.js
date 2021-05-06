import React, { useEffect, useState } from "react";
import { Accordion, Header, Icon, Message, Table } from "semantic-ui-react";
import { ReadOnlyPolicyMonacoEditor } from "./PolicyMonacoEditor";
import { useAuth } from "../../auth/AuthProviderDefault";
import { usePolicyContext } from "./hooks/PolicyProvider";

const ServiceControlPolicy = () => {
  const { params = {} } = usePolicyContext();
  const { accountID } = params;
  const { sendRequestCommon } = useAuth();
  const [serviceControlPolicies, setServiceControlPolicies] = useState([]);
  const [errorMessage, setErrorMessage] = useState(null);
  const [panels, setPanels] = useState([]);
  const [activeTargets, setActiveTargets] = useState({});

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
      if (result.status === "error") {
        setErrorMessage(JSON.stringify(result));
      } else {
        setServiceControlPolicies(result.data);
      }
    })();
  }, [accountID, sendRequestCommon]);

  useEffect(() => {
    const newPanels =
      serviceControlPolicies.length > 0
        ? serviceControlPolicies.map((policy) => {
            return {
              active: true,
              key: policy.policy.id,
              title: policy.policy.name,
              content: {
                content: (
                  <>
                    <Header as="h2">Details</Header>
                    <Table celled striped definition>
                      <Table.Body>
                        <Table.Row>
                          <Table.Cell>ARN</Table.Cell>
                          <Table.Cell>{policy.policy.arn}</Table.Cell>
                        </Table.Row>
                        <Table.Row>
                          <Table.Cell>Description</Table.Cell>
                          <Table.Cell>{policy.policy.description}</Table.Cell>
                        </Table.Row>
                        <Table.Row>
                          <Table.Cell>Type</Table.Cell>
                          <Table.Cell>{policy.policy.type}</Table.Cell>
                        </Table.Row>
                        <Table.Row>
                          <Table.Cell>AWS Managed</Table.Cell>
                          <Table.Cell>
                            {policy.policy.aws_managed ? "True" : "False"}
                          </Table.Cell>
                        </Table.Row>
                      </Table.Body>
                    </Table>
                    <Header as="h2">Content</Header>
                    <ReadOnlyPolicyMonacoEditor
                      policy={JSON.parse(policy.policy.content)}
                    />
                    {policy.targets.length ? (
                      <>
                        <Accordion exclusive={false} fluid>
                          <Accordion.Title
                            active={activeTargets[policy.policy.id] === true}
                            index={true}
                            onClick={() => {
                              let newState = activeTargets;
                              newState[policy.policy.id] = !newState[
                                policy.policy.id
                              ];
                              setActiveTargets({
                                ...activeTargets,
                                ...newState,
                              });
                            }}
                          >
                            <Icon name="dropdown" />
                            Targets
                          </Accordion.Title>
                          <Accordion.Content
                            active={activeTargets[policy.policy.id] === true}
                          >
                            <Table celled attached="bottom">
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
                                      <Table.Cell>
                                        {target.target_id}
                                      </Table.Cell>
                                      <Table.Cell>{target.arn}</Table.Cell>
                                      <Table.Cell>{target.type}</Table.Cell>
                                    </Table.Row>
                                  );
                                })}
                              </Table.Body>
                            </Table>
                          </Accordion.Content>
                        </Accordion>
                      </>
                    ) : null}
                  </>
                ),
              },
            };
          })
        : [];
    setPanels(newPanels);
  }, [serviceControlPolicies, activeTargets]);

  return (
    <>
      <Header as="h2">
        Service Control Policies
        <Header.Subheader>
          Service control policies (SCPs) are a type of organization policy that
          can be used to manage permissions across an entire AWS organization.
          More information about SCPs is
          <a
            target="_blank"
            rel="noopener noreferrer"
            href={
              "https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html"
            }
          >
            {" "}
            here
          </a>
        </Header.Subheader>
      </Header>
      {errorMessage ? (
        <Message negative>
          <p>{errorMessage}</p>
        </Message>
      ) : null}
      {panels.length > 0 ? (
        <Accordion
          defaultActiveIndex={[0]}
          exclusive={false}
          fluid
          panels={panels}
          styled
          style={{ marginTop: "2rem" }}
        />
      ) : null}
    </>
  );
};

export default ServiceControlPolicy;
