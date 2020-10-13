import React from 'react';
import {
    Button,
    Dropdown,
    Form,
    List,
    Icon,
    Header,
    Segment,
} from 'semantic-ui-react';


const ManagedPolicy = ({ policies = []}) => {
    // TODO, retrieve available managed policies to attach
    const managedPolicyOptions = [
        {
            key: "arn:aws:iam::123456789012:policy/TestRole",
            value: "arn:aws:iam::123456789012:policy/TestRole",
            text: "arn:aws:iam::123456789012:policy/TestRole",
        },
    ];

    return (
        <>
            <Header as='h2'>
                Managed Policies
            </Header>
            <Form>
                <Form.Field>
                    <label>
                        Select a managed policy from the dropdown that you wish to add to this role.
                    </label>
                    <Dropdown
                        placeholder='Choose a managed policy to add to this role.'
                        fluid
                        selection
                        options={managedPolicyOptions}
                    />
                </Form.Field>
            </Form>
            <Header as='h3' attached="top" content="Attached Policies"/>
            <Segment attached="bottom">
                <List divided size="medium" relaxed='very' verticalAlign='middle'>
                    {
                        policies.map(policy => {
                            return (
                                <List.Item key={policy.PolicyName}>
                                    <List.Content floated='right' >
                                        <Button negative size="small">
                                            <Icon name="remove" />
                                            Remove
                                        </Button>
                                    </List.Content>
                                    <List.Content >
                                        <List.Header>
                                            {policy.PolicyName}
                                        </List.Header>
                                        <List.Description as='a'>
                                            {policy.PolicyArn}
                                        </List.Description>
                                    </List.Content>
                                </List.Item>
                            )
                        })
                    }
                </List>
            </Segment>
        </>
    );
};

export default ManagedPolicy;
