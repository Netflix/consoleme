import React from 'react';
import ReactDOM from 'react-dom'
import { createStore, combineReducers } from 'redux';
import { reducer as reduxFormReducer } from 'redux-form';
import { object } from 'prop-types';
import { Checkbox as CheckboxUI } from 'semantic-ui-react';

export const renderField = ({ input, label, type, meta: { touched, error } }) => (
  <div>
    <label>{label}</label>
    <div>
      <input {...input} placeholder={label} type={type} />
      {touched && error && <span>{error}</span>}
    </div>
  </div>
);

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

export async function showResults(values) {
  // TODO: Ace editor showing editable policy and allow user to edit before submission
  window.alert(`You submitted:\n\n${JSON.stringify(values, null, 2)}`);
}

const reducer = combineReducers({
  form: reduxFormReducer, // mounted under "form"
});
export const store = (window.devToolsExtension
  ? window.devToolsExtension()(createStore)
  : createStore)(reducer);

const CheckboxC = ({
  input: { value, onChange, ...input },
  meta: { touched, error },
  ...rest
}) => (
  <div>
    <CheckboxUI
      {...input}
      {...rest}
      defaultChecked={!!value}
      onChange={(e, data) => onChange(data.checked)}
      type="checkbox"
    />
    {touched && error && <span>{error}</span>}
  </div>
);

CheckboxC.propTypes = {
  input: object.isRequired,
  meta: object.isRequired
};

CheckboxC.defaultProps = {
  input: null,
  meta: null
};

// export const Checkbox = <Field {...props} component={Checkbox} />;