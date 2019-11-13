import {Field, reduxForm} from "redux-form";
import React from "react";
import {Dropdown, Form} from 'semantic-ui-react';
import SelfServiceFormAppSearch from "./SelfServiceFormAppSearch";

const supportedServices = [
  {key: 'select', value: '', text: 'Choose One'},
  {key: 'CUSTOM', value: 'CUSTOM', text: 'Custom Permissions (Advanced)'},
  {key: 'EC2', value: 'EC2', text: 'EC2 Volmount'},
  {key: 'RDS', value: 'RDS', text: 'RDS Databases'},
  {key: 'R53', value: 'R53', text: 'Route 53 DNS'},
  {key: 'S3', value: 'S3', text: 'S3 Bucket'},
  {key: 'SES', value: 'SES', text: 'SES - Send Email'},
  {key: 'SNS', value: 'SNS', text: 'SNS Topic'},
  {key: 'SQS', value: 'SQS', text: 'SQS Queue'},
  {key: 'STS', value: 'STS', text: 'STS AssumeRole'},
  // {key: 'APIP', value:'APIP', text:'API Protect' },
];

const required = value => value ? undefined : 'Required field';

function validArn(value) {
  let re = RegExp('^arn:aws:iam::\\d+:role\\/.*$');
  if (re.test(value)) {
    return undefined;
  }
  return 'Invalid ARN. Search for your application and select an account on the right side.';
}

const DropdownFormField = ({input, label, type, meta: {touched, error, warning}}) => (
  <div>
    <Form.Field>
      <label>I want this role to have access to:</label>
      <Dropdown
        selection {...input}
        value={input.value}
        onChange={(param, data) => input.onChange(data.value)}
        placeholder={label}
        options={supportedServices}
      />
    </Form.Field>
    {touched && ((error && <strong style={{color: 'red'}}>{error}</strong>) || (warning &&
      <strong style={{color: 'red'}}>{warning}</strong>))}
  </div>
);

function DetermineArn(props) {
  if (props.arn) {
    return (
      <div>
      </div>
    )
  }
  return (
  <div>
    <div className="field" style={{width: "100%"}}>
      <label style={{width: "100%"}}>Search for your application and select an account to fill in your role identifier:</label>
      <div>
        <Field
          name="arn"
          component={SelfServiceFormAppSearch}
          type="text"
          resource_type="app"
          placeholder="Search for your application..."
          validate={[required, validArn]}
        />
      </div>
    </div>
    <br />
  </div>
  )
}


const SelfServiceFormPage1 = props => {
  const {handleSubmit, cancelRequest} = props;
  let cancelButtonDisplayed = "";
  if (window.location.href.endsWith("self_service")) {
    cancelButtonDisplayed = "none";
  }
  return (
    <Form onSubmit={handleSubmit}>
        <DetermineArn arn={props.state.arn} />
      <div>
        <Field name="choose" component={DropdownFormField} label="Service" validate={required}/>
      </div>
      <div>
        <button type="cancel" className="ui negative button cancel" onClick={cancelRequest} style={{margin: "10px", display: cancelButtonDisplayed}}>
          Cancel
        </button>
        <button type="submit" className="ui positive button next" style={{margin: "10px"}}>
          Next
        </button>
      </div>
    </Form>
  )
};

export default reduxForm({
  form: 'wizard', //                 <------ same form name
  destroyOnUnmount: false, //        <------ preserve form data
  forceUnregisterOnUnmount: true, // <------ unregister fields on unmount
})(SelfServiceFormPage1);