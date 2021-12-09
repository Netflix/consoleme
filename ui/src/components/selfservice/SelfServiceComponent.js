import _ from "lodash";
import React, { Component } from "react";
import ReactMarkdown from "react-markdown";
import {
  Accordion,
  Button,
  Divider,
  Dropdown,
  Form,
  Header,
  Message,
} from "semantic-ui-react";
import DropDownBlockComponent from "../blocks/DropDownBlockComponent";
import TextInputBlockComponent from "../blocks/TextInputBlockComponent";
import TypeaheadBlockComponent from "../blocks/TypeaheadBlockComponent";
import SingleTypeaheadBlockComponent from "../blocks/SingleTypeaheadBlockComponent";

class SelfServiceComponent extends Component {
  constructor(props) {
    super(props);
    this.state = {
      messages: [],
      values: {},
      activeIndex: 1,
      extraAction: [],
      includeAccount: [],
      excludeAccount: [],
      currentExtraActionValues: [],
      currentIncludeAccountValues: [],
      currentExcludeAccountValues: [],
    };
  }

  handleExtraActionAddition = (e, { value }) => {
    this.setState((prevState) => ({
      extraAction: [{ text: value, value }, ...prevState.extraAction],
    }));
  };

  handleIncludeAccountAddition = (e, { value }) => {
    this.setState((prevState) => ({
      includeAccount: [{ text: value, value }, ...prevState.includeAccount],
    }));
  };

  handleExcludeAccountAddition = (e, { value }) => {
    this.setState((prevState) => ({
      excludeAccount: [{ text: value, value }, ...prevState.excludeAccount],
    }));
  };

  handleExtraActionChange = (e, { value }) =>
    this.setState({ currentExtraActionValues: value });

  handleIncludeAccountChange = (e, { value }) =>
    this.setState({ currentIncludeAccountValues: value });

  handleExcludeAccountChange = (e, { value }) =>
    this.setState({ currentExcludeAccountValues: value });

  handleClick = (e, titleProps) => {
    const { index } = titleProps;
    const { activeIndex } = this.state;
    const newIndex = activeIndex === index ? -1 : index;

    this.setState({ activeIndex: newIndex });
  };

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
    const { values, extraAction, includeAccount, excludeAccount } = this.state;
    const { inputs, condition } = config.permissions_map[service];

    const default_values = { condition };

    inputs.forEach((input) => {
      default_values[input.name] = input.default || null;
    });

    const result = Object.assign(default_values, values);
    Object.keys(result).forEach((key) => {
      const value = result[key];
      if (
        value &&
        typeof value === "string" &&
        !["actions", "condition"].includes(key)
      ) {
        result[key] = value.replace("{account_id}", role.account_id);
      }
    });

    // Exception Handling for inputs
    const messages = [];
    Object.keys(inputs).forEach((idx) => {
      const input = inputs[idx];
      if (!result[input.name] || result[input.name].length === 0) {
        messages.push(`No value is given for ${input.text}. If you entered text for ${input.text},
                      don't forget to press enter to add it`);
      }
    });

    if (!("actions" in result)) {
      messages.push("No actions are selected");
    }

    if (messages.length > 0) {
      return this.setState({ messages });
    }

    if (extraAction.length > 0) {
      this.props.updateExtraActions(extraAction);
    }

    if (includeAccount.length > 0) {
      this.props.updateIncludeAccounts(includeAccount);
    }

    if (excludeAccount.length > 0) {
      this.props.updateExcludeAccounts(excludeAccount);
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
      async () => {
        await this.props.updatePermission(permission);
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
            <>
              <TypeaheadBlockComponent
                defaultValue={defaultValue + 1}
                handleInputUpdate={this.handleInputUpdate.bind(
                  this,
                  input.name
                )}
                required={input.required || false}
                typeahead={input.typeahead_endpoint}
                label={input.text}
                sendRequestCommon={this.props.sendRequestCommon}
              />
            </>
          );
        case "single_typeahead_input":
          return (
            <SingleTypeaheadBlockComponent
              defaultValue={defaultValue + 1}
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

  buildAdvancedOptions() {
    const { role } = this.props;
    const { activeIndex } = this.state;
    const { currentExtraActionValues } = this.state;
    const { currentIncludeAccountValues } = this.state;
    const { currentExcludeAccountValues } = this.state;

    return (
      <div>
        <Divider />
        <Accordion>
          <Accordion.Title
            active={activeIndex === 0}
            index={0}
            onClick={this.handleClick}
          >
            <span style={{ color: "#4183c4" }}>Advanced Options</span>
          </Accordion.Title>
          <Accordion.Content active={activeIndex === 0}>
            <label>Extra Actions (example: s3:get*)</label>
            <Dropdown
              options={this.state.extraAction}
              placeholder="Press Enter after typing each extra action"
              search
              selection
              fluid
              multiple
              allowAdditions
              value={currentExtraActionValues}
              onAddItem={this.handleExtraActionAddition}
              onChange={this.handleExtraActionChange}
              style={{ marginBottom: "1em" }}
              className={"advancedOption"}
            />
            {role.template_language === "honeybee" ? (
              <>
                <label>Include Accounts</label>
                <Dropdown
                  options={this.state.includeAccount}
                  placeholder="Press Enter after typing each included account"
                  search
                  selection
                  fluid
                  multiple
                  allowAdditions
                  value={currentIncludeAccountValues}
                  onAddItem={this.handleIncludeAccountAddition}
                  onChange={this.handleIncludeAccountChange}
                  style={{ marginBottom: "1em" }}
                  className={"advancedOption"}
                />
                <label>Exclude Accounts</label>
                <Dropdown
                  options={this.state.excludeAccount}
                  placeholder="Press Enter after typing each excluded account"
                  search
                  selection
                  fluid
                  multiple
                  allowAdditions
                  value={currentExcludeAccountValues}
                  onAddItem={this.handleExcludeAccountAddition}
                  onChange={this.handleExcludeAccountChange}
                  className={"advancedOption"}
                />
              </>
            ) : null}
          </Accordion.Content>
        </Accordion>
      </div>
    );
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
    const advancedOptions = this.buildAdvancedOptions();

    return (
      <Form
        onKeyPress={(e) => {
          e.key === "Enter" && e.preventDefault();
        }}
      >
        <Header as="h3">{text}</Header>
        <ReactMarkdown linkTarget="_blank" children={description} />
        {blocks}
        {advancedOptions}
        {messagesToShow}
        <Button
          fluid
          onClick={this.handleSubmit.bind(this)}
          primary
          type="submit"
        >
          {this.props.role.arn ? "Add Permission" : "Add to Policy"}
        </Button>
      </Form>
    );
  }
}

export default SelfServiceComponent;
