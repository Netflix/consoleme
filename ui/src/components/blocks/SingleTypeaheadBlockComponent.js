import _ from "lodash";
import React, { Component } from "react";
import { Form, Search } from "semantic-ui-react";

class SingleTypeaheadBlockComponent extends Component {
  constructor(props) {
    super(props);
    this.state = {
      isLoading: false,
      results: [],
      value: "",
    };
  }

  handleResultSelect(e, { result }) {
    this.setState(
      {
        value: result.title,
      },
      () => {
        this.props.handleInputUpdate(result.title);
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
        this.props.handleInputUpdate(value);
      }
    );

    setTimeout(() => {
      if (this.state.value.length < 1) {
        return this.setState(
          {
            isLoading: false,
            results: [],
            value: "",
          },
          () => {
            this.props.handleInputUpdate("");
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
    const { isLoading, results, value } = this.state;
    const { defaultValue, required, label } = this.props;

    return (
      <Form.Field required={required || false}>
        <label>{label || "Enter Value"}</label>
        <Search
          fluid
          defaultValue={defaultValue || ""}
          loading={isLoading}
          onResultSelect={this.handleResultSelect.bind(this)}
          onSearchChange={_.debounce(this.handleSearchChange.bind(this), 500, {
            leading: true,
          })}
          results={results}
          value={value}
        />
      </Form.Field>
    );
  }
}

export default SingleTypeaheadBlockComponent;
