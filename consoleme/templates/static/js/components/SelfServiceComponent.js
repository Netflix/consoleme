import React, { Component } from 'react';
import ReactMarkdown from 'react-markdown';
import {
    Button,
    Form,
    Header,
    Message,
} from 'semantic-ui-react';
import DropDownBlockComponent from "./blocks/DropDownBlockComponent";
import TextInputBlockComponent from "./blocks/TextInputBlockComponent";
import TypeaheadBlockComponent from "./blocks/TypeaheadBlockComponent";


class SelfServiceComponent extends Component {
    state = {
        messages: [],
        values: {},
    };

    handleInputUpdate(context, value) {
        const values = Object.assign(
            this.state.values,
            {[context]: value}
        );
        this.setState({
            values,
        });
    }

    handleSubmit() {
        const {config, service} = this.props;
        const {values} = this.state;
        const {inputs} = config.permissions_map[service];

        const default_values = {};
        inputs.forEach((input) => {
            default_values[input.name] = input.default || null;
        });
        const result = Object.assign(default_values, values);
        const permission = {
            service,
            ...result,
        };

        return this.setState({
            messages: [],
            values: {},
        }, () => {
            this.props.updatePermission(permission);
        });
    }

    buildInputBlocks() {
        const {config, service} = this.props;
        const {action_map, inputs} = config.permissions_map[service];
        const options = action_map.map(action => {
            return {
                key: action.name,
                text: action.text,
                value: action.name,
                actions: action.permissions,
            };
        });

        const blocks = inputs.map(input => {
            switch (input.type) {
                case "text_input":
                    return (
                        <TextInputBlockComponent
                            defaultValue={input.default || ""}
                            handleInputUpdate={this.handleInputUpdate.bind(this, input.name)}
                            required={input.required || false}
                        />
                    );
                case "typeahead_input":
                    return (
                        <TypeaheadBlockComponent
                            defaultValue={input.default || ""}
                            handleInputUpdate={this.handleInputUpdate.bind(this, input.name)}
                            required={input.required || false}
                            typeahead={input.typeahead_endpoint}
                        />
                    );
                default:
                    return <div />
            }
        });

        blocks.push(
            <DropDownBlockComponent
                handleInputUpdate={this.handleInputUpdate.bind(this, "actions")}
                options={options}
                required={true}
            />
        );

        return blocks;
    }

    render() {
        const {config, service} = this.props;
        const {description, text} = config.permissions_map[service];

        const {messages} = this.state;
        const messagesToShow = (messages.length > 0)
            ? (
                <Message negative>
                    <Message.Header>
                        There are some parameters missing.
                    </Message.Header>
                    <Message.List>
                        {
                            messages.map(message => {
                                return <Message.Item>{message}</Message.Item>;
                            })
                        }
                    </Message.List>
                </Message>
            )
            : null;

        const blocks = this.buildInputBlocks();

        return (
            <Form>
                <Header as="h3">
                    {text}
                </Header>
                <ReactMarkdown source={description} />
                {blocks}
                {messagesToShow}
                <Button
                    fluid
                    onClick={this.handleSubmit.bind(this)}
                    primary
                    type='submit'
                >
                    Add Permission
                </Button>
            </Form>
        );
    }
}

export default SelfServiceComponent;