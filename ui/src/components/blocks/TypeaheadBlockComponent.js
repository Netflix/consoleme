import _ from "lodash";
import React, { Component } from "react";
import { Form, Icon, Label, Search } from "semantic-ui-react";

class TypeaheadBlockComponent extends Component {
  constructor(props) {
    super(props);
    this.state = {
      isLoading: false,
      results: [],
      selectedValues: [],
      value: "",
    };
  }

  _handleKeyDown = (e) => {
    if (e.key === "Enter") {
      if (!e.target.value) {
        return;
      }
      let values = this.state.selectedValues;
      values.push(e.target.value);
      this.setState(
        {
          selectedValues: values,
          value: "",
          results: [],
        },
        () => {
          this.props.handleInputUpdate(values);
        }
      );
    }
  };

  handleSelectedValueDelete(value) {
    this.setState({
      selectedValues: this.state.selectedValues.filter(
        (item) => item !== value
      ),
    });
  }

  handleResultSelect(e, { result }) {
    let values = this.state.selectedValues;
    values.push(result.title);
    this.setState(
      {
        value: "",
        selectedValues: values,
      },
      () => {
        this.props.handleInputUpdate(values);
      }
    );
  }

  handleSearchChange(e, { value }) {
    const { typeahead } = this.props;
    this.setState(
      {
        isLoading: true,
        value,
      },
      () => {
        this.props.handleInputUpdate(this.state.selectedValues);
      }
    );

    setTimeout(() => {
      if (value.length < 1) {
        return this.setState(
          {
            isLoading: false,
            results: [],
            value: "",
          },
          () => {
            this.props.handleInputUpdate(this.state.selectedValues);
          }
        );
      }

      const re = new RegExp(_.escapeRegExp(value), "i");
      const isMatch = (result) => re.test(result.title);

      const TYPEAHEAD_API = typeahead.replace("{query}", value);
      this.props
        .sendRequestCommon(null, TYPEAHEAD_API, "get")
        .then((source) => {
          this.setState({
            isLoading: false,
            results: _.filter(source, isMatch),
          });
        });
    }, 300);
  }

  render() {
    const { isLoading, results, value, selectedValues } = this.state;
    const { defaultValue, required, label } = this.props;

    const selectedValueLabels = selectedValues.map((selectedValue) => {
      return (
        <Label basic color={"red"}>
          {selectedValue}
          <Icon
            name="delete"
            onClick={() => this.handleSelectedValueDelete(selectedValue)}
          />
        </Label>
      );
    });

    return (
      <Form.Field required={required || false}>
        <label>{label || "Enter Value"}</label>
        <Search
          fluid
          multiple
          defaultValue={defaultValue || ""}
          loading={isLoading}
          onResultSelect={this.handleResultSelect.bind(this)}
          onSearchChange={_.debounce(this.handleSearchChange.bind(this), 500, {
            leading: true,
          })}
          onKeyDown={this._handleKeyDown}
          results={results}
          value={value}
          showNoResults={false}
        />
        <br />
        {selectedValueLabels}
      </Form.Field>
    );
  }
}

export default TypeaheadBlockComponent;
