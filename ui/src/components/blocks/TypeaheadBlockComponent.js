import _ from "lodash";
import React, { useState } from "react";
import { Form, Search } from "semantic-ui-react";
import { sendRequestCommon } from "../../helpers/utils";

const TypeaheadBlockComponent = (props) => {
  const initialState = {
    isLoading: false,
    results: [],
    value: "",
  };

  const [state, setState] = useState(initialState);

  const handleResultSelect = (e, { result }) => {
    setState({
      ...state,
      value: result.title,
    });
    props.handleInputUpdate(result.title);
  };

  const handleSearchChange = (e, { value }) => {
    const { typeahead } = props;
    setState({
      ...state,
      isLoading: true,
      value,
    });
    props.handleInputUpdate(value);

    setTimeout(() => {
      if (state.value.length < 1) {
        setState({
          ...state,
          isLoading: false,
          results: [],
          value: "",
        });
        props.handleInputUpdate("");
      }

      const re = new RegExp(_.escapeRegExp(value), "i");
      const isMatch = (result) => re.test(result.title);

      const TYPEAHEAD_API = typeahead.replace("{query}", value);
      sendRequestCommon(null, TYPEAHEAD_API, "get").then((source) => {
        this.setState({
          isLoading: false,
          results: _.filter(source, isMatch),
        });
      });
    }, 300);
  };

  const { isLoading, results, value } = state;
  const { defaultValue, required, label } = props;

  return (
    <Form.Field required={required || false}>
      <label>{label || "Enter Value"}</label>
      <Search
        fluid
        defaultValue={defaultValue || ""}
        loading={isLoading}
        onResultSelect={() => handleResultSelect(this)}
        onSearchChange={_.debounce(() => handleSearchChange(this), 500, {
          leading: true,
        })}
        results={results}
        value={value}
      />
    </Form.Field>
  );
};

export default TypeaheadBlockComponent;
