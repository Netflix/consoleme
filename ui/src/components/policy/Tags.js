import React from 'react';
import {
    Button,
    Form,
    Header,
    Segment,
} from 'semantic-ui-react';


const Tags = ({ tags = [] }) => {
    // TODO, add expand all, close all features
    return (
        <>
            <Segment
                basic
                clearing
                style={{
                    padding: 0
                }}
            >
                <Header as='h2' floated='left'>
                    Tags
                    <Header.Subheader>
                        You can add/edit/delete tags for this role from here.
                    </Header.Subheader>
                </Header>
                <Button.Group floated='right'>
                    <Button positive>Create New Tag</Button>
                </Button.Group>
            </Segment>
            <Form>
                {
                    tags.map(tag => {
                        return (
                            <Form.Group key={tag.Key} inline>
                                <Form.Input label='Key' placeholder='Key' value={tag.Key} readOnly />
                                <Form.Input label='Value' placeholder='Value' value={tag.Value} />
                                <Form.Button negative icon='remove' content='Delete Tag' />
                            </Form.Group>
                        );
                    })
                }
                <Form.Button primary icon='save' content='Save' />
            </Form>
        </>
    );
};

export default Tags;
