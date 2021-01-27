import _ from "lodash";
import React, { Component } from "react";
import ReactMarkdown from "react-markdown";
import { Button, Form, Header, Message } from "semantic-ui-react";
import DropDownBlockComponent from "../blocks/DropDownBlockComponent";
import TextInputBlockComponent from "../blocks/TextInputBlockComponent";
import TypeaheadBlockComponent from "../blocks/TypeaheadBlockComponent";

class SelfServiceComponent extends Component {
  constructor(props) {
    super(props);
    this.state = {
      messages: [],
      values: {},
    };
  }

  handleInputUpdate(context, value) {
    const { values } = this.state;
    const newValues = {
      ...values,
      [context]: _.isString(value) ? value.trim() : value,
    };
    this.setState({
      values: newValues,
    });
  }

  handleSubmit() {
    const { config, role, service } = this.props;
    const { values } = this.state;
    const { inputs, condition } = config.permissions_map[service];

    const default_values = { condition };

    inputs.forEach((input) => {
      default_values[input.name] = input.default || null;
    });

    const result = Object.assign(default_values, values);
    Object.keys(result).forEach((key) => {
      const value = result[key];
      if (value && !["actions", "condition"].includes(key)) {
        result[key] = value.replace("{account_id}", role.account_id);
      }
    });

    // Exception Hanlding for inputs
    const messages = [];
    Object.keys(inputs).forEach((idx) => {
      const input = inputs[idx];
      if (!result[input.name]) {
        messages.push(`No value is given for ${input.name}`);
      }
    });

    if (!("actions" in result)) {
      messages.push("No actions are selected");
    }

    if (messages.length > 0) {
      return this.setState({ messages });
    }

    const permission = {
      service,
      ...result,
    };
    return this.setState(
      {
        messages: [],
        values: {},
      },
      () => {
        this.props.updatePermission(permission);
      }
    );
  }

  buildInputBlocks() {
    const { config, service, role } = this.props;
    const { action_map, inputs } = config.permissions_map[service];
    const options = action_map.map((action) => ({
      key: action.name,
      text: action.text,
      value: action.name,
      actions: action.permissions,
    }));

    const blocks = inputs.map((input) => {
      // TODO(heewonk), make this substitution logic uniform and applied once
      let defaultValue;
      defaultValue = input.default || "";
      defaultValue = defaultValue.replace("{account_id}", role.account_id);
      switch (input.type) {
        case "text_input":
          return (
            <TextInputBlockComponent
              defaultValue={defaultValue}
              handleInputUpdate={this.handleInputUpdate.bind(this, input.name)}
              required={input.required || false}
              label={input.text}
            />
          );
        case "typeahead_input":
          return (
            <TypeaheadBlockComponent
              defaultValue={defaultValue}
              handleInputUpdate={this.handleInputUpdate.bind(this, input.name)}
              required={input.required || false}
              typeahead={input.typeahead_endpoint}
              label={input.text}
              sendRequestCommon={this.props.sendRequestCommon}
            />
          );
        default:
          return <div />;
      }
    });

    // DropDown Blocks for gathering Permission Actions for this Service.
    blocks.push(
      <DropDownBlockComponent
        handleInputUpdate={this.handleInputUpdate.bind(this, "actions")}
        options={options}
        required
      />
    );

    return blocks;
  }

  render() {
    const { config, service } = this.props;
    const { description, text } = config.permissions_map[service];

    const { messages } = this.state;
    const messagesToShow =
      messages.length > 0 ? (
        <Message negative>
          <Message.Header>There are some parameters missing.</Message.Header>
          <Message.List>
            {messages.map((message) => (
              <Message.Item>{message}</Message.Item>
            ))}
          </Message.List>
        </Message>
      ) : null;

    const blocks = this.buildInputBlocks();

    return (
      <Form>
        <Header as="h3">{text}</Header>
        <ReactMarkdown linkTarget="_blank" source={description} />
        {blocks}
        {messagesToShow}
        <Button
          fluid
          onClick={this.handleSubmit.bind(this)}
          primary
          type="submit"
        >
          Add Permission
        </Button>
      </Form>
    );
  }
}

export default SelfServiceComponent;
