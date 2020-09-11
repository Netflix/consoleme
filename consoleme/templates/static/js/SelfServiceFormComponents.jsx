import React, { Component } from "react";
import { Label, Search, Step } from "semantic-ui-react";
import _ from "lodash";

export class CustomSearchField extends Component {
  constructor(props) {
    super(props);
    this.searchChange = _.debounce(this.handleSearchChange, 500, {
      leading: true,
    });
    this.state = {
      isLoading: false,
      value: props.input.value,
      results: [],
      label: props.label,
      input: props.input,
      value_param: props.value_param || "title",
      type: props.type,
      meta: props.meta,
      resource_type: props.resource_type,
      account_id: props.account_id,
    };
  }

  resultRenderer = ({ title }) => {
    return <Label content={title} />;
  };

  handleResultSelect = (e, { result }) => {
    let input = this.state.input;

    input.value = result[this.state.value_param];
    this.setState({ value: result[this.state.value_param], input: input });
  };

  fetchResults(value) {
    let url =
      "/policies/typeahead?resource=" +
      this.state.resource_type +
      "&search=" +
      value;
    if (this.state.account_id) {
      url += "&account_id=" + this.state.account_id;
    }

    fetch(url)
      .then((response) => response.json())
      .then((json) => {
        this.setState({
          isLoading: false,
          results: JSON.parse(JSON.stringify(json)),
        });
      });
  }

  handleSearchChange = (e, { value }) => {
    this.fetchResults(value);
  };

  preHandleSearchChange = (e, { value }) => {
    this.setState({ isLoading: true, value: value });
    this.searchChange(e, { value });
  };

  render() {
    return (
      <div>
        <label>{this.state.label}</label>
        <div>
          <Search
            fluid
            {...this.state.input}
            placeholder={this.state.label}
            type={this.state.type}
            loading={this.state.isLoading}
            onResultSelect={(param, data) => {
              this.props.input.onChange(data.result.title);
              this.handleResultSelect(param, data);
            }}
            onSearchChange={this.preHandleSearchChange}
            onChange={(param, data) => props.input.onChange(data.value)}
            results={this.state.results}
            value={this.state.value}
            resultRenderer={this.resultRenderer}
          />
          {this.props.meta.touched && this.props.meta.error && (
            <strong style={{ color: "red" }}>{this.props.meta.error}</strong>
          )}
        </div>
      </div>
    );
  }
}

export const StepProgress = (props) => {
  return (
    <Step.Group ordered>
      <Step completed={props.page > 1}>Select Resource</Step>
      <Step completed={props.page > 2}>Provide Permission Details</Step>
      <Step completed={props.page > 3}>Review and Submit</Step>
    </Step.Group>
  );
};
