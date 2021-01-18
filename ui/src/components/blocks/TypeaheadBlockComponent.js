import _ from "lodash";
import React, { useState } from "react";
import { Form, Search } from "semantic-ui-react";
import { sendRequestCommon } from "../../helpers/utils";

const TypeaheadBlockComponent = (props) => {
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [value, setValue] = useState("");

  const handleResultSelect = (e, { result }) => {
    setValue(result.title);
    props.handleInputUpdate(props.name, result.title);
  };

  const handleSearchChange = (e, { value }) => {
    const { typeahead } = props;
    setIsLoading(true);
    setValue(value);
    props.handleInputUpdate(props.name, value);

    setTimeout(() => {
      if (value.length < 1) {
        setIsLoading(false);
        setResults([]);
        setValue("");
        props.handleInputUpdate("");
      }

      const re = new RegExp(_.escapeRegExp(value), "i");
      const isMatch = (result) => re.test(result.title);

      const TYPEAHEAD_API = typeahead.replace("{query}", value);
      sendRequestCommon(null, TYPEAHEAD_API, "get").then((source) => {
        setIsLoading(false);
        setResults(_.filter(source, isMatch));
      });
    }, 300);
  };

  const { defaultValue, required, label } = props;

  return (
    <Form.Field required={required || false}>
      <label>{label || "Enter Value"}</label>
      <Search
        fluid
        defaultValue={defaultValue || ""}
        loading={isLoading}
        onResultSelect={(e, data) => handleResultSelect(e, data)}
        onSearchChange={_.debounce(
          (e) => handleSearchChange(e, e.target),
          500,
          {
            leading: true,
          }
        )}
        results={results}
        value={value}
      />
    </Form.Field>
  );
};

export default TypeaheadBlockComponent;
