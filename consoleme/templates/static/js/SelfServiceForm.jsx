import React, {Component} from 'react';
import PropTypes from 'prop-types';
import SelfServiceFormPage1 from './SelfServiceFormPage1';
import SelfServiceFormPage2 from './SelfServiceFormPage2';
import SelfServiceFormPage3 from './SelfServiceFormPage3';
import {StepProgress} from './SelfServiceFormComponents';
import {cancelNewPolicy, submitPolicyForReview} from "./policy_editor";
import 'babel-polyfill';


class SelfServiceForm extends Component {
  constructor(props) {
    super(props);

    this.state = {
      page: 1,
      isHidden: props.isHidden,
      choices: {wizard_policy_editor: null, buttonDisabled: false},
      arn: props.arn,
      account_id: props.account_id,
      policy_value: null,
      disableButton: false,
      is_temporary: false,
      expiration_date: "",
    };
  }

  nextPage = (choices) => {
    this.setState({page: this.state.page + 1, choices: choices});
  }

  previousPage = (choices) => {
    if (this.state.choices.choose === "CUSTOM") {
      this.setState({page: this.state.page - 2});
    } else {
      this.setState({page: this.state.page - 1});
    }

  }

  disableButton = () => {
    this.setState({disableButton: !disableButton});
  };

  handleTemporaryCheckboxChange = event => {
    this.setState({is_temporary: !this.state.is_temporary})
  };

  handleDateChange = (event, value) => {
    this.setState({expiration_date: value});
  };

  setPolicy = async (choices) => {
    this.setState(
      {policy_value: choices.wizard_policy_editor.ref.current.editor.getValue()},
      async () => {
        await submitPolicyForReview(choices.policy_type, choices.policy_name, choices.wizard_policy_editor.ref.current.editor, arn, account_id, true)
      }
    );
  };

  cancelRequest = async () => {
    this.setState({
      isHidden: !this.state.isHidden,
      choices: null
    });
    await cancelNewPolicy();
  }

  render() {
    const {page} = this.state;
    let gridClass = "ui stackable center aligned page grid"
    let columnClass = "left aligned center floated column"
    if (window.location.href.endsWith("self_service")) {
      gridClass = columnClass = ""
    }
    return (
      !this.state.isHidden &&
      <div>
        {typeof arn === 'undefined' && <StepProgress page={page}/>}
        <div className={gridClass}>
          <div className={columnClass}>
            {typeof arn !== 'undefined' && <StepProgress page={page}/>}
            {page !== 1 && <label style={{width: "100%", marginBottom: "10px"}}><b>Role ARN:</b> {this.state.choices.arn}</label>}
            {page === 1 &&
            <SelfServiceFormPage1
              onSubmit={this.nextPage}
              cancelRequest={this.cancelRequest}
              toggleCheckbox={this.handleTemporaryCheckboxChange}
              handleDateChange={this.handleDateChange}
              is_temporary={this.state.is_temporary}
              expiration_date={this.state.expiration_date}
              arn={this.state.arn}
            />}
            {page === 2 &&
            <SelfServiceFormPage2
              choices={this.state.choices}
              previousPage={this.previousPage}
              onSubmit={this.nextPage}
            />}
            {page === 3 &&
            <SelfServiceFormPage3
              choices={this.state.choices}
              previousPage={this.previousPage}
              disableButton={this.disableButton}
              state={this.state}
              onSubmit={async (e) => {
                await this.setPolicy(e);
              }}
            />}
          </div>
        </div>
      </div>
    );
  }
}

SelfServiceForm.propTypes = {
  onSubmit: PropTypes.func.isRequired,
};

export default SelfServiceForm;
