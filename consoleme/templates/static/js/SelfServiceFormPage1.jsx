import {Field, reduxForm} from "redux-form";
import React from "react";
import {Dropdown, Form} from 'semantic-ui-react';
import {DateInput} from 'semantic-ui-calendar-react';
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
    <div>For Help, visit <a href={"http://go/selfserviceiamtldr"} target={"_blank"}>go/selfserviceiamtldr</a></div>
    <br />
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

const semanticCheckbox = ({input, label}) => (
    <div className="ui checkbox" style={{paddingTop: "5px"}}>
        <input type="checkbox" readOnly="" tabIndex="0" {...input}/>
        <label style={{width: "auto"}}>{label}</label>
    </div>
);

const semanticDatePicker = ({input, label}) => (
    <div>
        <Form.Field>
            <label style={{width: "auto", paddingTop: "10px"}}>{label}</label>
            <DateInput
                clearable {...input}
                dateFormat="YYYY-MM-DD"
                name="Foo"
                value={input.value}
                onChange={(param, data) => input.onChange(data.value)}
                placeholder={input.placeholder}
            />
        </Form.Field>
    </div>
)

const SelfServiceFormPage1 = props => {
  const {handleSubmit, cancelRequest} = props;
  let cancelButtonDisplayed = "";
  if (window.location.href.endsWith("self_service")) {
    cancelButtonDisplayed = "none";
  }

  return (
    <Form onSubmit={handleSubmit} className="ui form">
        <DetermineArn arn={props.arn} />
      <div>
          <Field name="choose" component={DropdownFormField} label="Service" validate={required}/>
      </div>
      <br />
      <div>
        <label><b>Temporary Policy</b></label>
        <div>
          <div>
            <Field
                name="is_temporary"
                id="is_temporary"
                label="This policy is temporary"
                component={semanticCheckbox}
                type="checkbox"
                onChange={props.toggleCheckbox}/>
          </div>
          { props.is_temporary ? <Field
              name="expiration_date"
              id="expiration_date"
              label="Policy expiration date:"
              component={semanticDatePicker}
              value={props.expiration_date}
              iconPosition="left"
              onChange={props.handleDateChange}
              validate={required} />
              : null}
        </div>
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