import {Field, reduxForm} from "redux-form";
import React from 'react';
import {CustomSearchField} from './SelfServiceFormComponents';


// Warn on Cross Account S3 Write
// Fix Previous and Next buttons. Order and arrow
const required = value => value ? undefined : 'Required'

const semanticCheckbox = ({input, label}) => (
  <div className="ui checkbox">
    <input type="checkbox" readOnly="" tabIndex="0" {...input}/>
    <label style={{width: "auto"}}>{label}</label>
  </div>
);

const TextField = ({input, label, type, meta: {touched, error, warning}}) => (
  <div>
    <label>{label}</label>
    <div>
      <input {...input} placeholder={label} type={type}/>
      {touched && ((error && <strong style={{color: 'red'}}>{error}</strong>) || (warning &&
        <strong style={{color: 'red'}}>{warning}</strong>))}
    </div>
  </div>
);


const S3Form = props => {
  const {choices} = props;
  choices.prefix = "/*"
  return (
    <div>
      <div dangerouslySetInnerHTML={{__html: custom_s3_guidance}}></div>
      <br/>
      <div className="field">
        <label style={{width: "auto"}} dangerouslySetInnerHTML={{__html: custom_s3_bucket_name_header}}></label>
        <div>
          <Field
            name="bucket"
            component={CustomSearchField}
            type="text"
            resource_type="s3"
            placeholder="S3 Bucket Name"
            validate={[required]}
            account_id={account_id}
            value={choices.bucket}
          />
        </div>
      </div>
      <div className="field">
        <label style={{width: "auto"}}>Prefix (Folder under S3 that you need access to).</label>
        <Field
          name="prefix"
          component="input"
          type="text"
          placeholder="Prefix (Folder under S3 that you need access to). Should end in '/*'"
        />
      </div>
      {/*<div>*/}
      {/*  <Field name="multiregion" id="multiregion" label={"Multi Region? (Check if using Hermes and also need access to the 'us-west-2.' and 'eu-west-1.' prefixed buckets.)"}*/}
      {/*         component={semanticCheckbox} type="checkbox"/><br/><br/>*/}
      {/*</div>*/}
      <div>
        <div>
          <label><b>Desired Permissions</b></label><br/>
          <div>
            <div>
              <Field name="list" id="list" label="LIST Objects" component={semanticCheckbox} type="checkbox"/>
            </div>
            <div>
              <Field name="get" id="get" label="GET Objects" component={semanticCheckbox} type="checkbox"/>
            </div>
            <div>
              <Field name="put" id="put" label="PUT Objects" component={semanticCheckbox} type="checkbox"/>
            </div>
            <div>
              <Field name="delete" id="delete" label="DELETE Objects" component={semanticCheckbox} type="checkbox"/>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const SQSForm = props => {
  const {choices} = props;
  choices.permission = ""
  return (
    <div>
      <div className="field">
        <label>Queue ARN</label>
        <div>
          <Field
            name="queuearn"
            component={CustomSearchField}
            type="text"
            resource_type="sqs"
            placeholder="SQS Queue Arn"
            validate={[required]}
          />
        </div>
      </div>
      <div>
        <label><b>Desired Permissions</b></label><br/>
        <div>
          <div>
            <Field name="get" id="get" label="Get Queue Attributes/URL" component={semanticCheckbox} type="checkbox"/>
          </div>
          <div>
            <Field name="receive" id="receive" label="Receive Messages" component={semanticCheckbox} type="checkbox"/>
          </div>
          <div>
            <Field name="send" id="send" label="Send Messages" component={semanticCheckbox} type="checkbox"/>
          </div>
          <div>
            <Field name="delete" id="delete" label="Delete Messages" component={semanticCheckbox} type="checkbox"/>
          </div>
          <div>
            <Field name="set" id="set" label="Set Queue Attributes" component={semanticCheckbox} type="checkbox"/>
          </div>
        </div>
      </div>
    </div>
  );
};

const SNSForm = props => {
  const {choices} = props;
  choices.permission = ""
  return (
    <div>
      <div className="field">
        <label>Topic ARN</label>
        <div>
          <Field
            name="topicarn"
            component={CustomSearchField}
            type="text"
            resource_type="sns"
            placeholder="SNS Topic Arn"
            validate={[required]}
          />
        </div>
      </div>
      <div>
        <label><b>Desired Permissions</b></label><br/>
        <div>
          <div>
            <Field name="get" id="get" label="Get Topic/Endpoint Attributes" component={semanticCheckbox}
                   type="checkbox"/>
          </div>
          <div>
            <Field name="publish" id="publish" label="Publish Messages" component={semanticCheckbox} type="checkbox"/>
          </div>
          <div>
            <Field name="subscribe" id="subscribe" label="Subscribe to Topic" component={semanticCheckbox}
                   type="checkbox"/>
          </div>
          <div>
            <Field name="unsubscribe" id="unsubscribe" label="Unsubscribe from Topic" component={semanticCheckbox}
                   type="checkbox"/>
          </div>
        </div>
      </div>
    </div>
  );
};

const R53Form = props => {
  const {choices} = props;
  choices.permission = ""
  return (
    <div>
      <div>
        <label><b>Desired Permissions</b></label><br/>
        <div>
          <div>
            <Field name="list" id="list" label="List Records" component={semanticCheckbox} type="checkbox"/>
          </div>
          <div>
            <Field name="change" id="change" label="Change Records" component={semanticCheckbox} type="checkbox"/>
          </div>
        </div>
      </div>
    </div>
  );
};

const STSForm = props => {
  const {choices} = props;
  choices.permission = ""
  return (
    <div>
      <div className="field">
        <label>Role ARN That you wish to assume</label>
        <div>
          <Field
            name="rolearn"
            component={CustomSearchField}
            type="text"
            placeholder="Role ARN"
            resource_type="iam_arn"
            validate={[required]}
          />
        </div>
      </div>
    </div>
  );
};

const EC2Form = props => {
  const {choices} = props;
  choices.permission = ""
  return (
    <div>
      <div>
        <label><b>Desired Permissions</b></label><br/>
        <div>
          <div>
            <Field name="volmount" id="volmount" label="VolMount" component={semanticCheckbox} type="checkbox"/>
          </div>
        </div>
      </div>
    </div>
  );
};

const RDSForm = props => {
  const {choices} = props;
  choices.permission = ""
  return (
    <div>
      <div>
        <label><b>Desired Permissions</b></label><br/>
        <div>
          <div>
            <Field name="passrole" id="passrole" label="Passrole to rds-monitoring-role" component={semanticCheckbox}
                   type="checkbox"/>
          </div>
        </div>
      </div>
    </div>
  );
};

const SESForm = props => {
  const {choices} = props;
  choices.permission = ""
  choices.fromaddress = ses_from_address
  return (
    <div>
      <div className="field">
        <label style={{width: "auto"}}>Email Address to send from (Must end in
          "@{ses_from_address.split("@")[1]}")</label>
        <div>
          <Field
            name="fromaddress"
            component={TextField}
            type="text"
            placeholder={ses_from_address}
            validate={[required]}
          />
        </div>
      </div>
    </div>
  );
};

const SelfServiceFormPage2 = props => {
  const {choices, handleSubmit, previousPage} = props;

  if (choices.arn) {
    arn = choices.arn
    account_id = choices.arn.split(":")[4]
  }

  if (choices.choose === "CUSTOM") {
    handleSubmit()
  }
  return (
    <div>
      <form onSubmit={handleSubmit} className="ui form">
        {choices.choose === "R53" && <R53Form choices={choices}/>}
        {choices.choose === "S3" && <S3Form choices={choices}/>}
        {choices.choose === "SES" && <SESForm choices={choices}/>}
        {choices.choose === "SQS" && <SQSForm choices={choices}/>}
        {choices.choose === "SNS" && <SNSForm choices={choices}/>}
        {choices.choose === "STS" && <STSForm choices={choices}/>}
        {choices.choose === "EC2" && <EC2Form choices={choices}/>}
        {choices.choose === "RDS" && <RDSForm choices={choices}/>}
        <div>
          <button type="button" className="ui positive button previous" onClick={previousPage}
                  style={{margin: "10px"}}>
            Previous
          </button>
          <button type="submit" className="ui positive button next" style={{margin: "10px"}}>
            Next
          </button>
        </div>
      </form>
    </div>
  )

};

export default reduxForm({
  form: "wizard", //                 <------ same form name
  destroyOnUnmount: false, //        <------ preserve form data
  forceUnregisterOnUnmount: true // <------ unregister fields on unmount
})(SelfServiceFormPage2);
